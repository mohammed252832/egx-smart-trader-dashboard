import { redirect } from "next/navigation";
import { AuthShell } from "@/app/auth-shell";
import { getCurrentUser } from "@/lib/auth";

export const instant = false;

export default async function PendingPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (user.status === "approved") redirect("/");

  const blocked = user.status === "blocked";

  return (
    <AuthShell
      title={blocked ? "الحساب موقوف" : "حسابك قيد المراجعة"}
      subtitle={user.email}
    >
      <p className="text-center text-sm leading-7 text-muted">
        {blocked
          ? "تم إيقاف هذا الحساب. تواصل مع مسؤول الموقع إذا كنت تعتقد أن ذلك خطأ."
          : "سجّلنا حسابك بنجاح. سيظهر لك السوق والتوصيات بمجرد موافقة المسؤول على الحساب. حدّث الصفحة لاحقاً للتحقق."}
      </p>
      <div className="mt-6 flex flex-col gap-3">
        {!blocked && (
          <a href="/pending" className="btn-quiet">
            تحديث الحالة
          </a>
        )}
        <form action="/auth/logout" method="post">
          <button type="submit" className="btn-quiet w-full">
            تسجيل الخروج
          </button>
        </form>
      </div>
    </AuthShell>
  );
}
