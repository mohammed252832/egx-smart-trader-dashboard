import "server-only";

import { redirect } from "next/navigation";
import { isAllowedEmail } from "./auth-policy";
import { getSupabaseServerClient } from "./supabase";

export type AppUser = {
  id: string;
  email: string;
};

export async function getCurrentUser(): Promise<AppUser | null> {
  const supabase = await getSupabaseServerClient();
  if (!supabase) return null;

  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) return null;

  const email = data.user.email?.trim().toLowerCase() ?? "";
  if (!isAllowedEmail(email) || data.user.app_metadata?.role !== "member") return null;

  return { id: data.user.id, email };
}

export async function requireUser(): Promise<AppUser> {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  return user;
}
