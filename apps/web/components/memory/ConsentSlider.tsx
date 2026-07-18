"use client";

type Consent = "private" | "family" | "legacy";

export default function ConsentSlider({ consent, onChange }: { consent: Consent; onChange: (level: Consent) => void }) {
  const levels: { id: Consent; label: string }[] = [{ id: "private", label: "Private" }, { id: "family", label: "Family" }, { id: "legacy", label: "Legacy" }];
  return <div className="flex w-full rounded-full bg-secondary/20 p-1 shadow-inner">{levels.map((level) => <button key={level.id} type="button" onClick={() => onChange(level.id)} aria-pressed={consent === level.id} className={`flex-1 rounded-full px-1 py-2 text-xs font-medium transition-all duration-300 md:text-sm ${consent === level.id ? "bg-background text-primary shadow-clay" : "text-text/70 hover:text-text"}`}>{level.label}</button>)}</div>;
}
