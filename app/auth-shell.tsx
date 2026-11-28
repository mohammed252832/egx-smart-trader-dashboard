import type { ReactNode } from "react";
import { BrandMark } from "./brand-mark";

export function AuthShell({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <main dir="rtl" className="flex min-h-screen items-center justify-center bg-page px-5 py-12 text-ink">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <BrandMark className="h-14 w-14" />
          <p className="mt-4 text-sm font-semibold text-brand">EGX Smart Trader</p>
          <h1 className="mt-1 text-3xl font-bold">{title}</h1>
          {subtitle && <p className="mt-3 text-sm leading-6 text-muted">{subtitle}</p>}
        </div>
        <section className="card p-6 sm:p-8">{children}</section>
        <p className="mt-6 text-center text-xs leading-6 text-muted">
          الأسعار متأخرة أو آخر إغلاق يومي وليست بيانات لحظية. أداة بحث وتحليل، وليست نصيحة استثمارية.
        </p>
      </div>
    </main>
  );
}
