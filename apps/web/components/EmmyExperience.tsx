"use client";

import { FormEvent, useEffect, useState } from "react";
import { LoaderCircle, Send, Volume2 } from "lucide-react";

import { API_BASE, api } from "../lib/api";
import { createClient } from "../lib/supabase/client";

type Citation = { memory_id: string; excerpt: string; timestamp: string };
type Turn = { id: string; author: "you" | "emmy"; text: string; citations?: Citation[]; error?: boolean };
type SharedOwner = { owner_id: string; display_name: string };

export function EmmyExperience() {
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([{ id: "welcome", author: "emmy", text: "I’m here to continue the stories you chose to preserve. What would you like to talk about?" }]);
  const [owners, setOwners] = useState<SharedOwner[]>([]);
  const [ownerId, setOwnerId] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => { void api.sharedUsers().then(setOwners).catch(() => setOwners([])); }, []);

  const speak = (text: string) => {
    window.speechSynthesis?.cancel();
    window.speechSynthesis?.speak(new SpeechSynthesisUtterance(text));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const question = draft.trim();
    if (!question || sending) return;
    const history = turns.slice(-12).map((turn) => ({ role: turn.author === "you" ? "user" : "emmy", text: turn.text }));
    setDraft("");
    setSending(true);
    setTurns((current) => [...current, { id: `you-${Date.now()}`, author: "you", text: question }]);
    try {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) throw new Error("Please sign in to talk with Emmy.");
      const response = await fetch(`${API_BASE}${ownerId ? "/chat/shared" : "/api/emmy/conversation"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify(ownerId ? { question, conversation_history: history, owner_id: ownerId } : { question, conversation_history: history }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail || "Emmy could not respond right now.");
      const answer = { id: `emmy-${Date.now()}`, author: "emmy" as const, text: payload.text, citations: payload.citations as Citation[] | undefined };
      setTurns((current) => [...current, answer]);
      speak(answer.text);
    } catch (error) {
      setTurns((current) => [...current, { id: `error-${Date.now()}`, author: "emmy", text: error instanceof Error ? error.message : "Emmy could not respond right now.", error: true }]);
    } finally {
      setSending(false);
    }
  };

  return <main className="emmy-experience min-h-[calc(100vh-5rem)] bg-[radial-gradient(circle_at_92%_6%,#f2e3d8_0,transparent_24%),#f8f6f2] px-4 py-5 sm:px-8">
    <section className="mx-auto max-w-5xl rounded-[32px] border border-primary/10 bg-white/75 shadow-clay">
      <header className="flex flex-col justify-between gap-4 border-b border-primary/10 px-6 py-6 sm:flex-row sm:items-end sm:px-8"><div><p className="text-xs font-semibold uppercase tracking-[.2em] text-primary">Your preserved presence</p><h1 className="mt-2 font-serif text-4xl text-text sm:text-5xl">Talk with Emmy</h1><p className="mt-2 max-w-xl text-sm leading-6 text-text/65">Grounded in the Life Profile and stories you chose to preserve.</p></div><label className="text-sm text-text/65"><span className="mr-2 text-xs font-semibold uppercase tracking-wide text-primary">Memory source</span><select className="rounded-xl border border-primary/15 bg-white px-3 py-2 outline-none" value={ownerId} onChange={(event) => setOwnerId(event.target.value)}><option value="">My memories</option>{owners.map((owner) => <option key={owner.owner_id} value={owner.owner_id}>{owner.display_name}</option>)}</select></label></header>
      <div className="min-h-[430px] space-y-4 px-5 py-6 sm:px-8" aria-live="polite">{turns.map((turn) => <article key={turn.id} className={`flex ${turn.author === "you" ? "justify-end" : "justify-start"}`}><div className={`max-w-[86%] rounded-2xl px-4 py-3 ${turn.author === "you" ? "bg-primary text-white" : "border border-primary/10 bg-[#fffaf7] text-text"}`}><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide"><span>{turn.author === "you" ? "You" : "Emmy"}</span>{turn.author === "emmy" && <button type="button" onClick={() => speak(turn.text)} aria-label="Play Emmy response"><Volume2 size={14} /></button>}</div><p className={`mt-2 whitespace-pre-wrap text-sm leading-6 ${turn.error ? "text-red-700" : ""}`}>{turn.text}</p>{turn.citations?.length ? <details className="mt-3 border-t border-primary/10 pt-2 text-xs"><summary className="cursor-pointer font-semibold text-primary">Sources ({turn.citations.length})</summary>{turn.citations.map((citation) => <p key={citation.memory_id} className="mt-2 text-text/65">“{citation.excerpt}”</p>)}</details> : null}</div></article>)}</div>
      <form onSubmit={submit} className="border-t border-primary/10 p-4 sm:p-5"><label className="sr-only" htmlFor="emmy-question">Ask Emmy a question</label><div className="flex items-end gap-3 rounded-2xl border border-primary/15 bg-white p-2 pl-4"><textarea id="emmy-question" className="min-h-12 flex-1 resize-none bg-transparent py-2 text-sm outline-none" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about a memory, lesson, or moment…" rows={2} disabled={sending} /><button type="submit" disabled={sending || !draft.trim()} className="inline-flex h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-white disabled:opacity-50">{sending ? <LoaderCircle className="animate-spin" size={16} /> : <Send size={16} />}{sending ? "Remembering" : "Ask Emmy"}</button></div></form>
    </section>
  </main>;
}
