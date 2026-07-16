"use client";
import React from 'react';
import EchoResponse from '@/components/chat/EchoResponse';

export default function FamilyChatPage({ params }: { params: { echo_id: string } }) {
  return (
    <div className="h-screen w-full flex flex-col bg-background">
      <header className="p-8 text-center border-b border-text/5 bg-white/30 backdrop-blur-md">
        <h1 className="font-serif text-4xl text-primary tracking-tight">Family Conversation</h1>
      </header>
      <main className="flex-1 overflow-hidden">
        <EchoResponse echoId={params.echo_id} />
      </main>
    </div>
  );
}
