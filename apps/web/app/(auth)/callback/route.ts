import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const requestedNext = request.nextUrl.searchParams.get("next");
  // OAuth redirects must never turn this callback into an open redirect.
  const next = requestedNext?.startsWith("/") && !requestedNext.startsWith("//")
    ? requestedNext
    : "/subject/dashboard";
  const response = NextResponse.redirect(new URL(next, request.url));
  const code = request.nextUrl.searchParams.get("code");

  if (!code) {
    return NextResponse.redirect(new URL("/login?error=OAuth%20callback%20did%20not%20include%20an%20authorization%20code.", request.url));
  }

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      auth: { flowType: "pkce" },
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (values: any[]) => values.forEach(({ name, value, options }) => response.cookies.set(name, value, options)),
      },
    },
  );
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) {
    return NextResponse.redirect(new URL(`/login?error=${encodeURIComponent("OAuth sign-in could not be completed. Please try again.")}`, request.url));
  }

  return response;
}
