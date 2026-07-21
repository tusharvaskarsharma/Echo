"""Secure Family Group membership and shared-memory endpoints.

All access decisions are derived from the authenticated user and database rows.
The browser may select an owner to view, but it can never grant itself access.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.db.client import get_db
from app.models.memory import MemoryFragment
from app.routers.emmy_conversation import ConversationHistoryItem, EmmyConversationRequest, conversation
from app.services.username_service import normalize_username, username_error


router = APIRouter(prefix="/groups", tags=["family groups"], dependencies=[Depends(get_current_user)])
shared_router = APIRouter(tags=["family groups"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class InvitationCreate(BaseModel):
    username: str = Field(min_length=1, max_length=200)


class SharingUpdate(BaseModel):
    share_memories: bool


class SharedChatRequest(BaseModel):
    owner_id: UUID
    question: str = Field(min_length=1, max_length=4000)
    conversation_history: list[ConversationHistoryItem] = Field(default_factory=list, max_length=20)


def _clean_text(value: str | None) -> str | None:
    return value.strip() or None if value else None


def _validated_username(value: str) -> str:
    username = normalize_username(value)
    if error := username_error(username):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error)
    return username


def _group_dict(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "description": row["description"],
        "owner_id": str(row["owner_id"]),
        "owner_name": row["owner_name"] or row["owner_username"] or "Group owner",
        "owner_username": row["owner_username"],
        "role": row["role"],
        "member_count": int(row["member_count"]),
        "share_memories": bool(row["share_memories"]),
        "created_at": row["created_at"].isoformat(),
        "members": [],
        "invitations": [],
    }


def _invitation_dict(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "group_id": str(row["group_id"]),
        "group_name": row.get("group_name") if hasattr(row, "get") else row["group_name"],
        "inviter_id": str(row["inviter_id"]),
        "inviter_name": row["inviter_name"] or row["inviter_username"] or "A family member",
        "inviter_username": row["inviter_username"],
        "invited_user_id": str(row["invited_user_id"]),
        "invited_username": row["invited_username"],
        "invited_name": row["invited_name"] or row["invited_username"] or "Member",
        "status": str(row["status"]),
        "created_at": row["created_at"].isoformat(),
        "responded_at": row["responded_at"].isoformat() if row["responded_at"] else None,
        "expires_at": row["expires_at"].isoformat(),
    }


async def _expire_invitations(
    conn: asyncpg.Connection, group_id: UUID | None = None, invited_user_id: UUID | str | None = None,
) -> None:
    """Make expiry visible before any listing, resend, or response decision."""
    clauses = ["status = 'pending'", "expires_at <= now()"]
    values: list[UUID | str] = []
    if group_id is not None:
        values.append(group_id)
        clauses.append(f"group_id = ${len(values)}")
    if invited_user_id is not None:
        values.append(str(invited_user_id))
        clauses.append(f"invited_user_id = ${len(values)}")
    await conn.execute(
        f"UPDATE public.group_invitations SET status = 'expired' WHERE {' AND '.join(clauses)}",
        *values,
    )


def _require_pending_invitation(row: asyncpg.Record) -> None:
    if str(row["status"]) != "pending":
        raise HTTPException(status_code=409, detail=f"Invitation is already {row['status']}")
    if row["expires_at"] <= datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invitation has expired")


async def _ensure_has_username(conn: asyncpg.Connection, user_id: str) -> None:
    username = await conn.fetchval("SELECT username FROM public.profiles WHERE id = $1", user_id)
    if not username:
        raise HTTPException(status_code=403, detail="Choose a username before using Family Groups")


async def _group_for_member(conn: asyncpg.Connection, group_id: UUID, user_id: str) -> asyncpg.Record:
    row = await conn.fetchrow(
        """SELECT g.id, g.owner_id, gm.role
           FROM public.groups g JOIN public.group_members gm ON gm.group_id = g.id
           WHERE g.id = $1 AND gm.user_id = $2""",
        group_id, user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")
    return row


async def _require_group_owner(conn: asyncpg.Connection, group_id: UUID, user_id: str) -> asyncpg.Record:
    group = await _group_for_member(conn, group_id, user_id)
    if str(group["owner_id"]) != user_id:
        raise HTTPException(status_code=403, detail="Only the group owner can do that")
    return group


async def _groups_for_user(conn: asyncpg.Connection, user_id: str) -> list[dict]:
    rows = await conn.fetch(
        """SELECT g.id, g.name, g.description, g.owner_id, g.created_at, membership.role,
                  owner_profile.full_name AS owner_name, owner_profile.username AS owner_username,
                  COUNT(all_members.id) AS member_count,
                  EXISTS (
                    SELECT 1 FROM public.memory_permissions mp
                    WHERE mp.group_id = g.id AND mp.memory_owner_id = g.owner_id
                  ) AS share_memories
           FROM public.group_members membership
           JOIN public.groups g ON g.id = membership.group_id
           LEFT JOIN public.profiles owner_profile ON owner_profile.id = g.owner_id
           LEFT JOIN public.group_members all_members ON all_members.group_id = g.id
           WHERE membership.user_id = $1
           GROUP BY g.id, membership.role, owner_profile.full_name, owner_profile.username
           ORDER BY g.created_at DESC""",
        user_id,
    )
    groups = [_group_dict(row) for row in rows]
    if not groups:
        return groups
    member_rows = await conn.fetch(
        """SELECT gm.group_id, gm.user_id, gm.role, gm.joined_at, p.username, p.full_name
           FROM public.group_members gm
           LEFT JOIN public.profiles p ON p.id = gm.user_id
           WHERE gm.group_id = ANY($1::uuid[])
           ORDER BY CASE gm.role WHEN 'owner' THEN 0 ELSE 1 END, lower(COALESCE(p.full_name, p.username, ''))""",
        [UUID(group["id"]) for group in groups],
    )
    by_id = {group["id"]: group for group in groups}
    for member in member_rows:
        by_id[str(member["group_id"])]["members"].append({
            "user_id": str(member["user_id"]),
            "username": member["username"],
            "display_name": member["full_name"] or member["username"] or "Member",
            "role": member["role"],
            "joined_at": member["joined_at"].isoformat(),
            "is_current_user": str(member["user_id"]) == user_id,
        })
    owner_group_ids = [UUID(group["id"]) for group in groups if group["owner_id"] == user_id]
    if owner_group_ids:
        invitation_rows = await conn.fetch(
            """SELECT i.id, i.group_id, i.inviter_id, i.invited_user_id, i.status, i.created_at,
                      i.responded_at, i.expires_at, invited.username AS invited_username,
                      invited.full_name AS invited_name, inviter.username AS inviter_username,
                      inviter.full_name AS inviter_name
               FROM public.group_invitations i
               JOIN public.profiles invited ON invited.id = i.invited_user_id
               JOIN public.profiles inviter ON inviter.id = i.inviter_id
               WHERE i.group_id = ANY($1::uuid[])
               ORDER BY i.created_at DESC""",
            owner_group_ids,
        )
        for invitation in invitation_rows:
            by_id[str(invitation["group_id"])]["invitations"].append(_invitation_dict(invitation))
    return groups


async def _can_access_owner(conn: asyncpg.Connection, caller_id: str, owner_id: UUID | str) -> bool:
    return bool(await conn.fetchval(
        """SELECT $1::uuid = $2::uuid OR EXISTS (
               SELECT 1 FROM public.memory_permissions mp
               JOIN public.group_members gm ON gm.group_id = mp.group_id
               WHERE mp.memory_owner_id = $2::uuid AND gm.user_id = $1::uuid
           )""",
        caller_id, str(owner_id),
    ))


def _memory_from_row(row: asyncpg.Record) -> MemoryFragment:
    values = dict(row)
    for field, default in (("emotion_tags", []), ("topics", []), ("people_mentioned", []), ("semantic_metadata", {})):
        if isinstance(values.get(field), str):
            values[field] = json.loads(values[field])
        elif values.get(field) is None:
            values[field] = default
    return MemoryFragment(**values)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreate,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    user_id = str(user["sub"])
    await _ensure_has_username(conn, user_id)
    name = _clean_text(payload.name)
    if not name:
        raise HTTPException(status_code=422, detail="Group name is required")
    async with conn.transaction():
        group = await conn.fetchrow(
            """INSERT INTO public.groups (owner_id, name, description)
               VALUES ($1, $2, $3) RETURNING id""",
            user_id, name, _clean_text(payload.description),
        )
        await conn.execute(
            "INSERT INTO public.group_members (group_id, user_id, role) VALUES ($1, $2, 'owner')",
            group["id"], user_id,
        )
    return {"id": str(group["id"]), "name": name, "message": "Group created"}


@router.get("")
async def list_groups(
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> list[dict]:
    try:
        await _expire_invitations(conn)
        # An authenticated account with no memberships has no error state.
        return await _groups_for_user(conn, str(user["sub"]))
    except asyncpg.PostgresError as error:
        logger.exception("Failed to load family groups for user %s", user["sub"])
        raise HTTPException(status_code=503, detail="Family Groups are temporarily unavailable") from error


@router.get("/member-candidates")
async def find_member_candidate(
    username: str,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    """Find one exact username for the invitation confirmation UI.

    This is deliberately an exact, authenticated lookup rather than a profile
    directory, so usernames cannot be enumerated by prefix.
    """
    canonical_username = _validated_username(username)
    candidate = await conn.fetchrow(
        "SELECT id, username, full_name FROM public.profiles WHERE username = $1",
        canonical_username,
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="No account has that username")
    if str(candidate["id"]) == str(user["sub"]):
        raise HTTPException(status_code=422, detail="You cannot invite yourself")
    return {
        "user_id": str(candidate["id"]), "username": candidate["username"],
        "display_name": candidate["full_name"] or candidate["username"],
    }


@router.patch("/{group_id}")
async def update_group(
    group_id: UUID,
    payload: GroupUpdate,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    if "name" not in payload.model_fields_set and "description" not in payload.model_fields_set:
        raise HTTPException(status_code=422, detail="Provide a group name or description")
    user_id = str(user["sub"])
    await _require_group_owner(conn, group_id, user_id)
    name = _clean_text(payload.name) if "name" in payload.model_fields_set else None
    if "name" in payload.model_fields_set and not name:
        raise HTTPException(status_code=422, detail="Group name is required")
    row = await conn.fetchrow(
        """UPDATE public.groups SET
               name = COALESCE($1, name), description = CASE WHEN $2 THEN $3 ELSE description END,
               updated_at = now()
           WHERE id = $4 RETURNING id, name, description""",
        name, "description" in payload.model_fields_set, _clean_text(payload.description), group_id,
    )
    return {"id": str(row["id"]), "name": row["name"], "description": row["description"]}


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> Response:
    await _require_group_owner(conn, group_id, str(user["sub"]))
    await conn.execute("DELETE FROM public.groups WHERE id = $1", group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{group_id}/invite", status_code=status.HTTP_201_CREATED)
async def invite_group_member(
    group_id: UUID,
    payload: InvitationCreate,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    """Create a seven-day invitation without granting any membership or access."""
    caller_id = str(user["sub"])
    await _require_group_owner(conn, group_id, caller_id)
    username = _validated_username(payload.username)
    invited_user = await conn.fetchrow(
        "SELECT id, username, full_name FROM public.profiles WHERE username = $1", username
    )
    if not invited_user:
        raise HTTPException(status_code=404, detail="No account has that username")
    if str(invited_user["id"]) == caller_id:
        raise HTTPException(status_code=422, detail="You cannot invite yourself")
    if await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM public.group_members WHERE group_id = $1 AND user_id = $2)",
        group_id, invited_user["id"],
    ):
        raise HTTPException(status_code=409, detail="That user is already a member")
    await _expire_invitations(conn, group_id, invited_user["id"])
    try:
        row = await conn.fetchrow(
            """INSERT INTO public.group_invitations (group_id, inviter_id, invited_user_id)
               VALUES ($1, $2, $3)
               RETURNING id, group_id, inviter_id, invited_user_id, status, created_at, responded_at, expires_at""",
            group_id, caller_id, invited_user["id"],
        )
    except asyncpg.UniqueViolationError as error:
        raise HTTPException(status_code=409, detail="That user already has a pending invitation") from error
    return {
        **_invitation_dict({
            **dict(row), "group_name": None, "inviter_name": user.get("email"), "inviter_username": None,
            "invited_name": invited_user["full_name"], "invited_username": invited_user["username"],
        }),
        "message": "Invitation sent. They must accept before joining.",
    }


@router.post("/{group_id}/members", status_code=status.HTTP_410_GONE)
async def direct_member_addition_is_disabled(
    group_id: UUID,
    payload: InvitationCreate,
    user: Annotated[dict, Depends(get_current_user)],
) -> None:
    """Prevent legacy clients from bypassing the acceptance step."""
    raise HTTPException(status_code=410, detail="Direct member addition is disabled; send an invitation instead")


@router.get("/{group_id}/pending")
async def group_invitations(
    group_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> list[dict]:
    """Owner-only invitation history, including pending and response badges."""
    await _require_group_owner(conn, group_id, str(user["sub"]))
    await _expire_invitations(conn, group_id)
    rows = await conn.fetch(
        """SELECT i.id, i.group_id, g.name AS group_name, i.inviter_id, i.invited_user_id,
                      i.status, i.created_at, i.responded_at, i.expires_at,
                      invited.username AS invited_username, invited.full_name AS invited_name,
                      inviter.username AS inviter_username, inviter.full_name AS inviter_name
               FROM public.group_invitations i
               JOIN public.groups g ON g.id = i.group_id
               JOIN public.profiles invited ON invited.id = i.invited_user_id
               JOIN public.profiles inviter ON inviter.id = i.inviter_id
               WHERE i.group_id = $1
               ORDER BY i.created_at DESC""",
        group_id,
    )
    return [_invitation_dict(row) for row in rows]


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_group_invitation(
    invitation_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> Response:
    """Only a group owner may cancel an unanswered invitation."""
    await _expire_invitations(conn)
    deleted = await conn.fetchval(
        """DELETE FROM public.group_invitations i
           USING public.groups g
           WHERE i.id = $1 AND i.group_id = g.id AND g.owner_id = $2 AND i.status = 'pending'
           RETURNING i.id""",
        invitation_id, str(user["sub"]),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Pending invitation not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{group_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_or_leave_group(
    group_id: UUID,
    member_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> Response:
    caller_id = str(user["sub"])
    group = await _group_for_member(conn, group_id, caller_id)
    target = await conn.fetchrow(
        "SELECT user_id, role FROM public.group_members WHERE group_id = $1 AND user_id = $2",
        group_id, member_id,
    )
    if not target:
        raise HTTPException(status_code=404, detail="Group member not found")
    is_owner = str(group["owner_id"]) == caller_id
    if not is_owner and str(member_id) != caller_id:
        raise HTTPException(status_code=403, detail="You can only leave a group yourself")
    if target["role"] == "owner":
        raise HTTPException(status_code=409, detail="The group owner cannot leave; delete the group instead")
    await conn.execute("DELETE FROM public.group_members WHERE group_id = $1 AND user_id = $2", group_id, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{group_id}/sharing")
async def update_group_sharing(
    group_id: UUID,
    payload: SharingUpdate,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    caller_id = str(user["sub"])
    await _require_group_owner(conn, group_id, caller_id)
    if payload.share_memories:
        await conn.execute(
            """INSERT INTO public.memory_permissions (memory_owner_id, group_id)
               VALUES ($1, $2)
               ON CONFLICT (memory_owner_id, group_id) DO NOTHING""",
            caller_id, group_id,
        )
    else:
        await conn.execute(
            "DELETE FROM public.memory_permissions WHERE memory_owner_id = $1 AND group_id = $2",
            caller_id, group_id,
        )
    return {"group_id": str(group_id), "share_memories": payload.share_memories}


@shared_router.get("/invitations")
async def list_invitations(
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> list[dict]:
    """The recipient's notification inbox. Only active pending invites appear."""
    user_id = str(user["sub"])
    try:
        await _expire_invitations(conn, invited_user_id=user_id)
        rows = await conn.fetch(
            """SELECT i.id, i.group_id, g.name AS group_name, i.inviter_id, i.invited_user_id,
                          i.status, i.created_at, i.responded_at, i.expires_at,
                          inviter.username AS inviter_username, inviter.full_name AS inviter_name,
                          invited.username AS invited_username, invited.full_name AS invited_name,
                          COUNT(members.id) AS member_count
                   FROM public.group_invitations i
                   JOIN public.groups g ON g.id = i.group_id
                   JOIN public.profiles inviter ON inviter.id = i.inviter_id
                   JOIN public.profiles invited ON invited.id = i.invited_user_id
                   LEFT JOIN public.group_members members ON members.group_id = i.group_id
                   WHERE i.invited_user_id = $1 AND i.status = 'pending' AND i.expires_at > now()
                   GROUP BY i.id, g.name, inviter.username, inviter.full_name, invited.username, invited.full_name
                   ORDER BY i.created_at DESC""",
            user_id,
        )
    except asyncpg.PostgresError as error:
        logger.exception("Failed to load invitations for user %s", user_id)
        raise HTTPException(status_code=503, detail="Invitations are temporarily unavailable") from error
    invitations = []
    for row in rows:
        invitation = _invitation_dict(row)
        invitation["member_count"] = int(row["member_count"])
        invitations.append(invitation)
    return invitations


