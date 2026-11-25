import { AutoRefresh } from "@/app/auto-refresh";
import { getDashboardData } from "@/lib/data";
import { formatCairoDateTime } from "@/lib/market-time";
import type { LiveQuote, Recommendation } from "@/lib/types";

export const instant = false;

const money = (value: number) =>
  new Intl.NumberFormat("en-EG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);

const percent = (value: number) => `${money(value)}%`;

function quoteSourceLabel(source: string | null | undefined) {
  if (source === "egid_delayed") return "EGID الرسمي";
  if (source === "tradingview_delayed") return "TradingView (غير رسمي)";
  if (source === "yahoo_delayed") return "Yahoo Finance";
  return "مصدر أسعار متأخر";
}

function quoteStatusLabel(source: string | null | undefined, delayMinutes: number | null) {
  if (source === "yahoo_delayed") return "Yahoo Finance · آخر إغلاق يومي";
  return `${quoteSourceLabel(source)} · متأخر ${delayMinutes ?? "—"} د`;
}

function signalStyle(signal: string) {
  if (signal.includes("قوي")) {
    return "bg-emerald-500/10 text-emerald-400";
  }
  if (signal.includes("شراء")) {
    return "bg-cyan-500/10 text-cyan-400";
  }
  return "bg-yellow-500/10 text-yellow-400";
}

function RecommendationRow({ row, quote }: { row: Recommendation; quote?: LiveQuote }) {
  return (
    <tr className="border-b border-white/5 align-top">
      <td className="p-4">
        <p className="font-bold">{row.symbol}</p>
        <p className="mt-1 text-xs text-gray-500">{row.name}</p>
      </td>
      <td className="p-4 text-gray-300">
        <p>{money(row.entry_price)}</p>
        {quote && (
          <p
            className={`mt-1 text-xs ${quote.change_pct !== null && quote.change_pct < 0 ? "text-red-400" : "text-emerald-400"}`}
            title={`${quoteSourceLabel(quote.source)} · وقت الجلب: ${formatCairoDateTime(quote.fetched_at)}`}
          >
            آخر سعر معروف {money(quote.price)}
            {quote.change_pct === null ? "" : ` (${quote.change_pct >= 0 ? "+" : ""}${percent(quote.change_pct)})`}
          </p>
        )}
      </td>
      <td className="p-4 text-emerald-400">{money(row.target_price)}</td>
      <td className="p-4 text-red-400">{money(row.stop_loss)}</td>
      <td className="p-4 text-emerald-400">{percent(row.upside_pct)}</td>
      <td className="p-4 text-red-400">{percent(row.risk_pct)}</td>
      <td className="p-4 text-gray-300">{money(row.reward_risk)} : 1</td>
      <td className="p-4 text-cyan-400">
        {row.probability === null ? "—" : percent(row.probability * 100)}
      </td>
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
  const {
    recommendations,
    stats,
    lastRunAt,
    marketDate,
    expectedSession,
    isStale,
    isEmpty,
    liveQuotes,
    marketRefresh,
  } = await getDashboardData();
  const quoteBySymbol = new Map(liveQuotes.map((quote) => [quote.symbol, quote]));
  const delayMinutes = marketRefresh?.delay_seconds === null || marketRefresh?.delay_seconds === undefined
    ? null
    : Math.round(marketRefresh.delay_seconds / 60);
  const refreshFailed = Boolean(
    marketRefresh?.last_error
    && (!marketRefresh.last_success_at
      || Date.parse(marketRefresh.updated_at) > Date.parse(marketRefresh.last_success_at)),
  );

  return (
    <main dir="rtl" className="min-h-screen bg-[#0a1120] text-white">
      <AutoRefresh />
      <section className="mx-auto max-w-7xl px-6 py-10">
        <header className="mb-10 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-emerald-400">EGX SMART TRADER</p>
            <h1 className="mt-2 text-3xl font-black">محلل أسهم البورصة المصرية</h1>
            <p className="mt-2 text-sm text-gray-500">
              أفضل الفرص المتوقعة خلال 2–3 أيام · تاريخ السوق: {marketDate ?? "—"}
            </p>
            <p className="mt-1 text-xs text-gray-600">
              آخر تشغيل ناجح: {formatCairoDateTime(lastRunAt)} · الجلسة المتوقعة: {expectedSession ?? "—"}
            </p>
          </div>
          <span
            className={`rounded-lg px-4 py-2 text-xs ${
              isEmpty
                ? "bg-yellow-500/10 text-yellow-400"
                : "bg-emerald-500/10 text-emerald-400"
            }`}
          >
            {marketRefresh?.last_success_at
              ? quoteStatusLabel(marketRefresh.source, delayMinutes)
              : isEmpty
                ? "لا توجد نتائج منشورة بعد"
                : "تحديث الأسعار غير مفعّل"}
          </span>
        </header>

        {isStale && (
          <div className="mb-8 rounded-2xl border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm text-yellow-300">
            تنبيه: البيانات المعروضة أقدم من آخر جلسة متوقعة ({expectedSession ?? "—"}). قد يكون تشغيل التحليل متأخراً أو يوم عطلة؛ تحقق من تبويب Actions.
          </div>
        )}

        {marketRefresh?.last_error && (
          <div
            className={`mb-8 rounded-2xl border p-4 text-sm ${
              refreshFailed
                ? "border-red-500/30 bg-red-500/10 text-red-300"
                : "border-yellow-500/30 bg-yellow-500/10 text-yellow-300"
            }`}
          >
            {refreshFailed
              ? "تعذّر آخر تحديث للأسهم. نعرض آخر بيانات ناجحة، والخطأ: "
              : "اكتمل آخر تحديث جزئياً أو بعد الرجوع لمصدر احتياطي. نعرض آخر بيانات ناجحة، والتفاصيل: "}
            {marketRefresh.last_error}
          </div>
        )}

        <div className="mb-8 grid gap-3 rounded-2xl border border-white/10 bg-[#111c30] p-5 text-sm sm:grid-cols-3">
          <div>
            <p className="text-gray-500">مصدر الأسعار</p>
            <p className={`mt-1 font-bold ${marketRefresh?.last_success_at ? "text-emerald-400" : "text-yellow-400"}`}>
              {marketRefresh?.last_success_at
                ? quoteStatusLabel(marketRefresh.source, delayMinutes)
                : "تحديث الأسعار غير مفعّل بعد"}
            </p>
          </div>
          <div>
            <p className="text-gray-500">آخر تحديث ناجح</p>
            <p className="mt-1">{formatCairoDateTime(marketRefresh?.last_success_at ?? null)}</p>
          </div>
          <div>
            <p className="text-gray-500">وقت بيانات المصدر</p>
            <p className="mt-1">{formatCairoDateTime(marketRefresh?.source_timestamp ?? null)}</p>
          </div>
        </div>

        <div className="mb-8 grid gap-5 sm:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-[#111c30] p-6">
            <p className="text-sm text-gray-400">الأسهم المفحصة</p>
            <h3 className="my-4 text-3xl font-black text-emerald-400">
              {stats.analyzed === null ? "—" : stats.analyzed}
            </h3>
            <p className="text-xs text-gray-500">من قائمة السوق بعد فلاتر الجودة والسيولة</p>
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
                  <th className="p-4">الاحتمال</th>
                  <th
                    className="p-4"
                    title="درجة مركّبة من احتمال النموذج ونسبة العائد إلى المخاطرة والزخم والحجم. ليست احتمالاً؛ التفاصيل في MODEL_REPORT.md."
                  >
                    القوة ⓘ
                  </th>
                  <th className="p-4">الإشارة</th>
                </tr>
              </thead>
              <tbody>
                {isEmpty ? (
                  <tr>
                    <td colSpan={10} className="p-10 text-center text-sm text-gray-500">
                      لا توجد توصيات منشورة بعد. شغّل محرك التحليل أو راجع إعدادات Supabase.
                    </td>
                  </tr>
                ) : (
                  recommendations.map((row) => (
                    <RecommendationRow key={row.id} row={row} quote={quoteBySymbol.get(row.symbol)} />
                  ))
                )}
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

        <footer className="mt-12 border-t border-white/10 py-6 text-center text-xs leading-6 text-gray-600">
          EGX SMART TRADER © 2026 — أداة بحث وتحليل، وليست نصيحة استثمارية. الأسعار متأخرة أو آخر إغلاق يومي حسب المصدر، وليست بيانات لحظية.
        </footer>
      </section>
    </main>
  );
}
