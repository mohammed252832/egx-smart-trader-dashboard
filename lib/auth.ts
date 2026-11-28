import "server-only";

import { cache } from "react";
import { redirect } from "next/navigation";
import { getSupabaseServerClient } from "./supabase";

export type AccountStatus = "pending" | "approved" | "blocked";

export type AppUser = {
  id: string;
  email: string;
  displayName: string;
  status: AccountStatus;
};

function toStatus(value: unknown): AccountStatus {
  return value === "approved" || value === "blocked" ? value : "pending";
}

/** Signed-in user plus approval status (profiles.status). Null when signed out. */
export const getCurrentUser = cache(async (): Promise<AppUser | null> => {
  const supabase = await getSupabaseServerClient();
  if (!supabase) return null;

  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) return null;

  const email = data.user.email?.trim().toLowerCase() ?? "";
  const { data: profile } = await supabase
    .from("profiles")
    .select("display_name,status")
    .eq("id", data.user.id)
    .maybeSingle();

  const fallbackName = email.split("@")[0] || "حسابي";
  return {
    id: data.user.id,
    email,
    displayName: (profile?.display_name as string | null | undefined)?.trim() || fallbackName,
    status: toStatus(profile?.status),
  };
});

/** Pages that show market data: signed in AND approved. */
export async function requireUser(): Promise<AppUser> {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (user.status !== "approved") redirect("/pending");
  return user;
}
