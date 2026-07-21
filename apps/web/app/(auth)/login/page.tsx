"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const destination = "/subject/dashboard";

  useEffect(() => { setError(new URLSearchParams(window.location.search).get("error") || ""); }, []);

  async function signIn(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const { error: signInError } = await createClient().auth.signInWithPassword({ email, password });
    if (signInError) setError(signInError.message);
    else {
      if (!remember) sessionStorage.setItem("emmy-session-only", "true");
      router.replace(destination);
      router.refresh();
    }
    setLoading(false);
  }

  async function oauth(provider: "google" | "github") {
    setLoading(true);
    setError("");
    const oauthOrigin = (process.env.NEXT_PUBLIC_SITE_URL || window.location.origin).replace(/\/$/, "");
    const { error: oauthError } = await createClient().auth.signInWithOAuth({
      provider,
      options: { redirectTo: `${oauthOrigin}/auth/callback?next=${encodeURIComponent(destination)}` },
    });
    if (oauthError) {
      setError(oauthError.message);
      setLoading(false);
    }
  }

  return <main className="min-h-screen flex items-center justify-center p-6 bg-background"><form onSubmit={signIn} className="clay-card p-8 w-full max-w-md space-y-5"><h1 className="text-5xl font-serif text-primary">Welcome back</h1><p>Sign in to your private Emmy workspace.</p>{error && <p className="text-red-700" role="alert">{error}</p>}<input className="w-full p-3" type="email" required placeholder="Email" value={email} onChange={event => setEmail(event.target.value)} /><input className="w-full p-3" type="password" required placeholder="Password" value={password} onChange={event => setPassword(event.target.value)} /><label className="flex gap-2"><input type="checkbox" checked={remember} onChange={event => setRemember(event.target.checked)} />Remember me</label><button className="clay-button-primary w-full p-3" disabled={loading}>{loading ? "Signing inÃ¢â‚¬Â¦" : "Sign in"}</button><div className="flex justify-between"><Link href="/forgot-password">Forgot password?</Link><Link href="/signup">Create account</Link></div><div className="grid grid-cols-2 gap-3"><button type="button" className="clay-button p-2" disabled={loading} onClick={() => oauth("google")}>Google</button><button type="button" className="clay-button p-2" disabled={loading} onClick={() => oauth("github")}>GitHub</button></div></form></main>;
}
