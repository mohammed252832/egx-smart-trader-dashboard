import "server-only";

export function getPasswordRecoveryRedirect(): string | null {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  if (!configured) return null;

  try {
    const url = new URL(configured);
    const local = url.hostname === "localhost" || url.hostname === "127.0.0.1";
    if (url.protocol !== "https:" && !(process.env.NODE_ENV !== "production" && local && url.protocol === "http:")) {
      return null;
    }
    if (url.username || url.password || url.pathname !== "/" || url.search || url.hash) return null;
    return new URL("/auth/confirm", url).toString();
  } catch {
    return null;
  }
}
