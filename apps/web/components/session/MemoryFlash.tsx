"use client";

import { AnimatePresence, motion } from "framer-motion";
import { BookmarkPlus } from "lucide-react";

export type MemoryFlashItem = {
  id: string;
  summary: string;
  topics: string[];
};

export function MemoryFlash({ memories }: { memories: MemoryFlashItem[] }) {
  return <div className="pointer-events-none fixed right-5 top-24 z-40 flex w-[min(360px,calc(100vw-2.5rem))] flex-col gap-3" aria-live="polite">
    <AnimatePresence initial={false}>
      {memories.map((memory) => <motion.article key={memory.id} initial={{ opacity: 0, x: 32, y: -8 }} animate={{ opacity: 1, x: 0, y: 0 }} exit={{ opacity: 0, x: 32 }} transition={{ type: "spring", stiffness: 300, damping: 28 }} className="rounded-2xl border border-primary/20 bg-white/95 p-4 shadow-lg backdrop-blur">
        <div className="flex gap-3"><span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><BookmarkPlus size={17} /></span><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Memory spotted</p><p className="mt-1 text-sm leading-5 text-text/80">{memory.summary}</p>{memory.topics.length > 0 && <p className="mt-2 text-xs text-text/50">{memory.topics.join(" · ")}</p>}</div></div>
      </motion.article>)}
    </AnimatePresence>
  </div>;
}
