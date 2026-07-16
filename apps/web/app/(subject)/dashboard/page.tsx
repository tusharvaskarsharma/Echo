import Link from "next/link";
import { Mic, Settings, BookOpen } from "lucide-react";
import FineTuneStatusCard from "@/components/dashboard/FineTuneStatusCard";

export default function Dashboard() {
  return (
    <div className="min-h-screen p-6 md:p-12 max-w-6xl mx-auto flex flex-col gap-12 bg-background relative overflow-hidden">
      <header className="flex justify-between items-center w-full z-10 relative">
        <h1 className="text-5xl font-serif text-primary tracking-tight">Echo.</h1>
        <Link href="/legacy" className="clay-button p-4 text-text/70">
          <Settings className="w-6 h-6" />
        </Link>
      </header>

      <main className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-4 z-10 relative">
        {/* Welcome Hero */}
        <div className="clay-card p-10 md:p-16 flex flex-col items-center justify-center text-center gap-6 md:col-span-2 bg-secondary/10">
          <h2 className="text-5xl md:text-6xl font-serif text-primary">Welcome back, Grandma.</h2>
          <p className="text-2xl text-text/80 max-w-2xl mt-2">
            Your living legacy is growing. We have a few more stories to capture today whenever you're ready.
          </p>
          <Link href="/session" className="clay-button-primary px-10 py-5 text-2xl mt-8 flex items-center gap-4">
            <Mic className="w-8 h-8" />
            Start New Session
          </Link>
        </div>

        {/* Previous Sessions */}
        <div className="clay-card p-8 bg-white/20">
          <h3 className="text-3xl font-serif mb-6 text-primary flex items-center gap-3">
            <BookOpen className="w-7 h-7" />
            Previous Sessions
          </h3>
          <ul className="space-y-4">
            {["Childhood Memories", "Meeting Grandpa", "First Job"].map((session, i) => (
              <li key={i} className="p-5 rounded-clay hover:bg-white/50 cursor-pointer transition-colors border border-transparent hover:border-white/40 flex justify-between items-center">
                <p className="text-xl font-medium">{session}</p>
                <p className="text-text/60 text-lg">Oct {10 - i}, 2026</p>
              </li>
            ))}
          </ul>
        </div>
        
        {/* AI Persona Training Status */}
        <div className="col-span-1 md:col-span-1 h-full">
          <FineTuneStatusCard />
        </div>
      </main>
    </div>
  );
}