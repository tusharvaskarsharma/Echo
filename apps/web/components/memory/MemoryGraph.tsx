"use client";

import { useEffect, useMemo, useRef } from "react";
import * as d3 from "d3";

import type { Memory } from "@/hooks/useMemoryGraph";

type Node = Memory & d3.SimulationNodeDatum & { radius: number; topic: string; era: string; label: string };
type Link = d3.SimulationLinkDatum<Node> & { source: string | Node; target: string | Node; weight: number };

const eraColours: Record<string, string> = {
  "Before 1980": "#755c9f", "1980s–1990s": "#4c8695", "2000s": "#bd775b",
  "2010s": "#bc9b4b", "2020s+": "#728c69", Undated: "#9a8177",
};

const topicOf = (memory: Memory) => memory.topics.find(Boolean)?.trim() || "Uncategorised";
const words = (value: string) => value.toLowerCase().replace(/[^a-z0-9\s]/g, " ").split(/\s+/).filter((word) => word.length > 2 && word !== "echo");
const setOf = (items: string[]) => new Set(items.map((item) => item.toLowerCase().trim()).filter(Boolean));
const overlap = (left: Set<string>, right: Set<string>) => {
  const union = new Set([...left, ...right]);
  if (!union.size) return 0;
  return [...left].filter((item) => right.has(item)).length / union.size;
};
const labelOf = (memory: Memory) => {
  const source = memory.semantic_metadata?.title || memory.topics.find(Boolean) || memory.content;
  const label = words(source).slice(0, 2);
  return label.length === 2 ? label.map((word) => word[0].toUpperCase() + word.slice(1)).join(" ") : label[0] ? `${label[0][0].toUpperCase()}${label[0].slice(1)} Story` : "Shared Story";
};
const connectionWeight = (left: Memory, right: Memory) => {
  const topicScore = overlap(setOf(left.topics), setOf(right.topics));
  const peopleScore = overlap(setOf(left.people_mentioned), setOf(right.people_mentioned));
  const emotionScore = overlap(setOf(left.emotion_tags), setOf(right.emotion_tags));
  const keywordScore = overlap(new Set(words(left.semantic_metadata?.keywords?.join(" ") || left.content)), new Set(words(right.semantic_metadata?.keywords?.join(" ") || right.content)));
  return 0.65 * topicScore + 0.2 * peopleScore + 0.1 * emotionScore + 0.05 * keywordScore;
};
const eraOf = (time: string) => {
  const year = Number(time?.match(/(?:19|20)\d{2}/)?.[0]);
  if (!year) return "Undated";
  if (year < 1980) return "Before 1980";
  if (year < 2000) return "1980s–1990s";
  if (year < 2010) return "2000s";
  return year < 2020 ? "2010s" : "2020s+";
};

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
        svg.append("text").attr("x", width / 2).attr("y", height / 2 - 8).attr("text-anchor", "middle").attr("fill", "#806f68").attr("font-size", 20).text("Your memory map is ready to grow");
        svg.append("text").attr("x", width / 2).attr("y", height / 2 + 24).attr("text-anchor", "middle").attr("fill", "#806f68").attr("font-size", 14).text("Save a conversation and its themes will appear here.");
        return;
      }

      const nodes: Node[] = memories.map((memory) => ({
        ...memory,
        topic: topicOf(memory),
        era: eraOf(memory.time_period),
        label: labelOf(memory),
        radius: 15 + Math.round(Math.max(0.15, Math.min(1, memory.confidence_score || 0)) * 22),
      }));
      const topics = [...new Set(nodes.map((item) => item.topic))];
      const point = (topic: string) => {
        if (topics.length === 1) return { x: width / 2, y: height / 2 };
        const angle = ((topics.indexOf(topic) / topics.length) * Math.PI * 2) - Math.PI / 2;
        const radius = Math.min(width, height) * 0.25;
        return { x: width / 2 + Math.cos(angle) * radius, y: height / 2 + Math.sin(angle) * radius };
      };
      const links: Link[] = [];
      nodes.forEach((left, index) => nodes.slice(index + 1).forEach((right) => {
        const weight = connectionWeight(left, right);
        // A relationship needs meaningful shared evidence; weak word overlap
        // alone does not create a visual link.
        if (weight >= 0.2) links.push({ source: left.id, target: right.id, weight });
      }));

      const lines = svg.append("g").selectAll("line").data(links).join("line")
        .attr("stroke", "#a98f82")
        .attr("stroke-opacity", (item) => 0.12 + item.weight * 0.48)
        .attr("stroke-width", (item) => 1 + item.weight * 3);
      const labels = svg.append("g");
      if (topics.length > 1) topics.forEach((topic) => {
        const { x, y } = point(topic);
        labels.append("text").attr("x", x).attr("y", y - 64).attr("text-anchor", "middle")
          .attr("fill", "#806f68").attr("font-size", 12).attr("font-weight", 600)
          .text(topic.length > 20 ? `${topic.slice(0, 19)}…` : topic);
      });
      const circles = svg.append("g").selectAll<SVGCircleElement, Node>("circle")
        .data(nodes, (item) => item.id).join("circle")
        .attr("r", (item) => item.radius)
        .attr("fill", (item) => eraColours[item.era])
        .attr("fill-opacity", (item) => item.id === selectedId ? 1 : 0.82)
        .attr("stroke", (item) => item.id === selectedId ? "#3f312c" : "#fffaf6")
        .attr("stroke-width", (item) => item.id === selectedId ? 4 : 2)
        .attr("role", "button").attr("tabindex", 0)
        .attr("aria-label", (item) => `Open ${item.label}, ${item.era}, confidence ${Math.round(item.confidence_score * 100)} percent`)
        .style("cursor", "pointer")
        .on("click", (_event, item) => clickRef.current(item))
        .on("keydown", (event, item) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); clickRef.current(item); } });
      circles.append("title").text((item) => `${item.label} · ${item.era}\n${item.content.slice(0, 100)}`);
      const nodeLabels = svg.append("g").selectAll<SVGTextElement, Node>("text").data(nodes, (item) => item.id).join("text")
        .attr("text-anchor", "middle").attr("fill", "#5e4a43").attr("font-size", 12).attr("font-weight", 600)
        .attr("pointer-events", "none").text((item) => item.label);

      simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink<Node, Link>(links).id((item) => item.id).distance((item) => 250 - item.weight * 175).strength((item) => 0.15 + item.weight * 0.75))
        .force("charge", d3.forceManyBody().strength(-320))
        .force("collision", d3.forceCollide<Node>().radius((item) => item.radius + 12))
        .force("x", d3.forceX<Node>((item) => point(item.topic).x).strength(0.2))
        .force("y", d3.forceY<Node>((item) => point(item.topic).y).strength(0.2));
      circles.call(d3.drag<SVGCircleElement, Node>()
        .on("start", (event, item) => { if (!event.active) simulation?.alphaTarget(0.22).restart(); item.fx = item.x; item.fy = item.y; })
        .on("drag", (event, item) => { item.fx = event.x; item.fy = event.y; })
        .on("end", (event, item) => { if (!event.active) simulation?.alphaTarget(0); item.fx = null; item.fy = null; }));
      simulation.on("tick", () => {
        lines.attr("x1", (item) => (item.source as Node).x ?? 0).attr("y1", (item) => (item.source as Node).y ?? 0)
          .attr("x2", (item) => (item.target as Node).x ?? 0).attr("y2", (item) => (item.target as Node).y ?? 0);
        circles.attr("cx", (item) => Math.max(item.radius, Math.min(width - item.radius, item.x ?? width / 2)))
          .attr("cy", (item) => Math.max(item.radius, Math.min(height - item.radius, item.y ?? height / 2)));
        nodeLabels.attr("x", (item) => Math.max(item.radius, Math.min(width - item.radius, item.x ?? width / 2)))
          .attr("y", (item) => Math.max(item.radius, Math.min(height - item.radius, item.y ?? height / 2)) + item.radius + 19);
      });
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(host);
    return () => { observer.disconnect(); simulation?.stop(); };
  }, [memories, selectedId]);

  return <section className="relative min-h-[520px] overflow-hidden rounded-[28px] border border-primary/10 bg-[radial-gradient(circle_at_50%_46%,#fffaf5_0,transparent_34%),linear-gradient(135deg,#fffdfb,#f5e9e1)] shadow-sm">
    <svg ref={svgRef} className="h-[520px] w-full" role="img" aria-label="Interactive memory graph where shorter links show stronger evidence-based connections, node size shows confidence, and colour shows era" />
    <div className="absolute bottom-5 left-5 z-10 flex max-w-[calc(100%-2.5rem)] flex-wrap gap-x-3 gap-y-2 rounded-2xl bg-white/80 px-4 py-3 text-xs text-text/65 shadow-sm backdrop-blur">
      <span className="font-medium text-text/75">Shorter link = stronger connection</span>
      {legend.map(([era, colour]) => <span key={era} className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colour }} />{era}</span>)}
    </div>
  </section>;
}
