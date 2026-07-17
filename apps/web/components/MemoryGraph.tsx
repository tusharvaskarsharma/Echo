"use client";

import { DatabaseZap, LockKeyhole, Sparkles, UsersRound } from "lucide-react";
import { useMemo, useState } from "react";
import type { ConsentLevel, Memory } from "../lib/types";

const consentText: Record<ConsentLevel, string> = { private: "Private", family: "Family", legacy: "Legacy" };
const consentIcon: Record<ConsentLevel, typeof LockKeyhole> = { private: LockKeyhole, family: UsersRound, legacy: Sparkles };
const emotionColor: Record<string, { fill: string; glow: string }> = {
  joy: { fill: "#F2B66D", glow: "#FDE7C8" },
  pride: { fill: "#C97862", glow: "#F4D1C7" },
  regret: { fill: "#9A86C6", glow: "#E5DDF6" },
  grief: { fill: "#7182B0", glow: "#D7DDF0" },
  love: { fill: "#D97885", glow: "#F6D7DB" },
  wisdom: { fill: "#6EA98F", glow: "#D7EDE1" },
  reflection: { fill: "#A77464", glow: "#EAD6CC" },
};

type PositionedMemory = Memory & { x: number; y: number; color: { fill: string; glow: string } };

function excerpt(content: string, length = 120) {
  return content.length > length ? `${content.slice(0, length).trim()}…` : content;
}

