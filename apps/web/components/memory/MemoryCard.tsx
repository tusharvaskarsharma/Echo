"use client";

import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import type { Memory } from "@/hooks/useMemoryGraph";
import ConsentSlider from "./ConsentSlider";

export function MemoryCard({ memory, onClose, onConsentChange }: { memory: Memory | null; onClose: () => void; onConsentChange: (id: string, level: Memory["consent_level"]) => Promise<void> }) {
  return <AnimatePresence>{memory && <motion.aside initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 24 }} className="absolute bottom-5 right-5 top-5 z-20 flex w-[min(420px,calc(100%-2.5rem))] flex-col overflow-y-auto rounded-[26px] border border-primary/15 bg-white/95 p-6 shadow-2xl backdrop-blur" aria-label="Selected memory">
    <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Selected memory</p><h2 className="mt-2 font-serif text-3xl text-text">{memory.topics[0] || "A shared story"}</h2></div><button type="button" onClick={onClose} className="rounded-xl p-2 text-text/60 hover:bg-primary/10 hover:text-primary" aria-label="Close memory"><X size={20} /></button></div>
    <p className="mt-5 whitespace-pre-wrap rounded-2xl bg-[#fcf6f1] p-4 text-sm leading-7 text-text/80">{memory.content}</p>
    <dl className="mt-5 grid grid-cols-2 gap-3 text-sm"><div><dt className="text-text/50">Era</dt><dd className="mt-1 font-medium text-text">{memory.time_period || "Undated"}</dd></div><div><dt className="text-text/50">Confidence</dt><dd className="mt-1 font-medium text-text">{Math.round(memory.confidence_score * 100)}%</dd></div></dl>
    <div className="mt-5"><p className="text-sm font-medium text-text">Consent</p><p className="mt-1 text-xs leading-5 text-text/55">Choose who may use this memory.</p><div className="mt-3"><ConsentSlider consent={memory.consent_level} onChange={(level) => void onConsentChange(memory.id, level)} /></div></div>
    {!!memory.topics.length && <div className="mt-5"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-text/50">Topics</p><div className="mt-2 flex flex-wrap gap-2">{memory.topics.map((topic) => <span key={topic} className="rounded-full bg-primary/10 px-3 py-1 text-xs text-primary">{topic}</span>)}</div></div>}
  </motion.aside>}</AnimatePresence>;
}
