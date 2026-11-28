import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

type PendingCookie = { name: string; value: string; options: CookieOptions };

function isProtectedPath(pathname: string): boolean {
  return pathname === "/"
    || pathname === "/market"
    || pathname.startsWith("/market/")
    || pathname === "/charts"
    || pathname.startsWith("/charts/")
    || pathname === "/stocks"
    || pathname.startsWith("/stocks/")
    || pathname === "/account"
    || pathname.startsWith("/account/")
    || pathname === "/pending"
    || pathname === "/api/recommendations"
    || pathname === "/auth/update-password";
}

function withCookies(response: NextResponse, pendingCookies: PendingCookie[]): NextResponse {
  for (const { name, value, options } of pendingCookies) {
    response.cookies.set(name, value, options);
  }
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export async function proxy(request: NextRequest) {
  const pendingCookies: PendingCookie[] = [];
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  const protectedPath = isProtectedPath(request.nextUrl.pathname);

  if (!url || !key) {
    if (!protectedPath) return withCookies(NextResponse.next(), pendingCookies);
    if (request.nextUrl.pathname === "/api/recommendations") {
      return withCookies(NextResponse.json({ error: "Unauthorized" }, { status: 401 }), pendingCookies);
    }
    return withCookies(NextResponse.redirect(new URL("/login?error=config", request.url)), pendingCookies);
  }

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        for (const { name, value } of cookiesToSet) {
          request.cookies.set(name, value);
        }
        pendingCookies.push(...cookiesToSet);
      },
    },
  });

  let authorized = false;
  try {
    const { data, error } = await supabase.auth.getClaims();
    const claims = data?.claims;
    // Approval (profiles.status) is enforced per page and by RLS; the proxy only
    // refreshes the session and keeps signed-out visitors away from private pages.
    authorized = !error && Boolean(claims?.sub);
  } catch (error) {
    console.error("Supabase session verification failed", error);
  }

  if (!protectedPath || authorized) {
    return withCookies(NextResponse.next({ request }), pendingCookies);
  }

  if (request.nextUrl.pathname === "/api/recommendations") {
    return withCookies(NextResponse.json({ error: "Unauthorized" }, { status: 401 }), pendingCookies);
  }
  return withCookies(NextResponse.redirect(new URL("/login", request.url)), pendingCookies);
}

export const config = {
  matcher: [
    "/",
    "/market/:path*",
    "/charts/:path*",
    "/stocks/:path*",
    "/account/:path*",
    "/pending",
    "/api/recommendations",
    "/login",
    "/signup",
    "/forgot-password",
    "/auth/:path*",
  ],
};
