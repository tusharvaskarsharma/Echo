import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export function createClient() {
  const cookieStore = cookies();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) throw new Error("Supabase public environment variables are not configured.");
  return createServerClient(url, key, { cookies: {
    getAll: () => cookieStore.getAll(),
    setAll: (values: any[]) => { try { values.forEach(({ name, value, options }) => cookieStore.set(name, value, options)); } catch {} },
  }});
}
