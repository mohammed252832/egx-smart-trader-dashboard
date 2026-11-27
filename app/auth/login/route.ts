import { redirect } from "next/navigation";
import { SHARED_ACCOUNT_EMAIL } from "@/lib/auth-policy";
import { getSupabaseServerClient } from "@/lib/supabase";

export async function POST(request: Request) {
  const form = await request.formData();
  const password = String(form.get("password") ?? "");
  const supabase = await getSupabaseServerClient();

  if (!supabase) redirect("/login?error=config");
  if (password.length < 8 || password.length > 72) {
    redirect("/login?error=invalid");
  }

  const { error } = await supabase.auth.signInWithPassword({
    email: SHARED_ACCOUNT_EMAIL,
    password,
  });
  if (error) redirect("/login?error=invalid");
  redirect("/");
}
