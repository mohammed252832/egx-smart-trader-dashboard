import Link from "next/link";
import { redirect } from "next/navigation";
import { AuthShell } from "@/app/auth-shell";
import { getCurrentUser } from "@/lib/auth";

export const instant = false;

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; password?: string }>;
}) {
  if (await getCurrentUser()) redirect("/");

  const { error, password } = await searchParams;
  const message = password === "updated"
    ? "تم تحديث كلمة المرور. سجّل الدخول الآن."
    : error === "link"
      ? "رابط الدخول غير صالح أو منتهي. اطلب رابطاً جديداً."
      : error === "invalid"
        ? "البريد الإلكتروني أو كلمة المرور غير صحيحة."
        : error === "config"
          ? "إعدادات Supabase غير مكتملة على الخادم."
          : null;

  return (
    <AuthShell>
      {message && (
        <p className={`mb-5 rounded-xl border p-3 text-sm ${password === "updated" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-red-500/30 bg-red-500/10 text-red-300"}`} role="status">
          {message}
        </p>
      )}
      <form action="/auth/login" method="post" className="space-y-5">
        <label className="block text-sm text-gray-300">
          البريد الإلكتروني
          <input
            name="email"
            type="email"
            dir="ltr"
            autoComplete="email"
            required
            className="mt-2 w-full rounded-xl border border-white/10 bg-[#0a1120] px-4 py-3 text-left text-white outline-none focus:border-emerald-400"
            placeholder="name@wm.com"
          />
        </label>
        <label className="block text-sm text-gray-300">
          كلمة المرور
          <input
            name="password"
            type="password"
            dir="ltr"
            autoComplete="current-password"
            required
            minLength={8}
            maxLength={72}
            className="mt-2 w-full rounded-xl border border-white/10 bg-[#0a1120] px-4 py-3 text-left text-white outline-none focus:border-emerald-400"
          />
        </label>
        <button type="submit" className="w-full rounded-xl bg-emerald-500 px-5 py-3 font-bold text-[#07120d] transition hover:bg-emerald-400">
          تسجيل الدخول
        </button>
      </form>
      <div className="mt-5 flex items-center justify-between gap-3 text-sm">
        <Link href="/forgot-password" className="text-emerald-400 hover:text-emerald-300">نسيت كلمة المرور</Link>
        <span className="text-xs text-gray-500">أول دخول: أنشئ كلمة مرور من الرابط المرسل لبريدك</span>
      </div>
    </AuthShell>
  );
}
