export const SHARED_ACCOUNT_EMAIL = "shared@egx-smart-trader.invalid";

export function isAllowedEmail(email: string): boolean {
  return email.trim().toLowerCase() === SHARED_ACCOUNT_EMAIL;
}
