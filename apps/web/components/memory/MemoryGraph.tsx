"use client";

import { useEffect, useMemo, useRef } from "react";
import * as d3 from "d3";
import type { Memory } from "@/hooks/useMemoryGraph";

type Node = Memory & d3.SimulationNodeDatum & { radius: number; topic: string; era: string };
type Link = d3.SimulationLinkDatum<Node> & { source: string | Node; target: string | Node; strength: number };

const eraColours: Record<string, string> = { "Before 1980": "#755c9f", "1980s–1990s": "#4c8695", "2000s": "#bd775b", "2010s": "#bc9b4b", "2020s+": "#728c69", Undated: "#9a8177" };
const topicOf = (memory: Memory) => memory.topics.find(Boolean)?.trim() || "Uncategorised";
const eraOf = (time: string) => { const year = Number(time?.match(/(?:19|20)\d{2}/)?.[0]); return !year ? "Undated" : year < 1980 ? "Before 1980" : year < 2000 ? "1980s–1990s" : year < 2010 ? "2000s" : year < 2020 ? "2010s" : "2020s+"; };

export default function MemoryGraph({ memories, onNodeClick, selectedId }: { memories: Memory[]; onNodeClick: (memory: Memory) => void; selectedId: string | null }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const clickRef = useRef(onNodeClick);
  clickRef.current = onNodeClick;
  const legend = useMemo(() => Object.entries(eraColours), []);

  useEffect(() => {
    const svgEl = svgRef.current;
    const host = svgEl?.parentElement;
    if (!svgEl || !host) return;
    let simulation: d3.Simulation<Node, undefined> | undefined;
    const draw = () => {
      simulation?.stop();
      const { width, height } = host.getBoundingClientRect();
      if (!width || !height) return;
      const svg = d3.select(svgEl).attr("viewBox", `0 0 ${width} ${height}`);
      svg.selectAll("*").remove();
      if (!memories.length) {
        svg.append("text").attr("x", width / 2).attr("y", height / 2).attr("text-anchor", "middle").attr("fill", "#806f68").attr("font-size", 17).text("Your memory map is ready to grow.");
        return;
      }
      const nodes: Node[] = memories.map((memory) => ({ ...memory, topic: topicOf(memory), era: eraOf(memory.time_period), radius: 13 + Math.round(Math.max(0.15, Math.min(1, memory.confidence_score || 0)) * 22) }));
      const topics = [...new Set(nodes.map((item) => item.topic))];
      const point = (topic: string) => { const angle = ((topics.indexOf(topic) / topics.length) * Math.PI * 2) - Math.PI / 2; const radius = Math.min(width, height) * 0.27; return { x: width / 2 + Math.cos(angle) * radius, y: height / 2 + Math.sin(angle) * radius }; };
      const links: Link[] = [];
      nodes.forEach((left, i) => nodes.slice(i + 1).forEach((right) => { const strength = left.topics.filter((topic) => right.topics.includes(topic)).length; if (strength) links.push({ source: left.id, target: right.id, strength }); }));
      const lines = svg.append("g").selectAll("line").data(links).join("line").attr("stroke", "#a98f82").attr("stroke-opacity", 0.25).attr("stroke-width", (item) => Math.min(3, item.strength));
      const labels = svg.append("g");
      topics.forEach((topic) => { const { x, y } = point(topic); labels.append("text").attr("x", x).attr("y", y - 50).attr("text-anchor", "middle").attr("fill", "#806f68").attr("font-size", 12).attr("font-weight", 600).text(topic.length > 20 ? `${topic.slice(0, 19)}…` : topic); });
      const circles = svg.append("g").selectAll<SVGCircleElement, Node>("circle").data(nodes, (item) => item.id).join("circle")
        .attr("r", (item) => item.radius).attr("fill", (item) => eraColours[item.era]).attr("fill-opacity", (item) => item.id === selectedId ? 1 : 0.8)
        .attr("stroke", (item) => item.id === selectedId ? "#3f312c" : "#fffaf6").attr("stroke-width", (item) => item.id === selectedId ? 4 : 2)
        .attr("role", "button").attr("tabindex", 0).attr("aria-label", (item) => `Open memory about ${item.topic}, ${item.era}, confidence ${Math.round(item.confidence_score * 100)} percent`).style("cursor", "pointer")
        .on("click", (_event, item) => clickRef.current(item)).on("keydown", (event, item) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); clickRef.current(item); } });
      circles.append("title").text((item) => `${item.topic} · ${item.era}\n${item.content.slice(0, 100)}`);
      simulation = d3.forceSimulation(nodes).force("link", d3.forceLink<Node, Link>(links).id((item) => item.id).distance(92).strength((item) => Math.min(0.8, 0.25 + item.strength * 0.2))).force("charge", d3.forceManyBody().strength(-300)).force("collision", d3.forceCollide<Node>().radius((item) => item.radius + 10)).force("x", d3.forceX<Node>((item) => point(item.topic).x).strength(0.16)).force("y", d3.forceY<Node>((item) => point(item.topic).y).strength(0.16));
      circles.call(d3.drag<SVGCircleElement, Node>().on("start", (event, item) => { if (!event.active) simulation?.alphaTarget(0.22).restart(); item.fx = item.x; item.fy = item.y; }).on("drag", (event, item) => { item.fx = event.x; item.fy = event.y; }).on("end", (event, item) => { if (!event.active) simulation?.alphaTarget(0); item.fx = null; item.fy = null; }));
      simulation.on("tick", () => { lines.attr("x1", (item) => (item.source as Node).x ?? 0).attr("y1", (item) => (item.source as Node).y ?? 0).attr("x2", (item) => (item.target as Node).x ?? 0).attr("y2", (item) => (item.target as Node).y ?? 0); circles.attr("cx", (item) => Math.max(item.radius, Math.min(width - item.radius, item.x ?? width / 2))).attr("cy", (item) => Math.max(item.radius, Math.min(height - item.radius, item.y ?? height / 2))); });
    };
    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(host);
    return () => { observer.disconnect(); simulation?.stop(); };
  }, [memories, selectedId]);

  return <section className="relative min-h-[560px] overflow-hidden rounded-[28px] border border-primary/10 bg-[radial-gradient(circle_at_50%_46%,#fffaf5_0,transparent_34%),linear-gradient(135deg,#fffdfb,#f5e9e1)] shadow-sm"><div className="absolute left-5 top-5 z-10 max-w-sm rounded-2xl bg-white/80 px-4 py-3 shadow-sm backdrop-blur"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Memory map</p><p className="mt-1 text-sm leading-5 text-text/65">Clusters are shared topics. Larger nodes have stronger confidence.</p></div><svg ref={svgRef} className="h-[560px] w-full" role="img" aria-label="Interactive memory graph grouped by topic, with node size showing confidence and colour showing era" /><div className="absolute bottom-5 left-5 z-10 flex max-w-[calc(100%-2.5rem)] flex-wrap gap-x-3 gap-y-2 rounded-2xl bg-white/80 px-4 py-3 text-xs text-text/65 shadow-sm backdrop-blur">{legend.map(([era, colour]) => <span key={era} className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colour }} />{era}</span>)}</div></section>;
}
