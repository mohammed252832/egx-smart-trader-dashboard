import Link from "next/link";
import { redirect } from "next/navigation";
import { AuthShell } from "@/app/auth-shell";
import { getCurrentUser } from "@/lib/auth";

export const instant = false;

const ERRORS: Record<string, string> = {
  invalid: "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
  unconfirmed: "لم يتم تأكيد البريد الإلكتروني بعد. افتح الرسالة التي وصلتك واضغط على رابط التأكيد.",
  link: "رابط الدخول غير صالح أو منتهي.",
  config: "إعدادات الدخول غير مكتملة على الخادم.",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; notice?: string }>;
}) {
  const user = await getCurrentUser();
  if (user) redirect(user.status === "approved" ? "/" : "/pending");

  const { error, notice } = await searchParams;
  const message = error ? ERRORS[error] ?? null : null;

  return (
    <AuthShell title="تسجيل الدخول" subtitle="ادخل إلى حسابك لمتابعة فرص البورصة المصرية.">
      {notice === "confirm" && (
        <p className="mb-5 rounded-lg border border-up/30 bg-up-soft p-3 text-sm leading-6 text-up" role="status">
          أنشأنا حسابك. أرسلنا رسالة تأكيد إلى بريدك؛ اضغط على الرابط فيها ثم سجّل الدخول. بعد ذلك ينتظر حسابك موافقة المسؤول.
        </p>
      )}
      {message && (
        <p className="mb-5 rounded-lg border border-down/30 bg-down-soft p-3 text-sm text-down" role="alert">
          {message}
        </p>
      )}
      <form action="/auth/login" method="post" className="space-y-5">
        <label className="block text-sm font-semibold">
          البريد الإلكتروني
          <input
            name="email"
            type="email"
            dir="ltr"
            autoComplete="email"
            required
            maxLength={254}
            className="field mt-2 text-left"
          />
        </label>
        <label className="block text-sm font-semibold">
          كلمة المرور
          <input
            name="password"
            type="password"
            dir="ltr"
            autoComplete="current-password"
            required
            minLength={8}
            maxLength={72}
            className="field mt-2 text-left"
          />
        </label>
        <button type="submit" className="btn-primary w-full">
          تسجيل الدخول
        </button>
      </form>
      <p className="mt-5 text-center text-sm text-muted">
        ليس لديك حساب؟{" "}
        <Link href="/signup" className="font-semibold text-brand hover:underline">
          إنشاء حساب جديد
        </Link>
      </p>
    </AuthShell>
  );
}
