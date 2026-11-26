import Link from "next/link";
import { redirect } from "next/navigation";
import { AuthShell } from "@/app/auth-shell";
import { getCurrentUser } from "@/lib/auth";

export const instant = false;

export default async function UpdatePasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login?error=link");
  const { error } = await searchParams;

  return (
    <AuthShell>
      {error === "weak" && <p className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">استخدم كلمة مرور من 8 إلى 72 حرفاً.</p>}
      {error === "failed" && <p className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">تعذّر تحديث كلمة المرور. اطلب الرابط مرة أخرى.</p>}
      <form action="/auth/password" method="post" className="space-y-5">
        <p className="text-sm leading-6 text-gray-400">أنشئ كلمة مرور جديدة للحساب <strong dir="ltr" className="text-white">{user.email}</strong>.</p>
        <label className="block text-sm text-gray-300">
          كلمة المرور الجديدة
          <input
            name="password"
            type="password"
            dir="ltr"
            autoComplete="new-password"
            required
            minLength={8}
            maxLength={72}
            className="mt-2 w-full rounded-xl border border-white/10 bg-[#0a1120] px-4 py-3 text-left text-white outline-none focus:border-emerald-400"
          />
        </label>
        <button type="submit" className="w-full rounded-xl bg-emerald-500 px-5 py-3 font-bold text-[#07120d] transition hover:bg-emerald-400">
          حفظ كلمة المرور
        </button>
      </form>
      <Link href="/login" className="mt-6 block text-center text-sm text-emerald-400 hover:text-emerald-300">العودة لتسجيل الدخول</Link>
    </AuthShell>
  );
}
