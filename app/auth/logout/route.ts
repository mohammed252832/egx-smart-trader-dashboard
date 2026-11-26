import { redirect } from "next/navigation";
import { getSupabaseServerClient } from "@/lib/supabase";

export async function POST() {
  const supabase = await getSupabaseServerClient();
  if (supabase) await supabase.auth.signOut({ scope: "local" });
  redirect("/login");
}