async def _respond_to_invitation(
    conn: asyncpg.Connection, invitation_id: UUID, recipient_id: str, response: str,
) -> dict:
    """Atomically accept/decline an invitation owned by the signed-in recipient."""
    await _expire_invitations(conn, invited_user_id=recipient_id)
    async with conn.transaction():
        invitation = await conn.fetchrow(
            """SELECT i.id, i.group_id, g.name AS group_name, i.inviter_id, i.invited_user_id,
                      i.status, i.created_at, i.responded_at, i.expires_at,
                      inviter.username AS inviter_username, inviter.full_name AS inviter_name,
                      invited.username AS invited_username, invited.full_name AS invited_name
               FROM public.group_invitations i
               JOIN public.groups g ON g.id = i.group_id
               JOIN public.profiles inviter ON inviter.id = i.inviter_id
               JOIN public.profiles invited ON invited.id = i.invited_user_id
               WHERE i.id = $1 AND i.invited_user_id = $2
               FOR UPDATE""",
            invitation_id, recipient_id,
        )
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")
        _require_pending_invitation(invitation)
        updated = await conn.fetchrow(
            """UPDATE public.group_invitations
               SET status = $1
               WHERE id = $2 AND invited_user_id = $3 AND status = 'pending'
               RETURNING id, group_id, inviter_id, invited_user_id, status, created_at, responded_at, expires_at""",
            response, invitation_id, recipient_id,
        )
        if not updated:
            raise HTTPException(status_code=409, detail="Invitation has already been answered")
        if response == "accepted":
            await conn.execute(
                """INSERT INTO public.group_members (group_id, user_id, role)
                   VALUES ($1, $2, 'member') ON CONFLICT (group_id, user_id) DO NOTHING""",
                invitation["group_id"], recipient_id,
            )
        result = _invitation_dict({**dict(invitation), **dict(updated)})
        result["message"] = "Invitation accepted. You can now access this Emmy." if response == "accepted" else "Invitation declined."
        return result


