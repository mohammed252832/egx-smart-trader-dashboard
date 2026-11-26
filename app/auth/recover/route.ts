import { redirect } from "next/navigation";
import { isAllowedEmail } from "@/lib/auth-policy";
import { getSupabaseServerClient } from "@/lib/supabase";
import { getPasswordRecoveryRedirect } from "@/lib/site-url";

export async function POST(request: Request) {
  const form = await request.formData();
  const email = String(form.get("email") ?? "").trim().toLowerCase();
  const redirectTo = getPasswordRecoveryRedirect();
  const supabase = await getSupabaseServerClient();

  if (!supabase || !redirectTo) redirect("/forgot-password?error=config");

  if (isAllowedEmail(email)) {
    const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
    if (error) redirect("/forgot-password?error=send");
  }

  redirect("/forgot-password?sent=1");
}
