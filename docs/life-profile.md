# Life Profile: identity facts separate from memories

Emmy now uses two deliberately separate sources of knowledge:

1. **Life Profile (`identity_profiles`)** for stable, user-maintained facts such as name, family, profession, date of birth, values, and favourites.
2. **Semantic memory** in PostgreSQL plus Pinecone for stories, conversations, events, feelings, and advice.

Identity facts are never embedded or written to Pinecone. This prevents a correct name, spouse, occupation, or birth place from depending on a similarity-search result.

## API

- `GET /identity` creates a sparse owner row when necessary and returns the complete Life Profile.
- `PUT /identity` updates only the submitted fields. Sending `null` clears an optional text field.
- `GET /identity/{owner_id}` is available only to the owner or an accepted member of a group whose memory sharing is enabled. A group member receives only fields included in the ownerâ€™s `privacy_settings.shared_fields` allow-list.

The web page is `/life-profile`. It provides sections for basic details, family, values/favourites, and optional contact/health details, plus a per-field group-sharing control. Contact and health fields are private by default.

## Conversation routing

`IdentityService.classify_question()` routes questions to one of four paths:

| Intent | Examples | Behaviour |
| --- | --- | --- |
| `identity` | â€œWhat is your name?â€, â€œWho is your wife?â€, â€œHow old are you?â€ | Answers directly from `identity_profiles`; Pinecone is not queried. |
| `memory` | â€œWhat was your happiest memory?â€, â€œWhat advice did you leave?â€ | Uses the existing consent-scoped RAG pipeline. |
| `mixed` | â€œWhat did your wife think when you became a doctor?â€ | Adds authorised Life Profile facts and retrieved semantic memories to the prompt. |
| `general` | Non-specific questions | Uses normal memory retrieval, with Life Profile context available to the prompt. |

Prompt order is always: Identity Context, Persona Context, Retrieved Memories, then the latest user question. The streaming compatibility chat service uses the same classifier and context builder.

## Security model

Migration `023_identity_profiles.sql` enables RLS and allows direct table access only to the owner. This prevents a group member from bypassing field privacy with `select *`.

The public `get_shared_identity_profile(uuid)` RPC is a deliberately constrained, authenticated `SECURITY DEFINER` function: it verifies the caller is the owner or an accepted member of a group with active memory sharing, then emits only the fields in `shared_fields`. It has a fixed empty search path and cannot be called by `anon` or `PUBLIC`.

The FastAPI routes independently perform the same group-membership check and field filtering; frontend code does not query `identity_profiles` directly.

## Operations

- The table and all policies/triggers/functions in migration 023 use idempotent DDL (`IF NOT EXISTS`, `DROP â€¦ IF EXISTS`, or `CREATE OR REPLACE`) so the APIâ€™s migration runner can safely replay it.
- Existing rows and semantic memories are untouched.
- If no Life Profile fact exists, identity questions return a helpful Life Profile prompt rather than the semantic-memory fallback.


