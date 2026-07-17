import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
const publicPaths = ["/", "/login", "/signup", "/forgot-password", "/reset-password", "/verify-email", "/auth/callback"];
export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL, key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return response;
  const supabase = createServerClient(url, key, { cookies: { getAll: () => request.cookies.getAll(), setAll: (values: any[]) => values.forEach(({ name, value, options }) => response.cookies.set(name, value, options)) }});
  const { data: { user } } = await supabase.auth.getUser();
  const isPublic = publicPaths.some((p) => request.nextUrl.pathname === p || request.nextUrl.pathname.startsWith(`${p}/`));
  if (!user && !isPublic) { const login = request.nextUrl.clone(); login.pathname = "/login"; login.searchParams.set("next", request.nextUrl.pathname); return NextResponse.redirect(login); }
  if (user && ["/login", "/signup"].includes(request.nextUrl.pathname)) { const dashboard = request.nextUrl.clone(); dashboard.pathname = "/subject/dashboard"; return NextResponse.redirect(dashboard); }
  return response;
}
export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
