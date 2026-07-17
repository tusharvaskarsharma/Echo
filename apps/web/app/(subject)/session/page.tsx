"use client";

import { FormEvent, useState, useEffect } from "react";
import { AudioOrb } from "@/components/session/AudioOrb";
import { TranscriptStream } from "@/components/session/TranscriptStream";
import { SessionControls } from "@/components/session/SessionControls";
import { useRealtimeSession } from "@/hooks/useRealtimeSession";

export default function SessionPage() {
  const { 
    connect, disconnect, isConnected, isSpeaking, transcript, error, submitText
  } = useRealtimeSession();

  const [timer, setTimer] = useState(0);
  const [text, setText] = useState("");

  useEffect(() => {
    let interval: any;
    if (isConnected) {
      interval = setInterval(() => {
        setTimer((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isConnected]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const determineOrbState = () => {
    if (!isConnected) return "disconnected";
    if (isSpeaking) return "speaking";
    return "listening"; // default state when connected but not speaking
  };

  const sendText = (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim()) return;
    submitText(text);
    setText("");
  };

  return (
    <div className="min-h-[100dvh] flex flex-col justify-between p-6 pb-12 overflow-hidden bg-background">
      {/* Top Header */}
      <header className="flex justify-between items-center w-full max-w-4xl mx-auto z-10 relative">
        <h1 className="text-4xl font-serif text-primary tracking-tight">Echo.</h1>
        <div className="clay-card px-6 py-2 text-xl font-medium text-text/80 bg-white/30">
          {formatTime(timer)}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center gap-8 md:gap-12 w-full max-w-4xl mx-auto z-10 relative">
        
        {error && (
          <div className="bg-red-100 text-red-700 px-6 py-4 rounded-clay shadow-clay-sm w-full text-center text-lg">
            {error}. You can still type notes below while you check that the API is running, you are signed in, and GEMINI_API_KEY is valid.
          </div>
        )}

        <AudioOrb state={determineOrbState()} />
        
        <TranscriptStream transcript={transcript} />
        <form onSubmit={sendText} className="w-full max-w-2xl flex gap-3 px-2">
          <label htmlFor="session-text" className="sr-only">Write a memory or answer</label>
          <textarea
            id="session-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Prefer typing? Write a memory or answer here…"
            rows={2}
            className="flex-1 resize-none rounded-clay border border-primary/20 bg-white/70 px-5 py-3 text-lg outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button type="submit" disabled={!text.trim()} className="clay-button-primary self-end px-5 py-3 disabled:opacity-50">Send</button>
        </form>
      </main>

      {/* Footer Controls */}
      <footer className="w-full max-w-4xl mx-auto z-10 relative">
        <SessionControls 
          isConnected={isConnected} 
          onConnect={connect} 
          onDisconnect={disconnect} 
        />
      </footer>
    </div>
  );
}