export function MemoryGraph({ memories, onConsent }: { memories: Memory[]; onConsent: (id: string, consent: ConsentLevel) => Promise<void> }) {
  const [selectedId, setSelectedId] = useState<string | null>(memories[0]?.id ?? null);
  const [savingConsent, setSavingConsent] = useState(false);
  const nodes = useMemo<PositionedMemory[]>(() => memories.map((memory, index) => {
    const angle = (index * 2.399963229728653) - Math.PI / 2;
    const ring = 100 + (index % 3) * 64;
    return {
      ...memory,
      x: 500 + Math.cos(angle) * ring * 1.45,
      y: 276 + Math.sin(angle) * ring,
      color: emotionColor[memory.emotion_tags?.[0]?.toLowerCase()] ?? emotionColor.reflection,
    };
  }), [memories]);
  const selected = nodes.find((memory) => memory.id === selectedId) ?? nodes[0] ?? null;
  const links = useMemo(() => nodes.flatMap((node, index) => nodes.slice(index + 1).flatMap((other) => {
    const shared = node.topics.filter((topic) => other.topics.includes(topic));
    return shared.length ? [{ from: node, to: other, strength: shared.length }] : [];
  })), [nodes]);

  const changeConsent = async (consent: ConsentLevel) => {
    if (!selected || savingConsent) return;
    setSavingConsent(true);
    try { await onConsent(selected.id, consent); }
    finally { setSavingConsent(false); }
  };

  return (
    <section className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="overflow-hidden rounded-[30px] border border-primary/10 bg-gradient-to-br from-white via-[#fcf8f4] to-[#f1e7df] shadow-clay">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-primary/10 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Interactive constellation</p>
            <h2 className="mt-1 font-serif text-3xl text-text">The stories that shape you</h2>
          </div>
          <div className="rounded-full border border-primary/15 bg-white/70 px-4 py-2 text-sm text-text/70">
            {memories.length} {memories.length === 1 ? "memory" : "memories"} connected by shared themes
          </div>
        </div>
        <div className="relative min-h-[510px] p-4 sm:p-7">
          <div className="pointer-events-none absolute left-[8%] top-[15%] h-48 w-48 rounded-full bg-[#f5d8c9]/45 blur-3xl" />
          <div className="pointer-events-none absolute bottom-[8%] right-[10%] h-52 w-52 rounded-full bg-[#d7e9e0]/60 blur-3xl" />
          <svg viewBox="0 0 1000 560" className="relative h-[480px] w-full" role="img" aria-label="Interactive map of your memories">
            <defs>
              <filter id="memory-shadow" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="8" stdDeviation="8" floodColor="#8d6255" floodOpacity="0.18" /></filter>
              <radialGradient id="legacy-core"><stop stopColor="#fff8f2" /><stop offset="1" stopColor="#d9a88f" /></radialGradient>
            </defs>
            {links.map(({ from, to }) => <line key={`${from.id}-${to.id}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#ba927e" strokeOpacity="0.36" strokeWidth="2" strokeDasharray="5 7" />)}
            {nodes.map((node) => <line key={`core-${node.id}`} x1="500" y1="276" x2={node.x} y2={node.y} stroke={node.color.fill} strokeOpacity="0.2" strokeWidth="1.5" />)}
            <circle cx="500" cy="276" r="59" fill="url(#legacy-core)" filter="url(#memory-shadow)" />
            <circle cx="500" cy="276" r="43" fill="#fffaf7" fillOpacity="0.92" />
            <text x="500" y="270" textAnchor="middle" className="fill-text text-[15px] font-semibold">Your</text>
            <text x="500" y="291" textAnchor="middle" className="fill-text text-[15px] font-semibold">legacy</text>
            {nodes.map((node) => {
              const isSelected = selected?.id === node.id;
              const radius = 21 + Math.min(10, node.confidence_score * 12);
              return <g key={node.id} role="button" tabIndex={0} className="cursor-pointer outline-none" onClick={() => setSelectedId(node.id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setSelectedId(node.id); }} aria-label={`Open memory: ${excerpt(node.content, 70)}`}>
                <circle cx={node.x} cy={node.y} r={radius + 13} fill={node.color.glow} opacity={isSelected ? 0.95 : 0.58} />
                <circle cx={node.x} cy={node.y} r={radius} fill={node.color.fill} opacity={node.consent_level === "private" ? 0.7 : 1} stroke="#fff" strokeWidth={isSelected ? 5 : 3} filter="url(#memory-shadow)" />
                {isSelected && <circle cx={node.x} cy={node.y} r={radius + 7} fill="none" stroke={node.color.fill} strokeWidth="2" strokeDasharray="3 5" />}
                <text x={node.x} y={node.y + radius + 25} textAnchor="middle" className="fill-text text-[13px] font-medium">{node.topics?.[0] || "memory"}</text>
              </g>;
            })}
          </svg>
          {!nodes.length && <div className="absolute inset-0 flex items-center justify-center px-8 text-center"><div className="max-w-sm rounded-3xl border border-primary/10 bg-white/80 p-7 shadow-sm"><Sparkles className="mx-auto text-primary" size={28} /><h3 className="mt-3 font-serif text-2xl text-text">Your map is ready to grow</h3><p className="mt-2 text-sm leading-6 text-text/65">Save a conversation from Record and its themes will appear here as a new point in your constellation.</p></div></div>}
          <div className="absolute bottom-6 left-6 rounded-2xl border border-white/80 bg-white/75 px-4 py-3 text-sm text-text/65 shadow-sm backdrop-blur">
            <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-primary" />Click a memory to explore its details and privacy.
          </div>
        </div>
      </div>

      <aside className="rounded-[30px] border border-primary/10 bg-white/80 p-6 shadow-clay backdrop-blur">
        {selected && (() => {
          const Icon = consentIcon[selected.consent_level];
          return <>
            <div className="flex items-start justify-between gap-3">
              <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Selected memory</p><h2 className="mt-2 font-serif text-3xl text-text">{selected.topics?.[0] || "A shared story"}</h2></div>
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary"><Icon size={13} />{consentText[selected.consent_level]}</span>
            </div>
            <p className="mt-5 max-h-48 overflow-y-auto rounded-2xl border border-primary/10 bg-[#fcf7f3] p-4 leading-7 text-text/80">{selected.content}</p>
            <div className="mt-5"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-text/50">Themes</p><div className="mt-2 flex flex-wrap gap-2">{(selected.topics?.length ? selected.topics : ["voice session"]).map((topic) => <span key={topic} className="rounded-full bg-secondary/35 px-3 py-1 text-xs text-text/75">{topic}</span>)}</div></div>
            <div className="mt-6"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-text/50">Who can use this memory?</p><div className="mt-2 grid grid-cols-3 gap-2">{(Object.keys(consentText) as ConsentLevel[]).map((consent) => <button key={consent} type="button" disabled={savingConsent} onClick={() => changeConsent(consent)} className={`rounded-xl px-2 py-2 text-xs font-medium transition ${selected.consent_level === consent ? "bg-primary text-white shadow-sm" : "bg-[#f7f0eb] text-text/65 hover:bg-secondary/40"}`}>{consentText[consent]}</button>)}</div></div>
          </>;
        })()}
        <div className="mt-7 border-t border-primary/10 pt-5">
          <div className="flex gap-3"><DatabaseZap className="mt-0.5 text-primary" size={20} /><div><p className="font-medium text-text">Semantic search</p><p className="mt-1 text-sm leading-5 text-text/60">Pinecone finds related memories during persona conversations. This visual map groups the same records by their shared themes.</p></div></div>
        </div>
      </aside>

      <div className="xl:col-span-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {nodes.map((memory) => <button key={`card-${memory.id}`} type="button" onClick={() => setSelectedId(memory.id)} className={`rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-md ${selected?.id === memory.id ? "border-primary/50 bg-primary/5" : "border-primary/10 bg-white/70"}`}>
          <div className="flex items-center justify-between gap-3"><span className="rounded-full px-2.5 py-1 text-xs font-medium" style={{ background: memory.color.glow, color: memory.color.fill }}>{memory.emotion_tags?.[0] || "reflection"}</span><span className="text-xs text-text/45">{consentText[memory.consent_level]}</span></div>
          <p className="mt-3 line-clamp-3 text-sm leading-6 text-text/75">{excerpt(memory.content)}</p>
        </button>)}
      </div>
    </section>
  );
}
