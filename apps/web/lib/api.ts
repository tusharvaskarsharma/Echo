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
    throw new Error(`API error: ${res.statusText}`);
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
    const { data, error } = await supabase.from("profiles").select("full_name,bio,voice_preferences").eq("id", user.id).single();
    if (error) throw error;
    return {
      id: user.id,
      name: data.full_name || user.email || "Your legacy",
      age: 0,
      voice: data.voice_preferences?.preset || "alloy",
      bio: data.bio || "Your private living legacy.",
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
