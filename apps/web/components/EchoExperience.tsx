"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Headphones, Mic, RotateCcw, Send, Sparkles, Volume2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { API_BASE, api } from "../lib/api";
import { createClient } from "../lib/supabase/client";

type Citation = { memory_id: string; excerpt: string; session_id: string; timestamp: string };
type Explainability = { retrieved_memories: string[]; mind_traits: string[]; reasoning_summary: string; timeline: string };
type Turn = { id: string; author: "you" | "echo"; text: string; timestamp: Date; confidence?: number; citations?: Citation[]; emotion?: string; explanation?: Explainability; audioUrl?: string | null; error?: boolean };
type Phase = "idle" | "listening" | "retrieving" | "mind" | "reasoning" | "speaking";
type Mind = { values: unknown[]; beliefs: unknown[]; personality: unknown[]; life_lessons: unknown[] } | null;

const phaseCopy: Record<Phase, string> = {
  idle: "Here when you are.", listening: "Listening…", retrieving: "Searching memories…", mind: "Understanding your values…", reasoning: "Building a response…", speaking: "Speaking…",
};

const phaseLabel: Record<Phase, string> = {
  idle: "Idle", listening: "Listening", retrieving: "Retrieving memories", mind: "Loading Mind Model", reasoning: "Reasoning", speaking: "Speaking",
};

function displayTime(date: Date) { return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }); }

