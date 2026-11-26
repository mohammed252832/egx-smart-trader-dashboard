import { redirect } from "next/navigation";
import { getSupabaseServerClient } from "@/lib/supabase";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const tokenHash = url.searchParams.get("token_hash") ?? "";
  const rawType = url.searchParams.get("type") ?? "";
  const supabase = await getSupabaseServerClient();
  if (!supabase || !tokenHash || tokenHash.length > 500) redirect("/login?error=link");

  switch (rawType) {
    case "recovery":
    case "invite": {
      const { error } = await supabase.auth.verifyOtp({ type: rawType, token_hash: tokenHash });
      if (error) redirect("/login?error=link");
      redirect("/auth/update-password");
    }
    case "email":
    case "signup":
    case "magiclink": {
      const { error } = await supabase.auth.verifyOtp({ type: rawType, token_hash: tokenHash });
      if (error) redirect("/login?error=link");
      redirect("/");
    }
    default:
      redirect("/login?error=link");
  }
}
