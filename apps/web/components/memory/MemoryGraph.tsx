"use client";
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { Memory } from '@/hooks/useMemoryGraph';

interface MemoryGraphProps {
  memories: Memory[];
  onNodeClick: (memory: Memory) => void;
  selectedId: string | null;
}

export default function MemoryGraph({ memories, onNodeClick, selectedId }: MemoryGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !memories.length) return;

    const width = svgRef.current.clientWidth || window.innerWidth;
    const height = svgRef.current.clientHeight || window.innerHeight;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // clear on re-render

    const nodes = memories.map(m => ({ ...m, radius: 15 + (m.emotion_tags.length * 4) }));
    
    // Create links based on shared topics
    const links: any[] = [];
    for(let i=0; i<nodes.length; i++) {
        for(let j=i+1; j<nodes.length; j++) {
            const shared = nodes[i].topics.filter(t => nodes[j].topics.includes(t));
            if(shared.length > 0) {
                links.push({ source: nodes[i].id, target: nodes[j].id, value: shared.length });
            }
        }
    }

    const simulation = d3.forceSimulation(nodes as any)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(120))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius((d: any) => d.radius + 10));

    const link = svg.append("g")
      .attr("stroke", "#D8C6B8")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", d => Math.sqrt(d.value));

    const node = svg.append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", d => d.radius)
      .attr("fill", d => d.id === selectedId ? "#A77464" : "#D8C6B8")
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .on("click", (event, d) => onNodeClick(d as Memory));

    node.append("title")
      .text(d => d.content.substring(0, 50) + "...");

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node
        .attr("cx", (d: any) => Math.max(d.radius, Math.min(width - d.radius, d.x)))
        .attr("cy", (d: any) => Math.max(d.radius, Math.min(height - d.radius, d.y)));
    });

    // Add drag behavior
    const drag = d3.drag<SVGCircleElement, any>()
        .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        })
        .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
        })
        .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        });
        
    node.call(drag as any);

    return () => {
      simulation.stop();
    };
  }, [memories, selectedId, onNodeClick]);

  return (
    <svg ref={svgRef} className="w-full h-full absolute inset-0 z-0" />
  );
}