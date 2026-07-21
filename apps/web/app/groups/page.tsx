"use client";

import { FormEvent, useEffect, useState } from "react";
import { Check, LoaderCircle, Pencil, Plus, Trash2, UserMinus, Users, X } from "lucide-react";

import { AppNav } from "../../components/AppNav";
import { api } from "../../lib/api";
import type { FamilyGroup, GroupMember } from "../../lib/types";

type Notice = { type: "error" | "success"; text: string } | null;

export default function GroupsPage() {
  const [groups, setGroups] = useState<FamilyGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [inviteFor, setInviteFor] = useState<string | null>(null);
  const [inviteUsername, setInviteUsername] = useState("");
  const [candidate, setCandidate] = useState<Pick<GroupMember, "user_id" | "username" | "display_name"> | null>(null);
  const [searching, setSearching] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [working, setWorking] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try { setGroups(await api.groups()); }
    catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Unable to load groups." }); }
    finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, []);

  useEffect(() => {
    const username = inviteUsername.trim().toLowerCase();
    setCandidate(null);
    if (!inviteFor || username.length < 3 || !/^[a-z0-9_]{3,30}$/.test(username)) { setSearching(false); return; }
    let cancelled = false;
    setSearching(true);
    const timer = window.setTimeout(async () => {
      try {
        const found = await api.findGroupMember(username);
        if (!cancelled) setCandidate(found);
      } catch { /* The confirmation card remains hidden for unknown users. */ }
      finally { if (!cancelled) setSearching(false); }
    }, 350);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [inviteFor, inviteUsername]);

  const createGroup = async (event: FormEvent) => {
    event.preventDefault();
    if (!newName.trim()) return;
    setWorking("create"); setNotice(null);
    try {
      await api.createGroup(newName.trim(), newDescription.trim());
      setNewName(""); setNewDescription(""); setCreating(false);
      setNotice({ type: "success", text: "Family group created." });
      await load();
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Unable to create the group." }); }
    finally { setWorking(null); }
  };

  const updateSharing = async (group: FamilyGroup, checked: boolean) => {
    setWorking(`sharing-${group.id}`); setNotice(null);
    try {
      await api.updateGroupSharing(group.id, checked);
      setGroups((current) => current.map((item) => item.id === group.id ? { ...item, share_memories: checked } : item));
      setNotice({ type: "success", text: checked ? `Your memory map is now shared with ${group.name}.` : `Your memory map is private from ${group.name}.` });
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Unable to update sharing." }); }
    finally { setWorking(null); }
  };

  const addMember = async () => {
    if (!inviteFor || !candidate) return;
    setWorking(`invite-${inviteFor}`); setNotice(null);
    try {
      await api.addGroupMember(inviteFor, candidate.username || "");
      setInviteFor(null); setInviteUsername(""); setCandidate(null);
      setNotice({ type: "success", text: `${candidate.display_name} has been added to the group.` });
      await load();
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Unable to add this member." }); }
    finally { setWorking(null); }
  };

  const removeMember = async (group: FamilyGroup, member: GroupMember) => {
    const action = member.user_id === group.owner_id ? "delete this group" : member.is_current_user ? "leave" : "remove this member";
    if (!window.confirm(`Are you sure you want to ${action}?`)) return;
    setWorking(`member-${group.id}-${member.user_id}`); setNotice(null);
    try {
      await api.removeGroupMember(group.id, member.user_id);
      setNotice({ type: "success", text: member.user_id === group.owner_id ? "Group deleted." : "Group membership updated." });
      await load();
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Unable to update membership." }); }
    finally { setWorking(null); }
  };

  const deleteGroup = async (group: FamilyGroup) => {
    if (!window.confirm(`Delete “${group.name}”? This revokes its memory access immediately.`)) return;
    setWorking(`delete-${group.id}`); setNotice(null);
    try { await api.deleteGroup(group.id); setNotice({ type: "success", text: "Group deleted and sharing revoked." }); await load(); }
    catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Unable to delete the group." }); }
    finally { setWorking(null); }
  };

  const renameGroup = async (group: FamilyGroup) => {
    const name = window.prompt("New group name", group.name)?.trim();
    if (!name || name === group.name) return;
    setWorking(`rename-${group.id}`); setNotice(null);
    try {
      const updated = await api.updateGroup(group.id, { name });
      setGroups((current) => current.map((item) => item.id === group.id ? { ...item, name: updated.name, description: updated.description } : item));
      setNotice({ type: "success", text: "Group renamed." });
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Unable to rename the group." }); }
    finally { setWorking(null); }
  };

  return <><AppNav /><main className="min-h-[calc(100vh-5rem)] bg-[radial-gradient(circle_at_12%_0%,#f1e4da_0,transparent_28%),#f8f6f2] px-4 py-8 sm:px-8">
    <div className="mx-auto max-w-5xl">
      <header className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Private sharing</p><h1 className="mt-2 font-serif text-5xl text-text">Family Groups</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-text/65">Share your complete Echo memory map only with the family groups you choose. Access is revoked immediately when sharing is turned off or membership changes.</p></div><button type="button" onClick={() => setCreating((value) => !value)} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-4 py-3 text-sm font-semibold text-white shadow-sm hover:brightness-110"><Plus size={17} /> Create group</button></header>
      {notice && <p className={`mb-5 rounded-2xl border px-4 py-3 text-sm ${notice.type === "error" ? "border-red-200 bg-red-50 text-red-700" : "border-success/30 bg-green-50 text-green-800"}`} role={notice.type === "error" ? "alert" : "status"}>{notice.type === "success" && <Check className="mr-2 inline" size={16} />}{notice.text}</p>}
      {creating && <form onSubmit={createGroup} className="mb-6 rounded-[26px] border border-primary/15 bg-white/85 p-5 shadow-sm"><div className="flex items-center justify-between"><h2 className="font-serif text-2xl text-text">New family group</h2><button type="button" onClick={() => setCreating(false)} className="rounded-lg p-1.5 text-text/55 hover:bg-primary/10"><X size={18} /></button></div><div className="mt-4 grid gap-3 sm:grid-cols-2"><input required value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="e.g. Sharma Family" className="rounded-xl border border-primary/15 bg-white px-3.5 py-3 text-sm outline-none focus:ring-4 focus:ring-primary/10" /><input value={newDescription} onChange={(event) => setNewDescription(event.target.value)} placeholder="Optional description" className="rounded-xl border border-primary/15 bg-white px-3.5 py-3 text-sm outline-none focus:ring-4 focus:ring-primary/10" /></div><button disabled={working === "create"} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{working === "create" && <LoaderCircle className="animate-spin" size={16} />}Create private group</button></form>}
      {loading ? <div className="flex justify-center py-24 text-text/55"><LoaderCircle className="animate-spin" /></div> : groups.length === 0 ? <section className="rounded-[30px] border border-dashed border-primary/25 bg-white/60 px-6 py-16 text-center"><Users className="mx-auto text-primary" size={30} /><h2 className="mt-4 font-serif text-3xl text-text">Your groups stay private.</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-text/60">Create a group to choose exactly who can visit your Echo. No memories are shared until you turn sharing on.</p></section> : <div className="grid gap-5 lg:grid-cols-2">{groups.map((group) => <section key={group.id} className="rounded-[28px] border border-primary/10 bg-white/80 p-5 shadow-[0_12px_35px_rgba(96,60,43,.07)]"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">{group.role === "owner" ? "Your group" : `Owned by ${group.owner_name}`}</p><h2 className="mt-1 font-serif text-3xl text-text">{group.name}</h2>{group.description && <p className="mt-2 text-sm text-text/60">{group.description}</p>}</div>{group.role === "owner" && <div className="flex gap-1"><button type="button" onClick={() => void renameGroup(group)} disabled={working === `rename-${group.id}`} className="rounded-xl p-2 text-text/55 hover:bg-primary/10 hover:text-primary" aria-label={`Rename ${group.name}`}><Pencil size={17} /></button><button type="button" onClick={() => void deleteGroup(group)} disabled={working === `delete-${group.id}`} className="rounded-xl p-2 text-red-600 hover:bg-red-50" aria-label={`Delete ${group.name}`}><Trash2 size={17} /></button></div>}</div>
        {group.role === "owner" && <label className="mt-5 flex cursor-pointer items-center justify-between rounded-2xl border border-primary/12 bg-primary/5 px-4 py-3"><span><span className="block text-sm font-semibold text-text">Share my memory map</span><span className="block text-xs text-text/55">Members can explore and chat with your Echo.</span></span><input type="checkbox" checked={group.share_memories} disabled={working === `sharing-${group.id}`} onChange={(event) => void updateSharing(group, event.target.checked)} className="h-4 w-4 accent-primary" /></label>}
        <div className="mt-5 border-t border-primary/10 pt-4"><div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-text/45">Members · {group.member_count}</p>{group.role === "owner" && <button type="button" onClick={() => { setInviteFor(group.id); setInviteUsername(""); }} className="text-xs font-semibold text-primary hover:underline">Add by username</button>}</div><ul className="mt-3 space-y-2">{group.members.map((member) => <li key={member.user_id} className="flex items-center justify-between gap-3 rounded-xl bg-[#fbf8f5] px-3 py-2.5"><span><span className="block text-sm font-medium text-text">{member.display_name}</span><span className="block text-xs text-text/50">@{member.username || "pending"} · {member.role}</span></span>{group.role === "owner" && member.role !== "owner" && <button type="button" onClick={() => void removeMember(group, member)} disabled={working === `member-${group.id}-${member.user_id}`} className="rounded-lg p-1.5 text-text/45 hover:bg-red-50 hover:text-red-600" aria-label={`Remove ${member.display_name}`}><UserMinus size={16} /></button>}</li>)}</ul></div>
        {group.role === "member" && <button type="button" onClick={() => { const self = group.members.find((member) => member.is_current_user); if (self) void removeMember(group, self); }} className="mt-5 text-sm font-semibold text-red-700 hover:underline">Leave group</button>}
      </section>)}</div>}
      {inviteFor && <div className="fixed inset-0 z-50 grid place-items-center bg-black/30 p-4"><section className="w-full max-w-md rounded-[28px] bg-white p-6 shadow-2xl"><div className="flex items-center justify-between"><h2 className="font-serif text-3xl text-text">Add family member</h2><button onClick={() => setInviteFor(null)} className="rounded-lg p-1.5 text-text/55 hover:bg-primary/10"><X size={18} /></button></div><p className="mt-2 text-sm text-text/60">Enter their exact username. We’ll confirm who you are adding before changing the group.</p><input autoFocus value={inviteUsername} onChange={(event) => setInviteUsername(event.target.value.trim().toLowerCase())} placeholder="username" className="mt-4 w-full rounded-xl border border-primary/15 px-3.5 py-3 text-sm outline-none focus:ring-4 focus:ring-primary/10" />{searching && <p className="mt-3 text-sm text-text/50"><LoaderCircle className="mr-2 inline animate-spin" size={15} />Finding account…</p>}{candidate && <div className="mt-4 rounded-2xl border border-success/25 bg-green-50 p-4"><p className="font-medium text-text">{candidate.display_name}</p><p className="text-sm text-text/60">@{candidate.username}</p><button disabled={working === `invite-${inviteFor}`} type="button" onClick={() => void addMember()} className="mt-3 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white">Confirm and add</button></div>}{inviteUsername.length >= 3 && !searching && !candidate && <p className="mt-3 text-sm text-text/50">Use an existing username with 3–30 lowercase letters, numbers, or underscores.</p>}</section></div>}
    </div>
  </main></>;
}
