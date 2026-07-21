"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { createClient } from "../lib/supabase/client";

const ownerLinks = [
  { href: "/subject/dashboard", label: "Dashboard", matches: ["/subject/dashboard", "/dashboard"] },
  { href: "/subject/emmy", label: "Talk", matches: ["/subject/emmy"] },
  { href: "/subject/memories", label: "Legacy map", matches: ["/subject/memories", "/memories", "/legacy"] },
  { href: "/subject/session", label: "Record", matches: ["/subject/session", "/session"] },
  { href: "/groups", label: "Groups", matches: ["/groups"] },
  { href: "/invitations", label: "Invitations", matches: ["/invitations"] },
  { href: "/life-profile", label: "Life profile", matches: ["/life-profile"] },
  { href: "/settings", label: "Settings", matches: ["/settings"] },
];

export function AppNav() {
  const pathname = usePathname();
  const [name, setName] = useState("Account");

  useEffect(() => {
    createClient().auth.getUser().then(({ data }) => setName(data.user?.user_metadata.full_name || data.user?.email || "Account"));
  }, []);

  return <header className="nav-shell"><Link className="brand" href="/subject/dashboard" aria-label="Emmy dashboard">Emmy<span>•</span></Link><nav aria-label="Primary navigation">{ownerLinks.map((link) => { const active = link.matches.some((match) => pathname === match || pathname.startsWith(`${match}/`)); return <Link key={link.href} href={link.href} className={active ? "nav-active" : undefined} aria-current={active ? "page" : undefined}>{link.label}</Link>; })}</nav><Link className="nav-account" href="/life-profile" aria-label="Open your Life Profile">{name}</Link></header>;
}
