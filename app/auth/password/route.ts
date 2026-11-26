import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { getSupabaseServerClient } from "@/lib/supabase";

export async function POST(request: Request) {
  if (!(await getCurrentUser())) redirect("/login?error=link");

  const form = await request.formData();
  const password = String(form.get("password") ?? "");
  if (password.length < 8 || password.length > 72) redirect("/auth/update-password?error=weak");

  const supabase = await getSupabaseServerClient();
  if (!supabase) redirect("/login?error=config");

  const { error } = await supabase.auth.updateUser({ password });
  if (error) redirect("/auth/update-password?error=failed");
  redirect("/");
}
