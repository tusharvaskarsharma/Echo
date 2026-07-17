"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState(""), [password, setPassword] = useState(""), [remember, setRemember] = useState(true), [error, setError] = useState(""), [loading, setLoading] = useState(false);
  const destination = "/subject/dashboard";
  async function signIn(e: React.FormEvent) { e.preventDefault(); setLoading(true); setError(""); const supabase = createClient(); const { error } = await supabase.auth.signInWithPassword({ email, password }); if (error) setError(error.message); else { if (!remember) sessionStorage.setItem("echo-session-only", "true"); router.replace(destination); router.refresh(); } setLoading(false); }
  async function oauth(provider: "google" | "github") { const { error } = await createClient().auth.signInWithOAuth({ provider, options: { redirectTo: `${location.origin}/auth/callback?next=${encodeURIComponent(destination)}` } }); if (error) setError(error.message); }
  return <main className="min-h-screen flex items-center justify-center p-6 bg-background"><form onSubmit={signIn} className="clay-card p-8 w-full max-w-md space-y-5"><h1 className="text-5xl font-serif text-primary">Welcome back</h1><p>Sign in to your private Echo workspace.</p>{error && <p className="text-red-700" role="alert">{error}</p>}<input className="w-full p-3" type="email" required placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} /><input className="w-full p-3" type="password" required placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} /><label className="flex gap-2"><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />Remember me</label><button className="clay-button-primary w-full p-3" disabled={loading}>{loading ? "Signing in…" : "Sign in"}</button><div className="flex justify-between"><Link href="/forgot-password">Forgot password?</Link><Link href="/signup">Create account</Link></div><div className="grid grid-cols-2 gap-3"><button type="button" className="clay-button p-2" onClick={() => oauth("google")}>Google</button><button type="button" className="clay-button p-2" onClick={() => oauth("github")}>GitHub</button></div></form></main>;
}
