import { redirect } from "next/navigation";
import { getSupabaseServerClient } from "@/lib/supabase";

export async function POST(request: Request) {
  const form = await request.formData();
  const email = String(form.get("email") ?? "").trim().toLowerCase();
  const password = String(form.get("password") ?? "");
  const supabase = await getSupabaseServerClient();

  if (!supabase) redirect("/login?error=config");
  if (!email || email.length > 254 || password.length < 8 || password.length > 72) {
    redirect("/login?error=invalid");
  }

  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    redirect(error.code === "email_not_confirmed" ? "/login?error=unconfirmed" : "/login?error=invalid");
  }
  redirect("/");
}
