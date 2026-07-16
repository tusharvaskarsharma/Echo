import type { ConsentLevel, Memory, Profile } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

const request = async (endpoint: string, options: RequestInit = {}) => {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer demo-token',
    ...options.headers,
  };
  
  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
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
    // For demo purposes, returning a stubbed profile
    return {
      id: "eleanor-74",
      name: "Eleanor",
      age: 74,
      voice: "grandma",
      bio: "Grandmother, retired teacher, loves gardening.",
      session_count: 1,
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
    // Fake draft response for the simulator
    return { id: "draft-123" };
  }
};