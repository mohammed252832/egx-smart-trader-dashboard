"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { requireUser } from "@/lib/auth";
import { getSupabaseServerClient } from "@/lib/supabase";

const SYMBOL_PATTERN = /^[A-Z0-9]{1,12}$/;

export async function saveProfile(formData: FormData) {
  const user = await requireUser();
  const supabase = await getSupabaseServerClient();
  if (!supabase) redirect("/account?error=config");

  const displayName = String(formData.get("display_name") ?? "").trim();
  if (displayName.length < 2 || displayName.length > 60) redirect("/account?error=name");

  const { error } = await supabase
    .from("profiles")
    .update({
      display_name: displayName,
      alert_market_summary: formData.get("alert_market_summary") === "on",
      alert_watchlist: formData.get("alert_watchlist") === "on",
    })
    .eq("id", user.id);
  if (error) redirect("/account?error=save");

  revalidatePath("/account");
  redirect("/account?saved=1");
}

export async function addToWatchlist(formData: FormData) {
  const user = await requireUser();
  const supabase = await getSupabaseServerClient();
  if (!supabase) redirect("/account?error=config");

  const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase();
  if (!SYMBOL_PATTERN.test(symbol)) redirect("/account?error=symbol");

  const { data: stock, error: stockError } = await supabase
    .from("stocks")
    .select("symbol")
    .eq("symbol", symbol)
    .maybeSingle();
  if (stockError) redirect("/account?error=save");
  if (!stock) redirect("/account?error=unknown");

  const { error } = await supabase.from("watchlist").insert({ user_id: user.id, ticker: symbol });
  // 23505 = already in the list; treat as success.
  if (error && error.code !== "23505") redirect("/account?error=save");

  revalidatePath("/account");
  redirect("/account");
}

export async function removeFromWatchlist(formData: FormData) {
  const user = await requireUser();
  const supabase = await getSupabaseServerClient();
  if (!supabase) redirect("/account?error=config");

  const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase();
  if (!SYMBOL_PATTERN.test(symbol)) redirect("/account?error=symbol");

  const { error } = await supabase
    .from("watchlist")
    .delete()
    .eq("user_id", user.id)
    .eq("ticker", symbol);
  if (error) redirect("/account?error=save");

  revalidatePath("/account");
  redirect("/account");
}
