import useSWR from 'swr';
import { API_BASE } from '../lib/api';
import { createClient } from '../lib/supabase/client';
import { useEffect } from 'react';

const accessToken = async () => {
  const { data: { session } } = await createClient().auth.getSession();
  if (!session) throw new Error("You must be signed in.");
  return session.access_token;
};
const fetcher = async (url: string) => {
  const response = await fetch(url, { headers: { Authorization: `Bearer ${await accessToken()}` } });
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
};

export interface Memory {
  id: string;
  content: string;
  emotion_tags: string[];
  topics: string[];
  people_mentioned: string[];
  time_period: string;
  consent_level: 'private' | 'family' | 'legacy';
  confidence_score: number;
  session_id: string;
  search_document?: string | null;
  semantic_metadata?: {
    title?: string;
    keywords?: string[];
  };
}

export function useMemoryGraph() {
  const { data: memories, error, mutate } = useSWR<Memory[]>(`${API_BASE}/memories`, fetcher);

  useEffect(() => {
    const supabase = createClient();
    let channel: ReturnType<typeof supabase.channel> | undefined;
    let active = true;
    void supabase.auth.getUser().then(({ data }) => {
      if (!active || !data.user) return;
      channel = supabase.channel(`memory-graph:${data.user.id}`)
        .on("postgres_changes", { event: "*", schema: "public", table: "memories", filter: `user_id=eq.${data.user.id}` }, () => { void mutate(); })
        .subscribe();
    });
    return () => { active = false; if (channel) void supabase.removeChannel(channel); };
  }, [mutate]);

  const patchConsent = async (id: string, consent_level: string) => {
    // Optimistic update
    if (memories) {
      mutate(
        memories.map(m => m.id === id ? { ...m, consent_level: consent_level as any } : m),
        false
      );
    }
    
    // API Call
    try {
      const response = await fetch(`${API_BASE}/memories/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await accessToken()}`
        },
        body: JSON.stringify({ consent_level })
      });
      if (!response.ok) throw new Error("Unable to update consent");
    } catch (e) {
      console.error("Failed to patch consent", e);
      if (memories) mutate(memories, false);
    }
    
    // Revalidate
    mutate();
  };

  return {
    memories,
    isLoading: !error && !memories,
    isError: error,
    patchConsent
  };
}