@shared_router.post("/invitations/{invitation_id}/accept")
async def accept_invitation(
    invitation_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    return await _respond_to_invitation(conn, invitation_id, str(user["sub"]), "accepted")


@shared_router.post("/invitations/{invitation_id}/decline")
async def decline_invitation(
    invitation_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    return await _respond_to_invitation(conn, invitation_id, str(user["sub"]), "declined")


@shared_router.get("/shared-users")
async def shared_users(
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> list[dict]:
    """List accepted group members and whether their archive is selectable.

    A name is visible to fellow accepted members, while a missing permission
    keeps that person's archive disabled until they choose to share it. This
    avoids confusing an empty dropdown with an unaccepted invitation without
    granting access merely by listing a name.
    """
    try:
        rows = await conn.fetch(
            """SELECT member.user_id AS owner_id, owner.username, owner.full_name,
                      subject.id AS subject_id,
                      BOOL_OR(permission.memory_owner_id IS NOT NULL) AS can_access,
                      array_agg(DISTINCT groups.name ORDER BY groups.name) AS group_names
               FROM public.group_members AS caller_members
               JOIN public.groups AS groups ON groups.id = caller_members.group_id
               JOIN public.group_members AS member ON member.group_id = groups.id
               LEFT JOIN public.profiles AS owner ON owner.id = member.user_id
               LEFT JOIN public.memory_permissions AS permission
                 ON permission.group_id = groups.id AND permission.memory_owner_id = member.user_id
               LEFT JOIN LATERAL (
                 SELECT id FROM public.subjects WHERE user_id = member.user_id ORDER BY created_at ASC LIMIT 1
               ) subject ON true
               WHERE caller_members.user_id = $1 AND member.user_id <> $1::uuid
               GROUP BY member.user_id, owner.username, owner.full_name, subject.id
               ORDER BY owner.full_name NULLS LAST, owner.username NULLS LAST""",
            str(user["sub"]),
        )
    except asyncpg.PostgresError as error:
        logger.exception("Failed to load shared users for user %s", user["sub"])
        raise HTTPException(status_code=503, detail="Shared users are temporarily unavailable") from error
    return [{
        "owner_id": str(row["owner_id"]), "subject_id": str(row["subject_id"]) if row["subject_id"] else None,
        "username": row["username"], "display_name": row["full_name"] or row["username"] or "Member",
        "can_access": bool(row["can_access"]), "group_names": list(row["group_names"] or []),
    } for row in rows]


@shared_router.get("/shared-memories/{owner_id}", response_model=list[MemoryFragment])
async def shared_memories(
    owner_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> list[MemoryFragment]:
    caller_id = str(user["sub"])
    if not await _can_access_owner(conn, caller_id, owner_id):
        raise HTTPException(status_code=403, detail="You do not have access to this memory map")
    rows = await conn.fetch("SELECT * FROM public.memories WHERE user_id = $1 ORDER BY created_at DESC", owner_id)
    return [_memory_from_row(row) for row in rows]


@shared_router.get("/shared-mind/{owner_id}")
async def shared_mind_model(
    owner_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict | None:
    if not await _can_access_owner(conn, str(user["sub"]), owner_id):
        raise HTTPException(status_code=403, detail="You do not have access to this Emmy")
    row = await conn.fetchrow(
        "SELECT model FROM public.mind_model_snapshots WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        owner_id,
    )
    return dict(row["model"]) if row else None


@shared_router.post("/chat/shared")
async def chat_with_shared_emmy(
    payload: SharedChatRequest,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
):
    """Compatibility endpoint for chatting with an authorised shared owner."""
    if not await _can_access_owner(conn, str(user["sub"]), payload.owner_id):
        raise HTTPException(status_code=403, detail="You do not have access to this Emmy")
    return await conversation(
        EmmyConversationRequest(
            question=payload.question,
            conversation_history=payload.conversation_history,
            subject_id=str(payload.owner_id),
        ),
        user,
        conn,
    )