export function EchoExperience() {
  const searchParams = useSearchParams();
  const subjectId = searchParams.get("subject_id");
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([{ id: "welcome", author: "echo", text: "I’m here to continue the stories you chose to preserve. What would you like to talk about?", timestamp: new Date(), confidence: 1, emotion: "reflective" }]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [sending, setSending] = useState(false);
  const [mind, setMind] = useState<Mind>(null);
  const [memoryCount, setMemoryCount] = useState(0);
  const recognition = useRef<SpeechRecognition | null>(null);
  const speech = useRef<SpeechSynthesisUtterance | null>(null);
  const pendingTimers = useRef<number[]>([]);

  const latestEcho = useMemo(() => [...turns].reverse().find((turn) => turn.author === "echo"), [turns]);
  const traitCount = mind ? mind.values.length + mind.beliefs.length + mind.personality.length : 0;
  const lessonCount = mind?.life_lessons.length ?? 0;

  useEffect(() => {
    let mounted = true;
    Promise.all([api.memories(), (async () => {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) return null;
      const response = await fetch(`${API_BASE}/mind/latest`, { headers: { Authorization: `Bearer ${session.access_token}` } });
      return response.ok ? response.json() : null;
    })()]).then(([memories, model]) => {
      if (!mounted) return;
      setMemoryCount(memories.length); setMind(model as Mind);
    }).catch(() => undefined);
    return () => { mounted = false; pendingTimers.current.forEach(window.clearTimeout); window.speechSynthesis?.cancel(); };
  }, []);

  const play = (turn: Turn) => {
    window.speechSynthesis?.cancel();
    if (turn.audioUrl) { const audio = new Audio(turn.audioUrl); void audio.play(); return; }
    const utterance = new SpeechSynthesisUtterance(turn.text);
    utterance.rate = 0.96; utterance.pitch = 0.94;
    speech.current = utterance; window.speechSynthesis?.speak(utterance);
  };

  const sendQuestion = async (question: string) => {
    const asked = question.trim();
    if (!asked || sending) return;
    setDraft(""); setSending(true); setPhase("listening");
    const userTurn: Turn = { id: `you-${Date.now()}`, author: "you", text: asked, timestamp: new Date() };
    setTurns((current) => [...current, userTurn]);
    pendingTimers.current.forEach(window.clearTimeout);
    pendingTimers.current = [
      window.setTimeout(() => setPhase("retrieving"), 350),
      window.setTimeout(() => setPhase("mind"), 950),
      window.setTimeout(() => setPhase("reasoning"), 1550),
    ];
    try {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) throw new Error("Please sign in to talk with Echo.");
      const history = turns.slice(-12).map((turn) => ({ role: turn.author === "you" ? "user" : "echo", text: turn.text }));
      const response = await fetch(`${API_BASE}/api/echo/conversation`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ question: asked, conversation_history: history, subject_id: subjectId || undefined }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail || "Echo could not respond right now.");
      const answer: Turn = { id: `echo-${Date.now()}`, author: "echo", text: payload.text, timestamp: new Date(), confidence: payload.confidence, citations: payload.citations, emotion: payload.emotion, explanation: payload.explainability, audioUrl: payload.audio_url };
      setPhase("speaking"); setTurns((current) => [...current, answer]); play(answer);
    } catch (error) {
      setTurns((current) => [...current, { id: `error-${Date.now()}`, author: "echo", text: error instanceof Error ? error.message : "Echo could not respond right now.", timestamp: new Date(), error: true }]);
    } finally { setSending(false); window.setTimeout(() => setPhase("idle"), 900); }
  };

  const submit = (event: FormEvent) => { event.preventDefault(); void sendQuestion(draft); };
  const startVoice = () => {
    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Recognition) { setPhase("idle"); return; }
    const instance = new Recognition(); instance.continuous = false; instance.interimResults = false;
    instance.onresult = (event) => void sendQuestion(event.results[0][0].transcript);
    instance.onerror = () => setPhase("idle"); instance.onend = () => setPhase((current) => current === "listening" ? "idle" : current);
    recognition.current = instance; setPhase("listening"); instance.start();
  };
  const stopVoice = () => recognition.current?.stop();

  return <main className="echo-experience min-h-[calc(100vh-5rem)] bg-[radial-gradient(circle_at_92%_6%,#f2e3d8_0,transparent_24%),radial-gradient(circle_at_10%_80%,#fff_0,transparent_26%),#f8f6f2] px-4 py-4 sm:px-7 lg:px-8">
    <section className="mx-auto max-w-[1440px]">
      <header className="mb-5 flex flex-col justify-between gap-3 border-b border-primary/10 pb-4 sm:flex-row sm:items-end"><div><p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Your preserved presence</p><h1 className="mt-1 font-serif text-4xl tracking-tight text-text sm:text-5xl">Talk with Echo</h1><p className="mt-2 max-w-xl text-sm leading-6 text-text/60">Continue a conversation built from your memories, values, and life stories.</p></div><div className="flex items-center gap-2 rounded-full border border-primary/10 bg-white/60 px-4 py-2 text-sm text-text/60"><span className={`h-2 w-2 rounded-full ${sending ? "animate-pulse bg-primary" : "bg-success"}`} />{phaseLabel[phase]}</div></header>
      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_280px]">
        <section className="overflow-hidden rounded-[32px] border border-primary/10 bg-white/65 shadow-[0_22px_70px_rgba(102,69,55,0.10)] backdrop-blur-sm">
          <div className="border-b border-primary/10 px-5 py-3 sm:px-6"><div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Conversation</p><h2 className="mt-1 font-serif text-2xl text-text">A voice held with care</h2></div><span className="rounded-full bg-primary/8 px-3 py-1.5 text-xs font-medium text-primary">{turns.filter((turn) => turn.author === "you").length} turns</span></div></div>
          <div className="grid min-h-[500px] grid-rows-[190px_minmax(0,1fr)_auto]">
            <div className="flex flex-col items-center justify-center bg-[radial-gradient(circle,#fffdfb_0%,#fbf4ef_60%,transparent_72%)] px-5 text-center"><motion.div animate={{ scale: phase === "speaking" ? [1, 1.08, 1] : phase === "listening" ? [1, 1.05, 1] : [1, 1.025, 1], boxShadow: phase === "speaking" ? "0 0 0 20px rgba(197,144,83,.09), 0 24px 65px rgba(180,112,63,.28)" : phase === "listening" ? "0 0 0 18px rgba(132,93,171,.10), 0 24px 65px rgba(132,93,171,.22)" : "0 0 0 12px rgba(167,116,100,.08), 0 22px 55px rgba(167,116,100,.20)" }} transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }} className={`flex h-24 w-24 items-center justify-center rounded-full border border-white/60 ${phase === "speaking" ? "bg-[radial-gradient(circle_at_30%_30%,#f7d99e,#bf7e44)]" : phase === "listening" ? "bg-[radial-gradient(circle_at_30%_30%,#e6d8ff,#8a65ae)]" : "bg-[radial-gradient(circle_at_30%_30%,#e7d7ce,#a77464)]"}`}><Sparkles className="text-white/90" size={30} /></motion.div><AnimatePresence mode="wait"><motion.p key={phase} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="mt-3 text-sm font-medium text-text/65">{phaseCopy[phase]}</motion.p></AnimatePresence></div>
            <div className="max-h-[255px] space-y-4 overflow-y-auto px-5 py-4 sm:px-6" aria-live="polite">
              {turns.map((turn) => (
                <motion.article key={turn.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className={`flex ${turn.author === "you" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[86%] rounded-[22px] px-5 py-4 ${turn.author === "you" ? "rounded-br-md bg-primary text-white shadow-[0_10px_26px_rgba(167,116,100,.22)]" : "rounded-bl-md border border-primary/10 bg-[#fffaf7] text-text shadow-sm"}`}>
                    <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.15em]">
                      <span className={turn.author === "you" ? "text-white/70" : "text-primary"}>{turn.author === "you" ? "You" : "Echo"}</span>
                      <span suppressHydrationWarning className={turn.author === "you" ? "text-white/50" : "text-text/40"}>· {displayTime(turn.timestamp)}</span>
                      {turn.confidence !== undefined && <span className={turn.author === "you" ? "text-white/60" : "text-text/45"}>· {turn.citations?.length ? `${Math.round(turn.confidence * 100)}% grounded` : "casual conversation"}</span>}
                    </div>
                    <p className={`mt-2 whitespace-pre-wrap text-[15px] leading-7 ${turn.error ? "text-red-600" : ""}`}>{turn.text}</p>
                    {turn.author === "echo" && (
                      <div className="mt-4 flex items-center gap-2">
                        <button onClick={() => play(turn)} className="inline-flex items-center gap-1.5 rounded-full bg-primary/9 px-3 py-1.5 text-xs font-semibold text-primary transition hover:bg-primary/15"><Volume2 size={14} />Play</button>
                        {turn.citations && turn.citations.length > 0 && (
                          <details className="group">
                            <summary className="flex cursor-pointer list-none items-center gap-1.5 rounded-full border border-primary/15 px-3 py-1.5 text-xs font-semibold text-primary"><Headphones size={13} />Sources <ChevronDown size={13} className="transition group-open:rotate-180" /></summary>
                            <div className="mt-3 space-y-2 rounded-2xl border border-primary/10 bg-white p-3 text-xs text-text/65">
                              {turn.citations.map((citation) => (
                                <div key={citation.memory_id} className="border-b border-primary/10 pb-2 last:border-0 last:pb-0">
                                  <p>“{citation.excerpt}”</p>
                                  <p className="mt-1 text-[10px] uppercase tracking-wide text-text/40">{new Date(citation.timestamp).toLocaleDateString()}</p>
                                </div>
                              ))}
                            </div>
                          </details>
                        )}
                      </div>
                    )}
                  </div>
                </motion.article>
              ))}
            </div>
            <form onSubmit={submit} className="border-t border-primary/10 bg-white/80 p-4 sm:p-5"><div className="flex items-end gap-3 rounded-[22px] border border-primary/15 bg-white p-2 pl-4 shadow-sm focus-within:ring-2 focus-within:ring-primary/15"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Write a thought, question, or memory…" rows={2} disabled={sending} className="min-h-[50px] flex-1 resize-none bg-transparent py-2 text-sm leading-6 outline-none placeholder:text-text/40" /><button type="button" onPointerDown={startVoice} onPointerUp={stopVoice} onPointerLeave={stopVoice} className="hidden h-11 w-11 items-center justify-center rounded-2xl bg-primary/8 text-primary transition hover:bg-primary/15 sm:inline-flex" aria-label="Hold to talk"><Mic size={19} /></button><button type="submit" disabled={sending || !draft.trim()} className="inline-flex h-11 items-center gap-2 rounded-2xl bg-primary px-4 text-sm font-semibold text-white shadow-sm transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"><Send size={16} />Send</button></div><div className="mt-3 flex items-center justify-between px-1 text-xs text-text/45"><span><Mic size={12} className="mr-1 inline" />Hold to Talk</span><button type="button" onClick={() => latestEcho && play(latestEcho)} disabled={!latestEcho} className="inline-flex items-center gap-1 text-primary disabled:opacity-35"><RotateCcw size={13} />Replay last response</button></div></form>
          </div>
        </section>
        <aside className="space-y-5"><section className="rounded-[28px] border border-primary/10 bg-[#fffaf7]/90 p-6 shadow-[0_14px_45px_rgba(96,60,43,.08)]"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Echo profile</p><h2 className="mt-2 font-serif text-3xl text-text">Built with care.</h2><dl className="mt-6 space-y-4"><div className="flex justify-between border-b border-primary/10 pb-3"><dt className="text-sm text-text/55">Memories</dt><dd className="font-serif text-2xl text-primary">{memoryCount}</dd></div><div className="flex justify-between border-b border-primary/10 pb-3"><dt className="text-sm text-text/55">Mind traits</dt><dd className="font-serif text-2xl text-primary">{traitCount}</dd></div><div className="flex justify-between border-b border-primary/10 pb-3"><dt className="text-sm text-text/55">Life lessons</dt><dd className="font-serif text-2xl text-primary">{lessonCount}</dd></div><div><dt className="text-sm text-text/55">Last updated</dt><dd className="mt-1 text-sm font-medium text-text/80">{mind ? "Mind Model available" : "Awaiting Mind Model"}</dd></div></dl></section><section className="rounded-[28px] border border-primary/10 bg-white/70 p-6"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Confidence meter</p><div className="mt-4 h-2 overflow-hidden rounded-full bg-primary/10"><motion.div animate={{ width: `${Math.round((latestEcho?.confidence ?? 0) * 100)}%` }} className="h-full rounded-full bg-primary" /></div><p className="mt-3 text-sm text-text/60">{Math.round((latestEcho?.confidence ?? 0) * 100)}% confidence · {latestEcho?.emotion ?? "neutral"} tone</p></section><details className="rounded-[28px] border border-primary/10 bg-white/70 p-5"><summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-text"><span>Why did Echo answer this?</span><ChevronDown size={17} /></summary><div className="mt-5 space-y-4 text-sm leading-6 text-text/65"><div><p className="font-medium text-text">Retrieved memories</p><p>{latestEcho?.explanation?.retrieved_memories.length ? `${latestEcho.explanation.retrieved_memories.length} grounded source${latestEcho.explanation.retrieved_memories.length === 1 ? "" : "s"}` : "No response sources yet."}</p></div><div><p className="font-medium text-text">Mind traits</p><p>{latestEcho?.explanation?.mind_traits.length ? latestEcho.explanation.mind_traits.join(", ") : "No traits were applied."}</p></div><div><p className="font-medium text-text">Reasoning summary</p><p>{latestEcho?.explanation?.reasoning_summary || "Echo waits for a question before forming a grounded response."}</p></div>{latestEcho?.explanation?.timeline && <div><p className="font-medium text-text">Timeline</p><p>{latestEcho.explanation.timeline}</p></div>}</div></details></aside>
      </div>
    </section>
  </main>;
}

declare global {
  interface Window { SpeechRecognition?: new () => SpeechRecognition; webkitSpeechRecognition?: new () => SpeechRecognition; }
  interface SpeechRecognition extends EventTarget { continuous: boolean; interimResults: boolean; start(): void; stop(): void; onresult: ((event: SpeechRecognitionEvent) => void) | null; onerror: (() => void) | null; onend: (() => void) | null; }
  interface SpeechRecognitionEvent extends Event { results: { [index: number]: { [index: number]: { transcript: string } } }; }
}
