"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Check, Circle, MessageCircle, Save, Send, Sparkles } from "lucide-react";
import { AudioOrb } from "@/components/session/AudioOrb";
import { MemoryFlash } from "@/components/session/MemoryFlash";
import { SessionControls } from "@/components/session/SessionControls";
import { useRealtimeSession } from "@/hooks/useRealtimeSession";
import { api } from "@/lib/api";

export default function SessionPage() {
  const { connect, disconnect, finishRecording, isConnected, activeSpeaker, audioLevel, sessionId, transcript, messages, memoryFlashes, error, submitText } = useRealtimeSession();
  const [timer, setTimer] = useState(0);
  const [text, setText] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isConnected) return;
    const interval = window.setInterval(() => setTimer((previous) => previous + 1), 1000);
    return () => window.clearInterval(interval);
  }, [isConnected]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const formattedTime = useMemo(() => {
    const minutes = Math.floor(timer / 60).toString().padStart(2, "0");
    const seconds = (timer % 60).toString().padStart(2, "0");
    return `${minutes}:${seconds}`;
  }, [timer]);
  const conversationContent = useMemo(
    () => messages.map((message) => `${message.speaker === "echo" ? "Echo" : "You"}: ${message.text}`).join("\n"),
    [messages],
  );
  const canSave = Boolean(conversationContent.trim() || transcript.trim());

  const sendText = (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim()) return;
    submitText(text);
    setText("");
  };

  const startSession = async () => {
    setSaveError(null);
    setSaved(false);
    await connect();
  };

  const saveConversation = async () => {
    const content = conversationContent.trim() || transcript.trim();
    if (!content || isSaving || saved) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      const recording = await finishRecording();
      if (sessionId) {
        // The recording contains only the microphone.  Save this browser-side
        // Echo/User transcript first so every question stays paired with its
        // answer in the indexed evidence.
        await api.saveSessionTranscript(sessionId, content);
        if (recording?.size) await api.uploadSessionAudio(sessionId, recording);
        await api.finishSession(sessionId);
      } else {
        // Text-only and local no-Postgres sessions still persist as a private
        // transcript memory through the Supabase Storage fallback.
        await api.saveConversation(content);
      }
      setSaved(true);
      disconnect();
    } catch (saveFailure) {
      console.error("Unable to save conversation as a memory", saveFailure);
      setSaveError(saveFailure instanceof Error ? saveFailure.message : "We could not save this conversation. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <main className="h-[100dvh] overflow-hidden bg-[radial-gradient(circle_at_80%_0%,#f1e4da_0,transparent_32%),#f8f6f2] p-3 sm:p-5">
      <MemoryFlash memories={memoryFlashes} />
      <div className="mx-auto flex h-full max-w-7xl flex-col overflow-hidden rounded-[30px] border border-white/80 bg-white/45 shadow-[0_24px_70px_rgba(92,61,48,0.12)] backdrop-blur">
        <header className="flex items-center justify-between border-b border-primary/10 px-5 py-4 sm:px-7">
          <div className="flex items-center gap-3 sm:gap-5">
            <Link href="/subject/dashboard" className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-text/70 transition hover:bg-primary/10 hover:text-primary" aria-label="Back to main dashboard">
              <ArrowLeft size={17} /> <span className="hidden sm:inline">Dashboard</span>
            </Link>
            <div className="h-7 w-px bg-primary/15" />
            <div><p className="font-serif text-3xl leading-none text-primary">Echo.</p><p className="mt-1 text-xs text-text/50">Private conversation</p></div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-primary/10 bg-white/70 px-4 py-2 text-sm font-medium text-text/70 shadow-sm"><Circle size={8} className={isConnected ? "fill-success text-success" : "fill-text/30 text-text/30"} /> {formattedTime}</div>
        </header>

        <div className="min-h-0 flex-1 p-3 sm:p-5">
          <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(290px,1fr)]">
            <section className="flex min-h-0 flex-col overflow-hidden rounded-[24px] border border-primary/10 bg-white/70 shadow-sm">
              <div className="flex items-start justify-between gap-4 border-b border-primary/10 px-5 py-4">
                <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Conversation</p><h1 className="mt-1 font-serif text-3xl text-text">Your story, in your words</h1></div>
                <span className="hidden items-center gap-2 rounded-full bg-secondary/25 px-3 py-1.5 text-xs text-text/65 sm:inline-flex"><MessageCircle size={14} /> {messages.length} turns</span>
              </div>

              {(error || saveError) && <div className="mx-5 mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-5 text-red-700" role="alert">{error || saveError}</div>}

              <div ref={logRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5" aria-live="polite">
                {!messages.length && <div className="mx-auto mt-10 max-w-md rounded-3xl border border-primary/10 bg-[#fcf7f3] p-6 text-center"><Sparkles className="mx-auto text-primary" size={24} /><p className="mt-3 font-serif text-2xl text-text">I&apos;m here to listen.</p><p className="mt-2 text-sm leading-6 text-text/65">Start a voice session or type a thought. Echo will respond and the dialogue will stay clearly organised here.</p></div>}
                {messages.map((message) => {
                  const isEcho = message.speaker === "echo";
                  return <article key={message.id} className={`flex gap-3 ${isEcho ? "justify-start" : "justify-end"}`}>
                    {isEcho && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-serif text-white">E</div>}
                    <div className={`max-w-[82%] rounded-2xl px-4 py-3 shadow-sm ${isEcho ? "rounded-tl-sm border border-primary/10 bg-[#fcf5f0] text-text" : "rounded-tr-sm bg-primary text-white"}`}>
                      <p className={`text-xs font-semibold uppercase tracking-[0.12em] ${isEcho ? "text-primary" : "text-white/70"}`}>{isEcho ? "Echo" : "You"}</p>
                      <p className="mt-1 whitespace-pre-wrap text-sm leading-6 sm:text-[15px]">{message.text}</p>
                    </div>
                    {!isEcho && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-semibold text-text">Y</div>}
                  </article>;
                })}
              </div>

              <form onSubmit={sendText} className="border-t border-primary/10 bg-white/65 p-4">
                <label htmlFor="session-text" className="sr-only">Write a response</label>
                <div className="flex items-end gap-3 rounded-2xl border border-primary/15 bg-white px-3 py-2 shadow-sm focus-within:ring-2 focus-within:ring-primary/20">
                  <textarea id="session-text" value={text} onChange={(event) => setText(event.target.value)} placeholder="Write your response..." rows={1} className="max-h-24 min-h-[42px] flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-text/40" />
                  <button type="submit" disabled={!text.trim()} className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40" aria-label="Send message"><Send size={17} /></button>
                </div>
              </form>
            </section>

            <aside className="flex min-h-0 flex-col overflow-y-auto rounded-[24px] border border-primary/10 bg-[#fcf8f5]/90 p-5 shadow-sm">
              <div className="text-center"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Voice studio</p><h2 className="mt-1 font-serif text-3xl text-text">{!isConnected ? "Ready when you are" : activeSpeaker === "echo" ? "Echo is speaking" : activeSpeaker === "subject" ? "Listening to you" : "Session active"}</h2></div>
              <div className="flex flex-1 items-center justify-center py-3"><AudioOrb state={!isConnected ? "disconnected" : activeSpeaker === "echo" ? "speaking" : "listening"} amplitude={audioLevel} compact /></div>
              <div className="rounded-2xl border border-primary/10 bg-white/70 p-4 text-center"><p className="text-sm font-medium text-text">{isConnected ? "Your microphone is on" : "Start when you feel ready"}</p><p className="mt-1 text-xs leading-5 text-text/55">You can speak naturally or type in the conversation panel.</p></div>
              <div className="mt-4"><SessionControls isConnected={isConnected} onConnect={startSession} onDisconnect={disconnect} /></div>
              <div className="mt-5 border-t border-primary/10 pt-5">
                {saved ? <Link href="/subject/memories" className="flex items-center justify-center gap-2 rounded-2xl bg-success px-4 py-3 text-sm font-semibold text-white"><Check size={17} /> View saved memory</Link> : <button type="button" onClick={saveConversation} disabled={!canSave || isSaving} className="flex w-full items-center justify-center gap-2 rounded-2xl border border-primary/15 bg-white px-4 py-3 text-sm font-semibold text-primary transition hover:bg-primary/5 disabled:cursor-not-allowed disabled:opacity-40"><Save size={17} /> {isSaving ? "Saving..." : "Save conversation"}</button>}
                <p className="mt-2 text-center text-xs leading-5 text-text/50">Saved conversations are private and appear in your memory map.</p>
              </div>
            </aside>
          </div>
        </div>
      </div>
    </main>
  );
}
