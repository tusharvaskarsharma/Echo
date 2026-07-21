import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const CALLBACK_ERROR = "OAuth sign-in could not be completed. Please try again.";

function redirectToLogin(request: NextRequest, message: string) {
  const response = NextResponse.redirect(
    new URL(`/login?error=${encodeURIComponent(message)}`, request.url),
  );
  // This route can set the user's session cookies. It must never be cached.
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export async function GET(request: NextRequest) {
  const requestedNext = request.nextUrl.searchParams.get("next");
  // OAuth redirects must never turn this callback into an open redirect.
  const next = requestedNext?.startsWith("/") && !requestedNext.startsWith("//")
    ? requestedNext
    : "/subject/dashboard";
  const code = request.nextUrl.searchParams.get("code");

  if (!code) {
    return redirectToLogin(
      request,
      "OAuth callback did not include an authorization code.",
    );
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    console.error("Supabase public environment variables are not configured for the auth callback.");
    return redirectToLogin(request, CALLBACK_ERROR);
  }

  try {
    const response = NextResponse.redirect(new URL(next, request.url));
    // Auth exchanges write session cookies, so a shared cache would be unsafe.
    response.headers.set("Cache-Control", "private, no-store");
    const supabase = createServerClient(url, key, {
      auth: { flowType: "pkce" },
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (values: any[]) =>
          values.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          ),
      },
    });
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) {
      console.error("Supabase auth callback rejected the authorization code:", error.message);
      return redirectToLogin(request, CALLBACK_ERROR);
    }

    return response;
  } catch (error) {
    // Network and configuration failures are thrown by the SDK instead of
    // being returned in its result. Convert those into a safe login redirect
    // instead of letting Vercel return a raw 500 page.
    console.error(
      "Supabase auth callback failed:",
      error instanceof Error ? error.message : "Unknown callback failure",
    );
    return redirectToLogin(request, CALLBACK_ERROR);
  }
}
