"use client";
import React from 'react';
import { useMemoryGraph } from '@/hooks/useMemoryGraph';
import MemoryDetails from '@/components/memory/MemoryDetails';
import { useRouter } from 'next/navigation';

export default function MemorySinglePage({ params }: { params: { id: string } }) {
  const { memories, isLoading, patchConsent } = useMemoryGraph();
  const router = useRouter();

  if (isLoading) return <div className="p-8">Loading...</div>;

  const memory = memories?.find(m => m.id === params.id) || null;

  if (!memory) return <div className="p-8 text-center font-serif text-2xl text-text">Memory not found.</div>;

  return (
    <div className="min-h-screen bg-background p-8 relative overflow-hidden">
        <div className="text-text/70 font-serif text-2xl mb-8">Memory Record</div>
        <MemoryDetails 
            memory={memory}
            onClose={() => router.push('/memories')}
            onConsentChange={patchConsent}
        />
    </div>
  );
}