"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Check, HeartHandshake, LoaderCircle, Save, ShieldCheck, UserRound } from "lucide-react";

import { api } from "@/lib/api";
import type { IdentityProfile } from "@/lib/types";

type Notice = { type: "success" | "error"; text: string } | null;
type TextKey = Exclude<keyof IdentityProfile, "user_id" | "date_of_birth" | "privacy_settings" | "social_links" | "created_at" | "updated_at" | "languages" | "children" | "parents" | "siblings" | "grandchildren" | "pets" | "values">;
type ListKey = "languages" | "children" | "parents" | "siblings" | "grandchildren" | "pets" | "values";

const emptyProfile: IdentityProfile = {
  user_id: "", full_name: null, preferred_name: null, date_of_birth: null, gender: null, pronouns: null,
  occupation: null, education: null, nationality: null, religion: null, languages: [], hometown: null,
  current_city: null, biography: null, spouse: null, children: [], parents: [], siblings: [], grandchildren: [],
  pets: [], website: null, social_links: {}, email: null, values: [], motto: null, favorite_quote: null,
  favorite_song: null, favorite_book: null, favorite_food: null, favorite_place: null, blood_group: null,
  allergies: null, medical_notes: null, privacy_settings: { shared_fields: [] },
};

const shareableFields: Array<[keyof Omit<IdentityProfile, "user_id" | "privacy_settings" | "created_at" | "updated_at">, string]> = [
  ["full_name", "Name"], ["preferred_name", "Preferred name"], ["occupation", "Occupation"],
  ["education", "Education"], ["nationality", "Nationality"], ["religion", "Religion"],
  ["languages", "Languages"], ["hometown", "Hometown"], ["current_city", "Current city"],
  ["biography", "Biography"], ["spouse", "Spouse"], ["children", "Children"], ["parents", "Parents"],
  ["siblings", "Siblings"], ["grandchildren", "Grandchildren"], ["pets", "Pets"], ["website", "Website"],
  ["social_links", "Social links"], ["values", "Values"], ["motto", "Motto"], ["favorite_quote", "Favorite quote"],
  ["favorite_song", "Favorite song"], ["favorite_book", "Favorite book"], ["favorite_food", "Favorite food"],
  ["favorite_place", "Favorite place"], ["date_of_birth", "Birthday"], ["gender", "Gender"], ["pronouns", "Pronouns"],
  ["email", "Email"], ["blood_group", "Blood group"], ["allergies", "Allergies"], ["medical_notes", "Medical notes"],
];

const inputClass = "mt-1.5 w-full rounded-xl border border-primary/15 bg-white px-3.5 py-2.5 text-sm text-text shadow-sm outline-none transition placeholder:text-text/35 focus:border-primary/50 focus:ring-4 focus:ring-primary/10";

const commaList = (value: string) => value.split(",").map((item) => item.trim()).filter(Boolean);

