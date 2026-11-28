import { redirect } from "next/navigation";
import { getPasswordRecoveryRedirect } from "@/lib/site-url";
import { getSupabaseServerClient } from "@/lib/supabase";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(request: Request) {
  const form = await request.formData();
  const name = String(form.get("name") ?? "").trim();
  const email = String(form.get("email") ?? "").trim().toLowerCase();
  const password = String(form.get("password") ?? "");
  const supabase = await getSupabaseServerClient();

  if (!supabase) redirect("/signup?error=config");
  if (name.length < 2 || name.length > 60) redirect("/signup?error=name");
  if (!EMAIL_PATTERN.test(email) || email.length > 254) redirect("/signup?error=email");
  if (password.length < 8 || password.length > 72) redirect("/signup?error=password");

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { display_name: name },
      emailRedirectTo: getPasswordRecoveryRedirect() ?? undefined,
    },
  });
  if (error) {
    redirect(error.code === "weak_password" ? "/signup?error=password" : "/signup?error=failed");
  }

  // Email confirmation off: Supabase returns a session right away.
  if (data.session) redirect("/pending");
  redirect("/login?notice=confirm");
}
