import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
export const dynamic = "force-dynamic";
export async function GET(request: NextRequest) {
  const response = NextResponse.redirect(new URL(request.nextUrl.searchParams.get("next") || "/subject/dashboard", request.url));
  const code = request.nextUrl.searchParams.get("code");
  if (code) {
    const supabase = createServerClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, { cookies: { getAll: () => request.cookies.getAll(), setAll: (values: any[]) => values.forEach(({ name, value, options }) => response.cookies.set(name, value, options)) }});
    await supabase.auth.exchangeCodeForSession(code);
  }
  return response;
}
