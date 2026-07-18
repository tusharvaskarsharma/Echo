"use client";

import Link from "next/link";
import { ArrowLeft, BookHeart, LockKeyhole, Mic, Network, Settings, ShieldCheck, Sparkles } from "lucide-react";

import { AppNav } from "@/components/AppNav";
import { useMemoryGraph } from "@/hooks/useMemoryGraph";

export default function Legacy() {
  const { memories, isLoading } = useMemoryGraph();
  const count = memories?.length || 0;

  return <main className="min-h-screen bg-background">
    <AppNav />
    <div className="mx-auto max-w-6xl px-4 py-7 sm:px-8 sm:py-10">
      <Link href="/subject/dashboard" className="inline-flex items-center gap-2 text-sm font-medium text-text/60 transition hover:text-primary"><ArrowLeft size={16} />Back to dashboard</Link>
      <header className="mt-7 grid gap-7 border-b border-primary/10 pb-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
        <div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Your living legacy</p><h1 className="mt-2 font-serif text-5xl text-text sm:text-6xl">Preserve what matters.</h1><p className="mt-4 max-w-2xl text-base leading-7 text-text/65">Echo keeps your stories private by default. You choose which memories may become part of a family legacy.</p></div>
        <div className="rounded-[26px] border border-primary/10 bg-white/75 p-6 shadow-sm"><div className="flex items-center gap-3 text-primary"><BookHeart size={22} /><span className="text-sm font-semibold">Your preserved archive</span></div><p className="mt-4 font-serif text-5xl text-text">{isLoading ? "—" : count}</p><p className="mt-1 text-sm text-text/60">{count === 1 ? "memory held with care" : "memories held with care"}</p></div>
      </header>

      <section className="mt-8 grid gap-5 lg:grid-cols-3">
        <article className="rounded-[26px] border border-primary/10 bg-white/75 p-6 shadow-sm"><span className="inline-flex rounded-xl bg-primary/10 p-3 text-primary"><Mic size={21} /></span><h2 className="mt-5 font-serif text-3xl text-text">Capture a story</h2><p className="mt-3 text-sm leading-6 text-text/65">Record a conversation or write a memory whenever a story deserves to be kept.</p><Link href="/subject/session" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-primary hover:text-text">Start a session <span aria-hidden>→</span></Link></article>
        <article className="rounded-[26px] border border-primary/10 bg-white/75 p-6 shadow-sm"><span className="inline-flex rounded-xl bg-primary/10 p-3 text-primary"><Network size={21} /></span><h2 className="mt-5 font-serif text-3xl text-text">Shape the archive</h2><p className="mt-3 text-sm leading-6 text-text/65">Explore the connections between your stories and review each memory in your map.</p><Link href="/subject/memories" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-primary hover:text-text">Open memory map <span aria-hidden>→</span></Link></article>
        <article className="rounded-[26px] border border-primary/10 bg-white/75 p-6 shadow-sm"><span className="inline-flex rounded-xl bg-primary/10 p-3 text-primary"><Settings size={21} /></span><h2 className="mt-5 font-serif text-3xl text-text">Make it yours</h2><p className="mt-3 text-sm leading-6 text-text/65">Keep your profile, voice, notifications, and privacy preferences up to date.</p><Link href="/settings" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-primary hover:text-text">Review settings <span aria-hidden>→</span></Link></article>
      </section>

      <section className="mt-8 grid gap-5 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="rounded-[28px] border border-primary/10 bg-[#2f2a28] p-7 text-white shadow-lg"><div className="flex items-center gap-3 text-[#e7c7b8]"><ShieldCheck size={23} /><p className="text-xs font-semibold uppercase tracking-[0.18em]">Consent stays with you</p></div><h2 className="mt-5 font-serif text-4xl">Private first, always.</h2><p className="mt-4 max-w-2xl text-sm leading-7 text-white/70">Every memory starts private. Open any memory in the map when you are ready to set it to Family or Legacy. That consent setting controls what can be retrieved in family conversations.</p><Link href="/subject/memories" className="mt-6 inline-flex rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-text transition hover:bg-[#f6e8df]">Review memory consent</Link></div>
        <aside className="rounded-[28px] border border-primary/10 bg-primary/5 p-7"><Sparkles className="text-primary" size={26} /><h2 className="mt-5 font-serif text-3xl text-text">Your next chapter</h2><p className="mt-3 text-sm leading-6 text-text/65">A living legacy grows one honest memory at a time. There is no pressure to share more than you want.</p><div className="mt-6 flex items-center gap-2 text-sm font-medium text-primary"><LockKeyhole size={16} />Controlled by you</div></aside>
      </section>
    </div>
  </main>;
}
