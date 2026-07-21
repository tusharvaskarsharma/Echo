"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { createClient } from "../lib/supabase/client";

const ownerLinks = [
  { href: "/subject/dashboard", label: "Dashboard", matches: ["/subject/dashboard", "/dashboard"] },
  { href: "/subject/echo", label: "Talk", matches: ["/subject/echo"] },
  { href: "/subject/memories", label: "Legacy map", matches: ["/subject/memories", "/memories", "/legacy"] },
  { href: "/subject/session", label: "Record", matches: ["/subject/session", "/session"] },
  { href: "/groups", label: "Groups", matches: ["/groups"] },
  { href: "/settings", label: "Settings", matches: ["/settings"] },
];

export function AppNav() {
  const pathname = usePathname();
  const [name, setName] = useState("Account");

  useEffect(() => {
    createClient().auth.getUser().then(({ data }) => {
      setName(data.user?.user_metadata.full_name || data.user?.email || "Account");
    });
  }, []);

  return (
    <header className="nav-shell">
      <Link className="brand" href="/subject/dashboard" aria-label="Echo dashboard">
        Echo<span>•</span>
      </Link>
      <nav aria-label="Primary navigation">
        {ownerLinks.map((link) => {
          const isActive = link.matches.some((match) => pathname === match || pathname.startsWith(`${match}/`));
          return (
            <Link key={link.href} href={link.href} className={isActive ? "nav-active" : undefined} aria-current={isActive ? "page" : undefined}>
              {link.label}
            </Link>
          );
        })}
      </nav>
      <Link className="nav-account" href="/profile" aria-label="Open your profile">
        {name}
      </Link>
    </header>
  );
}