export default function LifeProfilePage() {
  const [profile, setProfile] = useState<IdentityProfile>(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  useEffect(() => {
    void (async () => {
      try {
        const loaded = await api.identity();
        setProfile({ ...emptyProfile, ...loaded, privacy_settings: loaded.privacy_settings || { shared_fields: [] } });
      } catch (error) {
        setNotice({ type: "error", text: error instanceof Error ? error.message : "Life Profile could not be loaded." });
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const shared = useMemo(() => new Set(profile.privacy_settings.shared_fields), [profile.privacy_settings.shared_fields]);
  const setText = (field: TextKey, value: string) => setProfile((current) => ({ ...current, [field]: value || null }));
  const setList = (field: ListKey, value: string) => setProfile((current) => ({ ...current, [field]: commaList(value) }));
  const toggleShared = (field: string) => setProfile((current) => {
    const currentShared = new Set(current.privacy_settings.shared_fields);
    if (currentShared.has(field)) currentShared.delete(field); else currentShared.add(field);
    return { ...current, privacy_settings: { shared_fields: Array.from(currentShared) } };
  });

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      const saved = await api.updateIdentity({
        ...profile,
        user_id: undefined,
        created_at: undefined,
        updated_at: undefined,
      });
      setProfile({ ...emptyProfile, ...saved, privacy_settings: saved.privacy_settings || { shared_fields: [] } });
      setNotice({ type: "success", text: "Your Life Profile and sharing choices are saved." });
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Life Profile could not be saved." });
    } finally {
      setSaving(false);
    }
  };

  const textFields = (fields: Array<[TextKey, string, string?]>) => fields.map(([field, label, placeholder]) => (
    <label key={field} className="text-sm font-medium text-text/75">{label}
      <input className={inputClass} value={(profile[field] as string | null) || ""} placeholder={placeholder} onChange={(event) => setText(field, event.target.value)} />
    </label>
  ));
  const listFields = (fields: Array<[ListKey, string, string?]>) => fields.map(([field, label, placeholder]) => (
    <label key={field} className="text-sm font-medium text-text/75">{label}
      <input className={inputClass} value={profile[field].join(", ")} placeholder={placeholder || "Separate names with commas"} onChange={(event) => setList(field, event.target.value)} />
    </label>
  ));

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_15%_0%,#f1e4da_0,transparent_25%),#f8f6f2] px-4 py-5 sm:px-8 sm:py-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-7 flex items-center justify-between gap-4"><Link href="/subject/dashboard" className="inline-flex items-center gap-2 rounded-xl border border-primary/10 bg-white/70 px-3.5 py-2.5 text-sm font-medium text-text/70 shadow-sm transition hover:bg-primary/10 hover:text-primary"><ArrowLeft size={17} /> Back to dashboard</Link><p className="hidden items-center gap-2 text-sm text-text/50 sm:flex"><ShieldCheck size={16} className="text-success" /> You control what groups can see</p></header>
        <div className="mb-8"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Your Emmy</p><h1 className="mt-2 font-serif text-5xl text-text sm:text-6xl">Life Profile</h1><p className="mt-3 max-w-3xl text-base leading-7 text-text/65">Save the stable facts that define you. Emmy uses these facts directly for identity questions, separately from your preserved stories.</p></div>
        <form onSubmit={save} className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
          <div className="space-y-6">
            <section className="rounded-[26px] border border-primary/10 bg-white/75 p-5 shadow-clay sm:p-7"><div className="flex items-start gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><UserRound size={19} /></span><div><h2 className="font-serif text-3xl text-text">Basic information</h2><p className="mt-1 text-sm text-text/60">The facts Emmy should always know.</p></div></div><div className="mt-6 grid gap-4 sm:grid-cols-2">{textFields([["full_name", "Full name", "Your full name"], ["preferred_name", "Preferred name", "What people call you"], ["gender", "Gender"], ["pronouns", "Pronouns", "e.g. she/her"], ["occupation", "Occupation"], ["education", "Education"], ["nationality", "Nationality"], ["religion", "Religion (optional)"], ["hometown", "Hometown"], ["current_city", "Current city"]])}<label className="text-sm font-medium text-text/75">Date of birth<input className={inputClass} type="date" value={profile.date_of_birth || ""} onChange={(event) => setProfile((current) => ({ ...current, date_of_birth: event.target.value || null }))} /></label>{listFields([["languages", "Languages", "Hindi, English"]])}<label className="sm:col-span-2 text-sm font-medium text-text/75">Biography<textarea className={`${inputClass} min-h-28 resize-y`} value={profile.biography || ""} placeholder="A concise introduction to your life." onChange={(event) => setText("biography", event.target.value)} /></label></div></section>
            <section className="rounded-[26px] border border-primary/10 bg-white/75 p-5 shadow-clay sm:p-7"><h2 className="font-serif text-3xl text-text">Family & relationships</h2><p className="mt-1 text-sm text-text/60">Use names or descriptions you are comfortable preserving.</p><div className="mt-6 grid gap-4 sm:grid-cols-2">{textFields([["spouse", "Spouse / partner"]])}{listFields([["children", "Children"], ["parents", "Parents"], ["siblings", "Siblings"], ["grandchildren", "Grandchildren"], ["pets", "Pets"]])}</div></section>
            <section className="rounded-[26px] border border-primary/10 bg-white/75 p-5 shadow-clay sm:p-7"><h2 className="font-serif text-3xl text-text">Values & favourites</h2><div className="mt-6 grid gap-4 sm:grid-cols-2">{listFields([["values", "Values", "Kindness, honesty, resilience"]])}{textFields([["motto", "Motto"], ["favorite_song", "Favorite song"], ["favorite_book", "Favorite book"], ["favorite_food", "Favorite food"], ["favorite_place", "Favorite place"]])}<label className="sm:col-span-2 text-sm font-medium text-text/75">Favorite quote<textarea className={`${inputClass} min-h-20 resize-y`} value={profile.favorite_quote || ""} onChange={(event) => setText("favorite_quote", event.target.value)} /></label></div></section>
            <section className="rounded-[26px] border border-primary/10 bg-white/75 p-5 shadow-clay sm:p-7"><h2 className="font-serif text-3xl text-text">Optional private details</h2><p className="mt-1 text-sm text-text/60">These are private by default, including contact and health details.</p><div className="mt-6 grid gap-4 sm:grid-cols-2">{textFields([["website", "Website"], ["email", "Email"], ["blood_group", "Blood group"], ["allergies", "Allergies"]])}<label className="sm:col-span-2 text-sm font-medium text-text/75">Social links<textarea className={`${inputClass} min-h-20 resize-y`} value={Object.entries(profile.social_links).map(([network, link]) => `${network}: ${link}`).join("\n")} placeholder="LinkedIn: https://..." onChange={(event) => setProfile((current) => ({ ...current, social_links: Object.fromEntries(event.target.value.split("\n").map((line) => { const divider = line.indexOf(":"); return divider < 1 ? ["", ""] : [line.slice(0, divider).trim(), line.slice(divider + 1).trim()]; }).filter(([network, link]) => network && link)) }))} /></label><label className="sm:col-span-2 text-sm font-medium text-text/75">Medical notes<textarea className={`${inputClass} min-h-24 resize-y`} value={profile.medical_notes || ""} onChange={(event) => setText("medical_notes", event.target.value)} /></label></div></section>
          </div>
          <aside className="h-fit space-y-4 lg:sticky lg:top-8"><section className="rounded-[26px] border border-primary/10 bg-[#2f2a28] p-6 text-white shadow-lg"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/55">Life Profile</p><p className="mt-2 text-sm leading-6 text-white/80">Emmy answers name, family, career, and other stable facts from this profile before it searches memories.</p><button type="submit" disabled={loading || saving} className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-primary px-4 py-3 text-sm font-semibold transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">{saving ? <LoaderCircle className="animate-spin" size={17} /> : <Save size={17} />}{saving ? "Saving..." : "Save Life Profile"}</button></section>{notice && <p className={`rounded-2xl border px-4 py-3 text-sm leading-5 ${notice.type === "success" ? "border-success/30 bg-green-50 text-green-800" : "border-red-200 bg-red-50 text-red-700"}`} role={notice.type === "error" ? "alert" : "status"}>{notice.type === "success" && <Check className="mr-2 inline" size={16} />}{notice.text}</p>}<section className="rounded-[26px] border border-primary/10 bg-white/75 p-5 shadow-sm"><div className="flex gap-2"><HeartHandshake className="mt-0.5 text-primary" size={18} /><div><h2 className="font-serif text-2xl text-text">Share with my groups</h2><p className="mt-1 text-xs leading-5 text-text/60">Only accepted members of groups with memory sharing enabled can see the fields you select.</p></div></div><div className="mt-4 max-h-[470px] space-y-2 overflow-y-auto pr-1">{shareableFields.map(([field, label]) => <label key={field} className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-primary/10 bg-white px-3 py-2.5 text-sm text-text/75"><span>{label}</span><input className="h-4 w-4 accent-primary" type="checkbox" checked={shared.has(field)} onChange={() => toggleShared(field)} /></label>)}</div></section></aside>
        </form>
      </div>
    </main>
  );
}


