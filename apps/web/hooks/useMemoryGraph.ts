import useSWR from 'swr';
import { API_BASE } from '../lib/api';

const fetcher = (url: string) => fetch(url, {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}` // simple fallback for auth
  }
}).then(res => res.json());

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
          'Authorization': `Bearer ${localStorage.getItem('token')}`
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