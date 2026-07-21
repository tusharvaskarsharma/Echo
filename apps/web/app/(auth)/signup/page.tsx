"use client";

import Link from "next/link";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function Signup() {
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError("");
    const canonicalUsername = username.trim().toLowerCase();
    if (!/^[a-z0-9_]{3,30}$/.test(canonicalUsername)) { setError("Use 3–30 lowercase letters, numbers, or underscores."); return; }
    const { error: signupError } = await createClient().auth.signUp({ email, password, options: { data: { full_name: name.trim(), username: canonicalUsername }, emailRedirectTo: `${location.origin}/auth/callback` } });
    if (signupError) setError(signupError.message); else setMessage("Check your email to verify your account, then sign in.");
  };
  return <main className="min-h-screen flex items-center justify-center p-6 bg-background"><form onSubmit={submit} className="clay-card p-8 w-full max-w-md space-y-5"><h1 className="text-5xl font-serif text-primary">Create account</h1>{message && <p role="status">{message}</p>}{error && <p className="text-red-700" role="alert">{error}</p>}<input className="w-full p-3" required placeholder="Full name" value={name} onChange={(event) => setName(event.target.value)} /><label className="block"><input className="w-full p-3" required minLength={3} maxLength={30} pattern="[a-z0-9_]+" placeholder="Username" value={username} onChange={(event) => setUsername(event.target.value.toLowerCase().replace(/\s/g, ""))} /><span className="mt-1 block text-xs text-text/55">Used for private family invitations. 3–30 lowercase letters, numbers, or underscores.</span></label><input className="w-full p-3" type="email" required placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} /><input className="w-full p-3" type="password" minLength={8} required placeholder="Password (8+ characters)" value={password} onChange={(event) => setPassword(event.target.value)} /><button className="clay-button-primary w-full p-3">Create secure account</button><Link href="/login">Already have an account? Sign in</Link></form></main>;
}
