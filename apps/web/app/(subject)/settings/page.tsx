"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Check, ChevronRight, Download, LoaderCircle, LogOut, Save, ShieldCheck, Trash2, UserRound } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { API_BASE } from "@/lib/api";

type ProfileForm = {
  full_name: string;
  username: string;
  bio: string;
  timezone: string;
  language: string;
  country: string;
  theme_preference: string;
  notifications: boolean;
  share_data: boolean;
};

const initial: ProfileForm = {
  full_name: "", username: "", bio: "", timezone: "UTC", language: "en", country: "",
  theme_preference: "system", notifications: true, share_data: false,
};

type Notice = { type: "success" | "error"; text: string } | null;
type UsernameStatus = "idle" | "invalid" | "checking" | "available" | "taken";

const usernameSyntaxError = (username: string) => {
  if (username.length < 3 || username.length > 30) return "Username must be between 3 and 30 characters";
  if (!/^[a-z0-9_]+$/.test(username)) return "Only lowercase letters, numbers and underscore allowed";
  return null;
};

export default function SettingsPage() {
  const router = useRouter();
  const [form, setForm] = useState<ProfileForm>(initial);
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [usernameStatus, setUsernameStatus] = useState<UsernameStatus>("idle");
  const [usernameMessage, setUsernameMessage] = useState("");
  const loadedUsername = useRef("");

  const setValue = <Key extends keyof ProfileForm>(key: Key, value: ProfileForm[Key]) => setForm((current) => ({ ...current, [key]: value }));

  useEffect(() => {
    const loadProfile = async () => {
      const supabase = createClient();
      const { data: { user }, error: userError } = await supabase.auth.getUser();
      if (userError || !user) {
        router.replace("/login?next=/settings");
        return;
      }
      setEmail(user.email || "");
      const { data, error } = await supabase.from("profiles").select("*").eq("id", user.id).maybeSingle();
      if (error) {
        setNotice({ type: "error", text: `Unable to load your saved profile: ${error.message}` });
      } else if (data) {
        setForm({
          full_name: data.full_name || "",
          username: data.username || "",
          bio: data.bio || "",
          timezone: data.timezone || "UTC",
          language: data.language || "en",
          country: data.country || "",
          theme_preference: data.theme_preference || "system",
          notifications: data.notification_preferences?.email ?? true,
          share_data: data.privacy_settings?.share_data ?? false,
        });
        loadedUsername.current = data.username || "";
      }
      setIsLoading(false);
    };
    void loadProfile();
  }, [router]);

  useEffect(() => {
    const username = form.username.trim().toLowerCase();
    const syntaxError = usernameSyntaxError(username);
    if (syntaxError) {
      setUsernameStatus("invalid");
      setUsernameMessage(syntaxError);
      return;
    }
    if (username === loadedUsername.current) {
      setUsernameStatus("available");
      setUsernameMessage("Username available");
      return;
    }

    let cancelled = false;
    setUsernameStatus("checking");
    setUsernameMessage("Checking username...");
    const timeout = window.setTimeout(async () => {
      try {
        const { data: { session } } = await createClient().auth.getSession();
        const response = await fetch(`${API_BASE}/profile/check-username?username=${encodeURIComponent(username)}`, {
          headers: { Authorization: `Bearer ${session?.access_token ?? ""}` },
        });
        const result = await response.json().catch(() => null);
        if (cancelled) return;
        if (!response.ok) throw new Error(result?.detail || "Unable to check username");
        setUsernameStatus(result.available ? "available" : "taken");
        setUsernameMessage(result.available ? "Username available" : result.reason || "Username already taken");
      } catch (error) {
        if (!cancelled) {
          setUsernameStatus("invalid");
          setUsernameMessage(error instanceof Error ? error.message : "Unable to check username");
        }
      }
    }, 400);
    return () => { cancelled = true; window.clearTimeout(timeout); };
  }, [form.username]);

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setNotice(null);
    if (usernameStatus !== "available") {
      setNotice({ type: "error", text: usernameMessage || "Choose an available username before saving." });
      return;
    }
    const usernameChanged = Boolean(loadedUsername.current && form.username.trim().toLowerCase() !== loadedUsername.current);
    if (usernameChanged && !window.confirm("Change your username? Family members use it to invite you, so confirm this change before saving.")) return;
    setIsSaving(true);
    const supabase = createClient();
    const { data: { user }, error: userError } = await supabase.auth.getUser();
    if (userError || !user) {
      setNotice({ type: "error", text: "Your sign-in session has expired. Please sign in again." });
      setIsSaving(false);
      return;
    }
    const profile = {
      full_name: form.full_name.trim() || null,
      username: form.username.trim().toLowerCase(),
      bio: form.bio.trim() || null,
      timezone: form.timezone.trim() || "UTC",
      language: form.language.trim() || "en",
      country: form.country.trim() || null,
      theme_preference: form.theme_preference,
      notifications: form.notifications,
      share_data: form.share_data,
      confirm_username_change: usernameChanged,
    };
    const { data: { session } } = await supabase.auth.getSession();
    const response = await fetch(`${API_BASE}/profile`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${session?.access_token ?? ""}` },
      body: JSON.stringify(profile),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      setNotice({ type: "error", text: `Settings could not be saved: ${data?.detail || "Please try again."}` });
      if (response.status === 409) { setUsernameStatus("taken"); setUsernameMessage("Username already taken"); }
    } else {
      setForm((current) => ({
        ...current,
        full_name: data.full_name || "",
        username: data.username || "",
        bio: data.bio || "",
        timezone: data.timezone || "UTC",
        language: data.language || "en",
        country: data.country || "",
        theme_preference: data.theme_preference || "system",
        notifications: data.notification_preferences?.email ?? current.notifications,
        share_data: data.privacy_settings?.share_data ?? current.share_data,
      }));
      loadedUsername.current = data.username || "";
      setUsernameStatus("available");
      setUsernameMessage("Username available");
      setNotice({ type: "success", text: "Your settings are saved securely." });
    }
    setIsSaving(false);
  };

  const logout = async () => {
    await createClient().auth.signOut();
    router.replace("/login");
    router.refresh();
  };

  const exportData = async () => {
    const { data, error } = await createClient().from("profiles").select("*");
    if (error) { setNotice({ type: "error", text: `Data export failed: ${error.message}` }); return; }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(blob);
    anchor.download = "echo-profile-data.json";
    anchor.click();
    URL.revokeObjectURL(anchor.href);
  };

  const destroy = async () => {
    if (!window.confirm("This permanently deletes your Echo account and data. Continue?")) return;
    const { data: { session } } = await createClient().auth.getSession();
    await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/account`, { method: "DELETE", headers: { Authorization: `Bearer ${session?.access_token}` } });
    await createClient().auth.signOut();
    router.replace("/login");
  };

  const inputClass = "mt-1.5 w-full rounded-xl border border-primary/15 bg-white px-3.5 py-2.5 text-sm text-text shadow-sm outline-none transition placeholder:text-text/35 focus:border-primary/50 focus:ring-4 focus:ring-primary/10";
  const usernameInputClass = `${inputClass} ${usernameStatus === "available" ? "border-success/70 focus:border-success focus:ring-success/10" : usernameStatus === "invalid" || usernameStatus === "taken" ? "border-red-400 focus:border-red-500 focus:ring-red-100" : ""}`;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_15%_0%,#f1e4da_0,transparent_25%),#f8f6f2] px-4 py-5 sm:px-8 sm:py-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-7 flex items-center justify-between gap-4">
          <Link href="/subject/dashboard" className="inline-flex items-center gap-2 rounded-xl border border-primary/10 bg-white/70 px-3.5 py-2.5 text-sm font-medium text-text/70 shadow-sm transition hover:bg-primary/10 hover:text-primary"><ArrowLeft size={17} /> Back to dashboard</Link>
          <p className="hidden items-center gap-2 text-sm text-text/50 sm:flex"><ShieldCheck size={16} className="text-success" /> Private account settings</p>
        </header>

        <div className="mb-8"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Your Echo</p><h1 className="mt-2 font-serif text-5xl text-text sm:text-6xl">Settings</h1><p className="mt-3 max-w-2xl text-base leading-7 text-text/65">Manage your profile, preferences, and privacy. Changes are saved to your private account.</p></div>

        <form onSubmit={save} className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
          <div className="space-y-6">
            <section className="rounded-[26px] border border-primary/10 bg-white/75 p-5 shadow-clay sm:p-7">
              <div className="flex items-start gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><UserRound size={19} /></span><div><h2 className="font-serif text-3xl text-text">Profile</h2><p className="mt-1 text-sm text-text/60">The details that make your Echo feel personal.</p></div></div>
              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium text-text/75">Full name<input className={inputClass} placeholder="Your full name" value={form.full_name} onChange={(event) => setValue("full_name", event.target.value)} /></label>
                <label className="text-sm font-medium text-text/75">Username
                  <span className="relative block"><input className={usernameInputClass} placeholder="your_username" value={form.username} onChange={(event) => setValue("username", event.target.value.trim().toLowerCase())} aria-describedby="username-feedback" aria-invalid={usernameStatus === "invalid" || usernameStatus === "taken"} />
                    <span className="pointer-events-none absolute right-3.5 top-[1.05rem]">{usernameStatus === "checking" ? <LoaderCircle className="animate-spin text-text/45" size={17} /> : usernameStatus === "available" ? <Check className="text-success" size={17} /> : null}</span>
                  </span>
                  <span id="username-feedback" className={`mt-1.5 block text-xs ${usernameStatus === "available" ? "text-success" : usernameStatus === "checking" ? "text-text/50" : "text-red-600"}`} role={usernameStatus === "invalid" || usernameStatus === "taken" ? "alert" : "status"}>{usernameMessage || "Use 3–30 lowercase letters, numbers, or underscores. Changes require confirmation."}</span>
                </label>
                <label className="sm:col-span-2 text-sm font-medium text-text/75">Bio<textarea className={`${inputClass} min-h-24 resize-y`} placeholder="A few words about you and the stories you want to preserve." value={form.bio} onChange={(event) => setValue("bio", event.target.value)} /></label>
                <label className="text-sm font-medium text-text/75">Timezone<input className={inputClass} placeholder="Asia/Kolkata" value={form.timezone} onChange={(event) => setValue("timezone", event.target.value)} /></label>
                <label className="text-sm font-medium text-text/75">Country<input className={inputClass} placeholder="India" value={form.country} onChange={(event) => setValue("country", event.target.value)} /></label>
                <label className="text-sm font-medium text-text/75">Language<input className={inputClass} placeholder="en" value={form.language} onChange={(event) => setValue("language", event.target.value)} /></label>
              </div>
            </section>

            <section className="rounded-[26px] border border-primary/10 bg-white/75 p-5 shadow-clay sm:p-7">
              <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Experience</p><h2 className="mt-1 font-serif text-3xl text-text">Appearance & privacy</h2></div>
              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <label className="text-sm font-medium text-text/75">Theme preference<select className={inputClass} value={form.theme_preference} onChange={(event) => setValue("theme_preference", event.target.value)}><option value="system">System default</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
                <div className="rounded-2xl border border-primary/10 bg-[#fcf7f3] p-4 text-sm leading-6 text-text/65">Voice and AI preferences remain private to your account. They are used only to personalise your Echo experience.</div>
              </div>
              <div className="mt-5 space-y-3">
                <label className="flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-primary/10 bg-white px-4 py-3.5"><span><span className="block text-sm font-semibold text-text">Email notifications</span><span className="mt-0.5 block text-xs text-text/55">Receive account and activity updates.</span></span><input className="h-5 w-5 accent-primary" type="checkbox" checked={form.notifications} onChange={(event) => setValue("notifications", event.target.checked)} /></label>
                <label className="flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-primary/10 bg-white px-4 py-3.5"><span><span className="block text-sm font-semibold text-text">Anonymous improvement data</span><span className="mt-0.5 block text-xs text-text/55">Share anonymised usage data to improve Echo.</span></span><input className="h-5 w-5 accent-primary" type="checkbox" checked={form.share_data} onChange={(event) => setValue("share_data", event.target.checked)} /></label>
              </div>
            </section>
          </div>

          <aside className="h-fit space-y-4 lg:sticky lg:top-8">
            <section className="rounded-[26px] border border-primary/10 bg-[#2f2a28] p-6 text-white shadow-lg"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/55">Signed in as</p><p className="mt-2 break-all text-sm text-white/90">{isLoading ? "Loading account..." : email}</p><div className="mt-6 border-t border-white/10 pt-5"><button type="submit" disabled={isLoading || isSaving || usernameStatus !== "available"} className="flex w-full items-center justify-center gap-2 rounded-2xl bg-primary px-4 py-3 text-sm font-semibold transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">{isSaving ? <LoaderCircle className="animate-spin" size={17} /> : <Save size={17} />}{isSaving ? "Saving settings..." : "Save changes"}</button></div></section>
            {notice && <p className={`rounded-2xl border px-4 py-3 text-sm leading-5 ${notice.type === "success" ? "border-success/30 bg-green-50 text-green-800" : "border-red-200 bg-red-50 text-red-700"}`} role={notice.type === "error" ? "alert" : "status"}>{notice.type === "success" && <Check className="mr-2 inline" size={16} />}{notice.text}</p>}
            <section className="rounded-[26px] border border-primary/10 bg-white/75 p-5 shadow-sm"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-text/45">Account actions</p><div className="mt-3 divide-y divide-primary/10"><button type="button" onClick={exportData} className="flex w-full items-center justify-between py-3 text-left text-sm font-medium text-text/75 hover:text-primary"><span className="flex items-center gap-2"><Download size={16} /> Export my profile data</span><ChevronRight size={16} /></button><button type="button" onClick={logout} className="flex w-full items-center justify-between py-3 text-left text-sm font-medium text-text/75 hover:text-primary"><span className="flex items-center gap-2"><LogOut size={16} /> Log out</span><ChevronRight size={16} /></button></div></section>
            <button type="button" onClick={destroy} className="flex w-full items-center justify-center gap-2 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700 transition hover:bg-red-100"><Trash2 size={16} /> Delete account</button>
          </aside>
        </form>
      </div>
    </main>
  );
}
