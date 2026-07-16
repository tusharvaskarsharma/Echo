"use client";

import { useState, useEffect } from "react";
import { AudioOrb } from "@/components/session/AudioOrb";
import { TranscriptStream } from "@/components/session/TranscriptStream";
import { SessionControls } from "@/components/session/SessionControls";
import { useRealtimeSession } from "@/hooks/useRealtimeSession";

export default function SessionPage() {
  const { 
    connect, disconnect, isConnected, isSpeaking, transcript, error 
  } = useRealtimeSession();

  const [timer, setTimer] = useState(0);

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
            {error}
          </div>
        )}

        <AudioOrb state={determineOrbState()} />
        
        <TranscriptStream transcript={transcript} />
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