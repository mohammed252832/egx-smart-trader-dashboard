import Link from "next/link";
import { redirect } from "next/navigation";
import { AuthShell } from "@/app/auth-shell";
import { getCurrentUser } from "@/lib/auth";

export const instant = false;

export default async function ForgotPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ sent?: string; error?: string }>;
}) {
  if (await getCurrentUser()) redirect("/");
  const { sent, error } = await searchParams;

  return (
    <AuthShell>
      {sent === "1" && (
        <p className="mb-5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300" role="status">
          إذا كان البريد مسجلاً، فسيصلك رابط لتعيين كلمة مرور جديدة.
        </p>
      )}
      {error === "config" && (
        <p className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300" role="alert">
          إعدادات الحساب أو رابط الموقع غير مكتملة على الخادم.
        </p>
      )}
      {error === "send" && (
        <p className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300" role="alert">
          تعذّر إرسال رابط الاستعادة الآن. حاول مرة أخرى لاحقاً.
        </p>
      )}
      <form action="/auth/recover" method="post" className="space-y-5">
        <label className="block text-sm text-gray-300">
          البريد الإلكتروني للحساب
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
        <button type="submit" className="w-full rounded-xl bg-emerald-500 px-5 py-3 font-bold text-[#07120d] transition hover:bg-emerald-400">
          إرسال رابط تعيين كلمة المرور
        </button>
      </form>
      <Link href="/login" className="mt-6 block text-center text-sm text-emerald-400 hover:text-emerald-300">العودة لتسجيل الدخول</Link>
    </AuthShell>
  );
}
