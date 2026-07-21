# Family Groups

Family Groups let an Echo owner grant their complete memory map to selected groups. Memories remain private unless the owner enables sharing for a specific group.

## Security model

- Every invitation uses the recipient's canonical username, never their email address.
- `groups`, `group_members`, and `memory_permissions` have foreign keys, indexes, and row-level security policies in migration `020_family_groups.sql`.
- A database trigger ensures a group can grant only its owner's memory map, and only the actual owner can hold the `owner` member role.
- The API checks authenticated membership for every group, shared-memory, shared-mind, and shared-chat request. The selected owner from the browser is only a selector, never authority.
- Echo resolves the target owner before retrieval. It queries that owner's subject namespace only and scopes citations and Mind Model reads to that owner.

## Deployment

The API migration runner applies `apps/api/app/db/migrations/020_family_groups.sql` during backend startup. Deploy the API before using the new web UI, then deploy the web service. No worker, Redis, or Celery service is required.

## User flow

1. New accounts choose a 3–30 character lowercase username at signup. Existing users without a username are redirected to onboarding.
2. An owner creates a group, confirms an exact username search, and adds members.
3. The owner turns on **Share my memory map** for that group.
4. Members choose the owner's name under **Memory source** in Echo. Switching source resets conversation history and uses only the selected, permitted owner context.
