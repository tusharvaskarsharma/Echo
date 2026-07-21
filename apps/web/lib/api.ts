import type { ConsentLevel, FamilyGroup, GroupMember, Memory, Profile, SharedUser } from "./types";
import { createClient } from "./supabase/client";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const request = async (endpoint: string, options: RequestInit = {}) => {
  const { data: { session } } = await createClient().auth.getSession();
  if (!session) throw new Error("You must be signed in.");
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.access_token}`,
    ...options.headers,
  };
  
  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers, credentials: "include" });
  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    throw new Error(payload?.detail || payload?.error || `API error: ${res.status} ${res.statusText}`);
  }
  if (res.status === 204) {
    return null;
  }
  return res.json();
};

const normalizeMemories = (memories: any[]): Memory[] => memories.map((memory: any, index: number) => ({
  ...memory,
  time_period: memory.time_period ?? "",
  recorded_at: memory.created_at ?? new Date().toISOString(),
  timestamp_seconds: 0,
  x: 20 + ((index * 31) % 60),
  y: 25 + ((index * 47) % 50),
}));

export const api = {
  profile: async (): Promise<Profile> => {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("You must be signed in.");
    // Auth metadata is always available to its owner.  Do not make the
    // dashboard depend on a direct `profiles` query, since a newly provisioned
    // Supabase project may not have its RLS migration applied yet.
    const metadata = user.user_metadata ?? {};
    return {
      id: user.id,
      name: metadata.full_name || metadata.name || user.email || "Your legacy",
      age: 0,
      voice: metadata.voice_preferences?.preset || "alloy",
      bio: metadata.bio || "Your private living legacy.",
      session_count: 0,
      memory_count: 0
    };
  },
  
  memories: async (): Promise<Memory[]> => {
    const memories = await request("/memories");
    return normalizeMemories(memories);
  },

  groups: (): Promise<FamilyGroup[]> => request("/groups"),
  createGroup: (name: string, description?: string): Promise<{ id: string; name: string }> => request("/groups", {
    method: "POST", body: JSON.stringify({ name, description: description || null }),
  }),
  updateGroup: (groupId: string, data: { name?: string; description?: string | null }): Promise<Pick<FamilyGroup, "id" | "name" | "description">> => request(`/groups/${groupId}`, {
    method: "PATCH", body: JSON.stringify(data),
  }),
  deleteGroup: (groupId: string): Promise<null> => request(`/groups/${groupId}`, { method: "DELETE" }),
  findGroupMember: (username: string): Promise<Pick<GroupMember, "user_id" | "username" | "display_name">> => request(`/groups/member-candidates?username=${encodeURIComponent(username)}`),
  addGroupMember: (groupId: string, username: string): Promise<GroupMember> => request(`/groups/${groupId}/members`, {
    method: "POST", body: JSON.stringify({ username }),
  }),
  removeGroupMember: (groupId: string, memberId: string): Promise<null> => request(`/groups/${groupId}/members/${memberId}`, { method: "DELETE" }),
  updateGroupSharing: (groupId: string, share_memories: boolean): Promise<{ group_id: string; share_memories: boolean }> => request(`/groups/${groupId}/sharing`, {
    method: "PATCH", body: JSON.stringify({ share_memories }),
  }),
  sharedUsers: (): Promise<SharedUser[]> => request("/shared-users"),
  sharedMemories: async (ownerId: string): Promise<Memory[]> => normalizeMemories(await request(`/shared-memories/${ownerId}`)),
  sharedMind: (ownerId: string): Promise<any> => request(`/shared-mind/${ownerId}`),
  
  patchMemory: async (id: string, consent: ConsentLevel): Promise<Memory> => {
    return request(`/memories/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ consent_level: consent })
    });
  },
  
  createSession: async (): Promise<{ id: string }> => {
    return request("/sessions", {
      method: "POST",
      body: JSON.stringify({})
    });
  },
  
  finishSession: async (sessionId: string) => {
    return request(`/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "completed" })
    });
  },

  uploadSessionAudio: async (sessionId: string, audio: Blob) => {
    const { data: { session } } = await createClient().auth.getSession();
    if (!session) throw new Error("You must be signed in.");
    const form = new FormData();
    form.append("audio", audio, "echo-session.webm");
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/audio`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${session.access_token}` },
      body: form,
      credentials: "include",
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || payload?.error || "Unable to upload the session recording.");
    }
    return response.json();
  },
  
  createDraft: async (sessionId: string, data: any) => {
    return request("/memories/draft", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, ...data })
    });
  },

  saveConversation: async (content: string): Promise<Memory> => {
    return request("/memories/conversation", {
      method: "POST",
      body: JSON.stringify({ content })
    });
  }
};
