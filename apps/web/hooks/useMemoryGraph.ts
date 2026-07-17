import useSWR from 'swr';
import { API_BASE } from '../lib/api';
import { createClient } from '../lib/supabase/client';

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
}

export function useMemoryGraph() {
  const { data: memories, error, mutate } = useSWR<Memory[]>(`${API_BASE}/memories`, fetcher);

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
      await fetch(`${API_BASE}/memories/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await accessToken()}`
        },
        body: JSON.stringify({ consent_level })
      });
    } catch (e) {
      console.error("Failed to patch consent", e);
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
