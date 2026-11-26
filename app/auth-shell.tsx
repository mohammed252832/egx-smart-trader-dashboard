import type { ReactNode } from "react";

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main dir="rtl" className="flex min-h-screen items-center justify-center bg-[#0a1120] px-5 py-12 text-white">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <p className="text-sm font-bold text-emerald-400">EGX SMART TRADER</p>
          <h1 className="mt-3 text-3xl font-black">بوابة تحليل البورصة المصرية</h1>
          <p className="mt-3 text-sm leading-6 text-gray-500">دخول خاص بالحسابات المعتمدة. الأسعار متأخرة أو آخر إغلاق يومي وليست بيانات لحظية.</p>
        </div>
        <section className="rounded-3xl border border-white/10 bg-[#111c30] p-6 shadow-2xl shadow-black/30 sm:p-8">
          {children}
        </section>
        <p className="mt-6 text-center text-xs leading-6 text-gray-600">أداة بحث وتحليل، وليست نصيحة استثمارية.</p>
      </div>
    </main>
  );
}
