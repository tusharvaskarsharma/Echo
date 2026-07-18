"use client";

import Link from "next/link";
import { ArrowLeft, BrainCircuit, CircleDot, Sparkles } from "lucide-react";
import { useState } from "react";

import { AppNav } from "@/components/AppNav";
import MemoryGraph from "@/components/memory/MemoryGraph";
import { MemoryCard } from "@/components/memory/MemoryCard";
import { Memory, useMemoryGraph } from "@/hooks/useMemoryGraph";

export default function MemoriesPage() {
  const { memories, isLoading, isError, patchConsent } = useMemoryGraph();
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);

  if (isLoading) return <div className="flex min-h-screen items-center justify-center bg-background"><div className="animate-pulse font-serif text-2xl text-primary">Loading your memory map…</div></div>;

  const allMemories = memories || [];
  const activeMemory = selectedMemory ? allMemories.find((memory) => memory.id === selectedMemory.id) || null : null;
  const topicCount = new Set(allMemories.flatMap((memory) => memory.topics)).size;

  return <main className="min-h-screen bg-background">
    <AppNav />
    <div className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-7 sm:py-9 lg:px-10">
      <header className="flex flex-col gap-5 border-b border-primary/10 pb-7 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <Link href="/subject/dashboard" className="inline-flex items-center gap-2 text-sm font-medium text-text/60 transition hover:text-primary"><ArrowLeft size={16} />Back to dashboard</Link>
          <p className="mt-5 text-xs font-semibold uppercase tracking-[0.2em] text-primary">Your living archive</p>
          <h1 className="mt-2 font-serif text-4xl text-text sm:text-5xl">Memory constellation</h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-text/65">Explore the stories you have preserved. Connected memories share a theme; node size reflects confidence and colour reflects its era.</p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:min-w-[310px]">
          <div className="rounded-2xl border border-primary/10 bg-white/70 px-4 py-3 shadow-sm"><div className="flex items-center gap-2 text-primary"><BrainCircuit size={18} /><span className="text-xs font-semibold uppercase tracking-[0.14em]">Memories</span></div><p className="mt-2 font-serif text-3xl text-text">{allMemories.length}</p></div>
          <div className="rounded-2xl border border-primary/10 bg-white/70 px-4 py-3 shadow-sm"><div className="flex items-center gap-2 text-primary"><CircleDot size={18} /><span className="text-xs font-semibold uppercase tracking-[0.14em]">Themes</span></div><p className="mt-2 font-serif text-3xl text-text">{topicCount}</p></div>
        </div>
      </header>

      {isError && <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">Your memories could not be loaded. Please refresh and try again.</div>}
      <section className="relative mt-7"><MemoryGraph memories={allMemories} onNodeClick={setSelectedMemory} selectedId={activeMemory?.id || null} /><MemoryCard memory={activeMemory} onClose={() => setSelectedMemory(null)} onConsentChange={patchConsent} /></section>
      <footer className="mt-5 flex items-center gap-2 rounded-2xl border border-primary/10 bg-white/65 px-5 py-4 text-sm text-text/65"><Sparkles size={17} className="shrink-0 text-primary" /><span>Select any node to read the preserved memory and control its consent. Drag nodes to arrange your own view.</span></footer>
    </div>
  </main>;
}
