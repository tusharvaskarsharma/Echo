"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export default function OnboardingPage() {
  const router = useRouter(); const [username, setUsername] = useState(""); const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(""); const canonicalUsername = username.trim().toLowerCase();
    if (!/^[a-z0-9_]{3,30}$/.test(canonicalUsername)) { setError("Use 3–30 lowercase letters, numbers, or underscores."); return; }
    setSaving(true);
    try {
      const supabase = createClient(); const { data: { user } } = await supabase.auth.getUser(); const { data: { session } } = await supabase.auth.getSession();
      if (!user || !session) throw new Error("Please sign in again.");
      const response = await fetch(`${API_BASE}/profile`, { method: "PUT", headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` }, body: JSON.stringify({ username: canonicalUsername, full_name: user.user_metadata?.full_name || null, confirm_username_change: true }) });
      const result = await response.json().catch(() => null); if (!response.ok) throw new Error(result?.detail || "Unable to save username.");
      router.replace("/subject/dashboard"); router.refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to save username."); } finally { setSaving(false); }
  };
  return <main className="min-h-screen bg-[radial-gradient(circle_at_15%_0%,#f1e4da_0,transparent_30%),#f8f6f2] px-5 py-16"><form onSubmit={submit} className="mx-auto max-w-md rounded-[30px] border border-primary/12 bg-white/85 p-8 shadow-clay"><p className="text-xs font-semibold uppercase tracking-[.2em] text-primary">One quick step</p><h1 className="mt-3 font-serif text-5xl text-text">Choose your username</h1><p className="mt-4 text-sm leading-6 text-text/65">Family groups use a username instead of an email address, keeping your contact details private.</p>{error && <p className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</p>}<input autoFocus required minLength={3} maxLength={30} pattern="[a-z0-9_]+" value={username} onChange={(event) => setUsername(event.target.value.toLowerCase().replace(/\s/g, ""))} placeholder="username" className="mt-6 w-full rounded-xl border border-primary/15 px-3.5 py-3 text-sm outline-none focus:ring-4 focus:ring-primary/10" /><p className="mt-2 text-xs text-text/50">3–30 lowercase letters, numbers, or underscores.</p><button disabled={saving} className="mt-6 w-full rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{saving ? "Saving…" : "Continue to Echo"}</button></form></main>;
}
