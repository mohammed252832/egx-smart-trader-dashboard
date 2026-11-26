"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main dir="rtl" className="flex min-h-screen items-center justify-center bg-[#0a1120] px-5 text-white">
      <div className="w-full max-w-lg rounded-2xl border border-red-500/20 bg-[#111c30] p-8 text-center">
        <p className="text-sm text-red-300">تعذّر تحميل البيانات</p>
        <h1 className="mt-3 text-2xl font-black">الخدمة غير متاحة مؤقتاً</h1>
        <p className="mt-4 text-sm leading-7 text-gray-400">
          لم نتمكن من قراءة بيانات السوق أو التحقق من الاتصال. لم نستبدل الخطأ ببيانات فارغة أو أرقام تقديرية.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-6 rounded-xl bg-emerald-500 px-6 py-3 font-bold text-[#07120d] transition hover:bg-emerald-400"
        >
          إعادة المحاولة
        </button>
      </div>
    </main>
  );
}
