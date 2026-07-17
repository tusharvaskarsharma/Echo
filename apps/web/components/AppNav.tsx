"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "../lib/supabase/client";

export function AppNav() {
  const [name, setName] = useState("Account");
  useEffect(() => { createClient().auth.getUser().then(({ data }) => setName(data.user?.user_metadata.full_name || data.user?.email || "Account")); }, []);
  return <header className="nav-shell"><Link className="brand" href="/">Echo<span>•</span></Link><nav><Link href="/subject/dashboard">My legacy</Link><Link href="/subject/session">Record</Link><Link href="/settings">Settings</Link></nav><span className="text-sm text-text/70">{name}</span></header>;
}
