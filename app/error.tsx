"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main dir="rtl" className="flex min-h-screen items-center justify-center bg-page px-5 text-ink">
      <div className="card w-full max-w-lg p-8 text-center">
        <p className="text-sm font-semibold text-down">تعذّر تحميل البيانات</p>
        <h1 className="mt-3 text-2xl font-bold">الخدمة غير متاحة مؤقتاً</h1>
        <p className="mt-4 text-sm leading-7 text-muted">
          لم نتمكن من قراءة بيانات السوق أو التحقق من الاتصال. لم نستبدل الخطأ ببيانات فارغة أو أرقام تقديرية.
        </p>
        <button type="button" onClick={reset} className="btn-primary mt-6">
          إعادة المحاولة
        </button>
      </div>
    </main>
  );
}
