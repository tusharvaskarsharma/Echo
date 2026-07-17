import type { ConsentLevel, Memory, Profile } from "./types";
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
    return request("/memories");
  },
  
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
  
  createDraft: async (sessionId: string, data: any) => {
    return request("/memories/draft", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, ...data })
    });
  }
};
