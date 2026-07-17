"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { ConsentLevel, Memory, Profile } from "../lib/types";
import { MemoryGraph } from "./MemoryGraph";

export function MemoryExperience({ compact = false }: { compact?: boolean }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { Promise.all([api.profile(), api.memories()]).then(([nextProfile, nextMemories]) => { setProfile(nextProfile); setMemories(nextMemories); }).catch(() => setError("Echo's demo API is not running yet. Start FastAPI on port 8000.")); }, []);
  const updateConsent = async (id: string, consent: ConsentLevel) => {
    const previous = memories;
    setMemories((items) => items.map((item) => item.id === id ? { ...item, consent_level: consent } : item));
    try { await api.patchMemory(id, consent); } catch { setMemories(previous); setError("The consent change could not be saved."); }
  };
  if (error) return <div className="error-card">{error}</div>;
  if (!profile) return <div className="loading-card">Opening Eleanor&apos;s constellation…</div>;
  return <>
    {!compact && (
      <section className="subject-hero">
        <div className="hero-content">
          <p className="eyebrow">Your living legacy</p>
          <h1>{profile.name}</h1>
          <p className="bio">{profile.bio}</p>
        </div>
        <div className="stat-stack">
          <div className="stat-item">
            <strong>{profile.session_count}</strong>
            <span>recorded sessions</span>
          </div>
          <div className="stat-divider"></div>
          <div className="stat-item">
            <strong>{memories.length}</strong>
            <span>memories held with care</span>
          </div>
        </div>
      </section>
    )}
    <MemoryGraph memories={memories} onConsent={updateConsent} />
  </>;
}

