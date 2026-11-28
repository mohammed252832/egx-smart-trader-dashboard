import Link from "next/link";
import { redirect } from "next/navigation";
import { AuthShell } from "@/app/auth-shell";
import { getCurrentUser } from "@/lib/auth";

export const instant = false;

const ERRORS: Record<string, string> = {
  name: "اكتب اسماً من حرفين على الأقل.",
  email: "اكتب بريداً إلكترونياً صحيحاً.",
  password: "كلمة المرور يجب أن تكون من 8 إلى 72 حرفاً وغير سهلة التخمين.",
  failed: "تعذّر إنشاء الحساب. تأكد من البيانات وحاول مرة أخرى.",
  config: "إعدادات التسجيل غير مكتملة على الخادم.",
};

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const user = await getCurrentUser();
  if (user) redirect(user.status === "approved" ? "/" : "/pending");

  const { error } = await searchParams;
  const message = error ? ERRORS[error] ?? null : null;

  return (
    <AuthShell title="إنشاء حساب" subtitle="بعد التسجيل يراجع المسؤول حسابك ثم يفتح لك الوصول.">
      {message && (
        <p className="mb-5 rounded-lg border border-down/30 bg-down-soft p-3 text-sm text-down" role="alert">
          {message}
        </p>
      )}
      <form action="/auth/signup" method="post" className="space-y-5">
        <label className="block text-sm font-semibold">
          الاسم
          <input name="name" type="text" autoComplete="name" required minLength={2} maxLength={60} className="field mt-2" />
        </label>
        <label className="block text-sm font-semibold">
          البريد الإلكتروني
          <input name="email" type="email" dir="ltr" autoComplete="email" required maxLength={254} className="field mt-2 text-left" />
        </label>
        <label className="block text-sm font-semibold">
          كلمة المرور
          <input
            name="password"
            type="password"
            dir="ltr"
            autoComplete="new-password"
            required
            minLength={8}
            maxLength={72}
            className="field mt-2 text-left"
          />
          <span className="mt-1 block text-xs font-normal text-muted">8 أحرف على الأقل.</span>
        </label>
        <button type="submit" className="btn-primary w-full">
          إنشاء الحساب
        </button>
      </form>
      <p className="mt-5 text-center text-sm text-muted">
        لديك حساب بالفعل؟{" "}
        <Link href="/login" className="font-semibold text-brand hover:underline">
          تسجيل الدخول
        </Link>
      </p>
    </AuthShell>
  );
}
