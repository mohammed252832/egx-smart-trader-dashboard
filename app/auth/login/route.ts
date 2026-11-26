import { redirect } from "next/navigation";
import { isAllowedEmail } from "@/lib/auth-policy";
import { getSupabaseServerClient } from "@/lib/supabase";

export async function POST(request: Request) {
  const form = await request.formData();
  const email = String(form.get("email") ?? "").trim().toLowerCase();
  const password = String(form.get("password") ?? "");
  const supabase = await getSupabaseServerClient();

  if (!supabase) redirect("/login?error=config");
  if (!isAllowedEmail(email) || password.length < 8 || password.length > 72) {
    redirect("/login?error=invalid");
  }

  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) redirect("/login?error=invalid");
  redirect("/");
}
