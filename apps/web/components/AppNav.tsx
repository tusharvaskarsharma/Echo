import Link from "next/link";

export function AppNav() {
  return (
    <header className="nav-shell">
      <Link className="brand" href="/">Echo<span>•</span></Link>
      <nav>
        <Link href="/subject/dashboard">My legacy</Link>
        <Link href="/subject/session">Record</Link>
        <Link href="/family/conversation/eleanor-74">Talk to Eleanor</Link>
      </nav>
      <div className="demo-badge">Demo mode</div>
    </header>
  );
}

