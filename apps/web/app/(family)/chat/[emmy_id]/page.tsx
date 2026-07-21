"use client";
import React from 'react';
import EmmyResponse from '@/components/chat/EmmyResponse';

export default function FamilyChatPage({ params }: { params: { emmy_id: string } }) {
  return (
    <div className="h-screen w-full flex flex-col bg-background">
      <header className="p-8 text-center border-b border-text/5 bg-white/30 backdrop-blur-md">
        <h1 className="font-serif text-4xl text-primary tracking-tight">Family Conversation</h1>
      </header>
      <main className="flex-1 overflow-hidden">
        <EmmyResponse emmyId={params.emmy_id} />
      </main>
    </div>
  );
}
