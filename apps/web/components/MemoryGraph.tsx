"use client";

import { forceCenter, forceCollide, forceSimulation, forceX, forceY } from "d3-force";
import { useEffect, useMemo, useState } from "react";
import type { ConsentLevel, Memory } from "../lib/types";

type Node = Memory & { cx: number; cy: number };

const consentText: Record<ConsentLevel, string> = { private: "Private", family: "Family", legacy: "Legacy" };
const emotionColor: Record<string, string> = { joy: "#f5bd5b", pride: "#db836e", regret: "#a98bc4", grief: "#7481b8", love: "#ef9b8c", wisdom: "#85bda7" };

export function MemoryGraph({ memories, onConsent }: { memories: Memory[]; onConsent: (id: string, consent: ConsentLevel) => Promise<void> }) {
  const [selected, setSelected] = useState<Memory | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);

  useEffect(() => {
    const simulated = memories.map((memory) => ({ ...memory, cx: memory.x * 5.4, cy: memory.y * 3.45 }));
    const simulation = forceSimulation(simulated)
      .force("x", forceX<Node>(270).strength(0.035))
      .force("y", forceY<Node>(172).strength(0.035))
      .force("collide", forceCollide<Node>((node) => 13 + node.confidence_score * 10))
      .force("center", forceCenter<Node>(270, 172))
      .stop();
    for (let index = 0; index < 90; index += 1) simulation.tick();
    setNodes(simulated);
  }, [memories]);

  const links = useMemo(() => nodes.flatMap((node, index) => index % 3 === 0 && nodes[index + 1] ? [{ from: node, to: nodes[index + 1] }] : []), [nodes]);
  const update = async (consent: ConsentLevel) => {
    if (!selected) return;
    await onConsent(selected.id, consent);
    setSelected({ ...selected, consent_level: consent });
  };

  return (
    <section className="graph-layout">
      <div className="graph-canvas" aria-label="Eleanor's memory constellation">
        <div className="graph-halo halo-one" /><div className="graph-halo halo-two" />
        <svg viewBox="0 0 540 345" role="img">
          {links.map(({ from, to }) => <line key={`${from.id}-${to.id}`} className="graph-link" x1={from.cx} y1={from.cy} x2={to.cx} y2={to.cy} />)}
          {nodes.map((node) => (
            <g key={node.id} className="memory-node" onClick={() => setSelected(node)} tabIndex={0} role="button" aria-label={`Open memory: ${node.content}`}>
              <circle cx={node.cx} cy={node.cy} r={8 + node.confidence_score * 8} fill={emotionColor[node.emotion_tags[0]] ?? "#a98bc4"} opacity={node.consent_level === "private" ? 0.35 : 0.92} />
              <circle cx={node.cx} cy={node.cy} r={14 + node.confidence_score * 8} className="node-glow" />
            </g>
          ))}
        </svg>
      </div>
      <aside className="memory-panel" aria-live="polite">
        {selected ? <>
          <p className="eyebrow">{selected.time_period} · {selected.topics[0]}</p>
          <h2>{selected.emotion_tags[0]} memory</h2>
          <p>{selected.content}</p>
          <p className="source-meta">{selected.session_id} · {Math.floor(selected.timestamp_seconds / 60)}:{String(selected.timestamp_seconds % 60).padStart(2, "0")}</p>
          <label className="consent-label">Who can use this memory?</label>
          <div className="consent-control">
            {(Object.keys(consentText) as ConsentLevel[]).map((consent) => <button key={consent} className={selected.consent_level === consent ? "active" : ""} onClick={() => update(consent)}>{consentText[consent]}</button>)}
          </div>
          <p className="small-note">Private memories are immediately removed from family retrieval.</p>
        </> : <>
          <p className="eyebrow">Memory constellation</p><h2>Choose a star</h2><p>Each star is a story Eleanor shared. Size reflects confidence; colour reflects emotion.</p>
        </>}
      </aside>
    </section>
  );
}

