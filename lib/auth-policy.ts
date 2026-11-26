export const ALLOWED_ACCOUNT_EMAILS = [
  "kigobigo11@wm.com",
  "mohammed.fathi2532@wm.com",
  "wael@wm.com",
] as const;

export function isAllowedEmail(email: string): boolean {
  return (ALLOWED_ACCOUNT_EMAILS as readonly string[]).includes(email.trim().toLowerCase());
}
