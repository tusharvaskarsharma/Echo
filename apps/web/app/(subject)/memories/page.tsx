"use client";
import React, { useState } from 'react';
import MemoryGraph from '@/components/memory/MemoryGraph';
import MemoryDetails from '@/components/memory/MemoryDetails';
import { useMemoryGraph, Memory } from '@/hooks/useMemoryGraph';

export default function MemoriesPage() {
  const { memories, isLoading, patchConsent } = useMemoryGraph();
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-pulse text-primary font-serif text-2xl">Loading your constellation...</div>
      </div>
    );
  }

  if (!memories || memories.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background p-8 text-center">
        <div>
          <h1 className="font-serif text-4xl text-text mb-4">No Memories Yet</h1>
          <p className="text-text/70">Complete an interview session to start building your constellation.</p>
        </div>
      </div>
    );
  }

  const activeMemory = selectedMemory ? memories.find(m => m.id === selectedMemory.id) || null : null;

  return (
    <div className="relative w-full h-screen bg-background overflow-hidden">
      <div className="absolute top-8 left-8 z-10 pointer-events-none bg-background/50 backdrop-blur-md p-6 rounded-clay shadow-clay-sm border border-white/50">
        <h1 className="font-serif text-4xl text-text mb-2">Memory Constellation</h1>
        <p className="text-text/70 text-lg max-w-sm">
          Explore the web of stories and relationships that make up your legacy. Click on any memory to control its privacy.
        </p>
      </div>

      <MemoryGraph 
        memories={memories} 
        onNodeClick={setSelectedMemory} 
        selectedId={activeMemory?.id || null} 
      />

      <MemoryDetails 
        memory={activeMemory} 
        onClose={() => setSelectedMemory(null)}
        onConsentChange={patchConsent}
      />
    </div>
  );
}