import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  // Client components are evaluated while Next prerenders routes.  Do not
  // construct a browser client until code runs in a browser.
  if (typeof window === "undefined") return null as never;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) throw new Error("Supabase public environment variables are not configured.");
  return createBrowserClient(url, key);
}
