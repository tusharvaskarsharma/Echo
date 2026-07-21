"use client";

import { FormEvent, useRef, useState } from "react";
import { ChevronDown, Heart, Mic, Send, Sparkles } from "lucide-react";

import { API_BASE } from "../lib/api";
import { createClient } from "../lib/supabase/client";

type Source = { memory_id: string; excerpt: string; session_id: string; timestamp: string };
type Turn = { id: string; speaker: "family" | "emmy"; text: string; sources?: Source[]; error?: boolean };

export function ConversationClient({ emmyId }: { emmyId: string }) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([{ id: "welcome", speaker: "emmy", text: "Hello. I’m here to share only the stories that were entrusted to me. What would you like to ask?" }]);
  const [sending, setSending] = useState(false);
  const recognition = useRef<{ start: () => void } | null>(null);

  const startVoiceInput = () => {
    const BrowserRecognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!BrowserRecognition) return;
    const instance = new BrowserRecognition();
    instance.onresult = (event: SpeechRecognitionEvent) => setQuestion(event.results[0][0].transcript);
    recognition.current = instance;
    instance.start();
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const asked = question.trim();
    if (!asked || sending) return;
    const answerId = `emmy-${Date.now()}`;
    setQuestion("");
    setSending(true);
    setTurns((current) => [...current, { id: `family-${Date.now()}`, speaker: "family", text: asked }, { id: answerId, speaker: "emmy", text: "" }]);
    try {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) throw new Error("Please sign in to continue.");
      const body = new FormData();
      body.append("text", asked);
      const response = await fetch(`${API_BASE}/emmy/${encodeURIComponent(emmyId)}/converse`, { method: "POST", headers: { Authorization: `Bearer ${session.access_token}`, Accept: "text/event-stream" }, body });
      if (!response.ok || !response.body) throw new Error("Emmy could not start a response.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let complete = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const raw = frame.match(/^data:\s*(.+)$/m)?.[1];
          if (!raw) continue;
          const payload = JSON.parse(raw);
          if (payload.type === "text") { complete += payload.text; setTurns((current) => current.map((turn) => turn.id === answerId ? { ...turn, text: complete } : turn)); }
          if (payload.type === "sources") setTurns((current) => current.map((turn) => turn.id === answerId ? { ...turn, sources: payload.sources } : turn));
          if (payload.type === "error") setTurns((current) => current.map((turn) => turn.id === answerId ? { ...turn, text: payload.message, error: true } : turn));
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Emmy could not reach the memory archive.";
      setTurns((current) => current.map((turn) => turn.id === answerId ? { ...turn, text: message, error: true } : turn));
    } finally { setSending(false); }
  };

  return <main className="min-h-[calc(100vh-5rem)] bg-[radial-gradient(circle_at_75%_5%,#f1e1d6_0,transparent_25%),#f8f6f2] px-4 py-7 sm:px-7"><section className="mx-auto grid max-w-6xl gap-5 lg:grid-cols-[minmax(0,1fr)_300px]"><div className="overflow-hidden rounded-[30px] border border-primary/10 bg-white/75 shadow-clay"><header className="border-b border-primary/10 px-6 py-6 sm:px-8"><div className="flex items-center gap-3 text-primary"><Heart size={18} fill="currentColor" /><p className="text-xs font-semibold uppercase tracking-[.2em]">A family conversation</p></div><h1 className="mt-3 font-serif text-4xl text-text sm:text-5xl">A voice held in memory.</h1><p className="mt-3 text-sm leading-6 text-text/65">Every answer is grounded in consented memories. When Emmy does not know, Emmy will say so.</p></header><div className="max-h-[58vh] min-h-[420px] space-y-5 overflow-y-auto px-5 py-6 sm:px-8" aria-live="polite">{turns.map((turn) => <article key={turn.id} className={`flex gap-3 ${turn.speaker === "family" ? "justify-end" : "justify-start"}`}><div className={`max-w-[84%] rounded-3xl px-5 py-4 shadow-sm ${turn.speaker === "family" ? "bg-primary text-white" : "border border-primary/10 bg-[#fdf7f3] text-text"}`}><p className="text-xs font-semibold uppercase tracking-wide">{turn.speaker === "family" ? "You" : "Emmy"}</p><p className={`mt-2 whitespace-pre-wrap text-[15px] leading-7 ${turn.error ? "text-red-600" : ""}`}>{turn.text || <span className="inline-flex items-center gap-2 text-text/50"><Sparkles size={16} className="animate-pulse" />Searching memories…</span>}</p>{turn.sources?.length ? <details className="mt-4 border-t border-primary/10 pt-3"><summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-semibold text-primary">Memories used ({turn.sources.length}) <ChevronDown size={16} /></summary>{turn.sources.map((source) => <p key={source.memory_id} className="mt-2 text-sm text-text/65">“{source.excerpt}”</p>)}</details> : null}</div></article>)}</div><form onSubmit={submit} className="border-t border-primary/10 p-4 sm:p-5"><label htmlFor="family-question" className="sr-only">Ask Emmy a question</label><div className="flex items-end gap-3 rounded-2xl border border-primary/15 bg-white p-2 pl-4"><textarea id="family-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about a memory, lesson, or moment…" rows={2} disabled={sending} className="min-h-[48px] flex-1 resize-none bg-transparent py-2 text-sm outline-none" /><button type="button" onClick={startVoiceInput} className="hidden h-10 w-10 items-center justify-center rounded-xl text-primary sm:inline-flex" aria-label="Speak your question"><Mic size={18} /></button><button type="submit" disabled={sending || !question.trim()} className="inline-flex h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-white disabled:opacity-40"><Send size={16} />{sending ? "Remembering" : "Ask Emmy"}</button></div></form></div></section></main>;
}

declare global {
  interface Window { SpeechRecognition?: new () => SpeechRecognition; webkitSpeechRecognition?: new () => SpeechRecognition; }
  interface SpeechRecognition extends EventTarget { start(): void; onresult: ((event: SpeechRecognitionEvent) => void) | null; }
  interface SpeechRecognitionEvent extends Event { results: { [index: number]: { [index: number]: { transcript: string } } }; }
}
