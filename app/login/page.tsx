import { redirect } from "next/navigation";
import { AuthShell } from "@/app/auth-shell";
import { getCurrentUser } from "@/lib/auth";

export const instant = false;

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  if (await getCurrentUser()) redirect("/");

  const { error } = await searchParams;
  const message = error === "invalid"
    ? "كلمة المرور غير صحيحة."
    : error === "link"
      ? "رابط الدخول غير صالح أو منتهي."
      : error === "config"
        ? "إعدادات الدخول غير مكتملة على الخادم."
        : null;

  return (
    <AuthShell>
      {message && (
        <p className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300" role="alert">
          {message}
        </p>
      )}
      <form action="/auth/login" method="post" className="space-y-5">
        <label className="block text-sm text-gray-300">
          كلمة المرور المشتركة
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
      <p className="mt-5 text-center text-xs leading-6 text-gray-500">
        الدخول متاح لمن يملك كلمة المرور. لا تشاركها إلا مع من تريد منحه الوصول.
      </p>
    </AuthShell>
  );
}
