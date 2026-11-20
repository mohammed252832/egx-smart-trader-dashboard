import { getDashboardData } from "@/lib/data";
import type { Recommendation } from "@/lib/types";

const money = (value: number) =>
  new Intl.NumberFormat("en-EG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);

const percent = (value: number) => `${money(value)}%`;

function signalStyle(signal: string) {
  if (signal.includes("قوي")) {
    return "bg-emerald-500/10 text-emerald-400";
  }
  if (signal.includes("شراء")) {
    return "bg-cyan-500/10 text-cyan-400";
  }
  return "bg-yellow-500/10 text-yellow-400";
}

function RecommendationRow({ row }: { row: Recommendation }) {
  return (
    <tr className="border-b border-white/5 align-top">
      <td className="p-4">
        <p className="font-bold">{row.symbol}</p>
        <p className="mt-1 text-xs text-gray-500">{row.name}</p>
      </td>
      <td className="p-4 text-gray-300">{money(row.entry_price)}</td>
      <td className="p-4 text-emerald-400">{money(row.target_price)}</td>
      <td className="p-4 text-red-400">{money(row.stop_loss)}</td>
      <td className="p-4 text-emerald-400">{percent(row.upside_pct)}</td>
      <td className="p-4 text-red-400">{percent(row.risk_pct)}</td>
      <td className="p-4 text-gray-300">{money(row.reward_risk)} : 1</td>
      <td className="p-4">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-16 overflow-hidden rounded-full bg-white/10">
            <span
              className="block h-full rounded-full bg-emerald-400"
              style={{ width: `${Math.min(100, row.score)}%` }}
            />
          </span>
          <span className="text-xs text-gray-400">{money(row.score)}</span>
        </div>
      </td>
      <td className="p-4">
        <span className={`rounded-lg px-3 py-2 text-xs ${signalStyle(row.signal)}`}>
          {row.signal}
        </span>
      </td>
    </tr>
  );
}

export default async function Page() {
  const { recommendations, stats, asOf, isDemo } = await getDashboardData();

  return (
    <main dir="rtl" className="min-h-screen bg-[#0a1120] text-white">
      <section className="mx-auto max-w-7xl px-6 py-10">
        <header className="mb-10 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-emerald-400">EGX SMART TRADER</p>
            <h1 className="mt-2 text-3xl font-black">محلل أسهم البورصة المصرية</h1>
            <p className="mt-2 text-sm text-gray-500">
              أفضل الفرص المتوقعة خلال 2–3 أيام · آخر تحديث: {asOf ?? "—"}
            </p>
          </div>
          <span
            className={`rounded-lg px-4 py-2 text-xs ${
              isDemo
                ? "bg-yellow-500/10 text-yellow-400"
                : "bg-emerald-500/10 text-emerald-400"
            }`}
          >
            {isDemo ? "بيانات تجريبية — أضف Supabase لعرض النتائج الحقيقية" : "متصل بـ Supabase"}
          </span>
        </header>

        <div className="mb-8 grid gap-5 sm:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-[#111c30] p-6">
            <p className="text-sm text-gray-400">الأسهم المفحصة</p>
            <h3 className="my-4 text-3xl font-black text-emerald-400">{stats.analyzed}</h3>
            <p className="text-xs text-gray-500">من كامل السوق في آخر تشغيل</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#111c30] p-6">
            <p className="text-sm text-gray-400">متوسط الصعود المتوقع</p>
            <h3 className="my-4 text-3xl font-black text-emerald-400">
              {percent(stats.avgUpside)}
            </h3>
            <p className="text-xs text-gray-500">لأفضل 10 فرص</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#111c30] p-6">
            <p className="text-sm text-gray-400">نسبة نجاح التوصيات</p>
            <h3 className="my-4 text-3xl font-black text-emerald-400">
              {stats.winRate === null ? "—" : percent(stats.winRate)}
            </h3>
            <p className="text-xs text-gray-500">بعد اكتمال فترة الاحتفاظ</p>
          </div>
        </div>

        <div className="mb-8 rounded-2xl border border-white/10 bg-[#111c30] p-6">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold">أفضل فرص التداول</h2>
              <p className="mt-1 text-sm text-gray-500">
                ترتيب الأسهم حسب قوة الفرصة المتوقعة
              </p>
            </div>
            <span className="rounded-lg bg-emerald-500/10 px-4 py-2 text-xs text-emerald-400">
              فترة الاحتفاظ: 2–3 أيام
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[1100px] text-right">
              <thead>
                <tr className="border-b border-white/10 text-sm text-gray-500">
                  <th className="p-4">السهم</th>
                  <th className="p-4">الدخول</th>
                  <th className="p-4">الهدف</th>
                  <th className="p-4">الوقف</th>
                  <th className="p-4">الصعود</th>
                  <th className="p-4">المخاطرة</th>
                  <th className="p-4">العائد/المخاطرة</th>
                  <th className="p-4">القوة</th>
                  <th className="p-4">الإشارة</th>
                </tr>
              </thead>
              <tbody>
                {recommendations.map((row) => (
                  <RecommendationRow key={row.id} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-[#111c30] p-6">
            <h3 className="mb-4 font-bold">محرك التحليل الذكي</h3>
            <p className="text-sm leading-7 text-gray-400">
              Pandas لتجهيز المؤشرات الفنية، وXGBoost لتقدير احتمال الصعود خلال
              3 جلسات، مع دمج أسعار من أكثر من مصدر قبل إصدار التوصية.
            </p>
            <p className="mt-5 text-sm text-yellow-400">● يعمل عبر GitHub Actions</p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#111c30] p-6">
            <h3 className="mb-4 font-bold">إدارة المخاطر</h3>
            <p className="text-sm leading-7 text-gray-400">
              سعر الدخول والهدف ووقف الخسارة تُحسب من متوسط المدى الحقيقي ATR،
              وتُخزّن النتائج في Supabase لتقييم دقتها تلقائياً.
            </p>
            <p className="mt-5 text-sm text-yellow-400">● تقييم بعد 3 جلسات</p>
          </div>
        </div>

        <footer className="mt-12 border-t border-white/10 py-6 text-center text-xs text-gray-600">
          EGX SMART TRADER © 2026 — أداة تحليل الأسهم المصرية
        </footer>
      </section>
    </main>
  );
}
