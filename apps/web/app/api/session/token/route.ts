import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

/**
 * Authenticated proxy for a Gemini Live ephemeral token.  Gemini API keys must
 * never reach the browser; FastAPI validates the Supabase bearer token first.
 */
export async function POST() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const supabase = createClient();
  const { data: userData, error: userError } = await supabase.auth.getUser();
  if (userError || !userData.user) {
    return NextResponse.json({ error: "Your session has expired. Please sign in again." }, { status: 401 });
  }
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
  if (sessionError || !sessionData.session) {
    return NextResponse.json({ error: "Unable to retrieve your session." }, { status: 401 });
  }

  const response = await fetch(`${apiBaseUrl}/api/session/token`, {
    method: "POST",
    headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
    cache: "no-store",
  });
  const body = await response.text();
  if (!response.ok) console.error("[session/token] Gemini token endpoint returned", response.status, body);
  return new NextResponse(body, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
  });
}
