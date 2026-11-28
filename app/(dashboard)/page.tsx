import Link from "next/link";
import { AutoRefresh } from "@/app/auto-refresh";
import { getDashboardData } from "@/lib/data";
import { getInsights } from "@/lib/insights";
import { formatCairoDateTime } from "@/lib/market-time";
import type { LiquidityLeader, LiquidRisingPick, LiveQuote, MarketState, Recommendation } from "@/lib/types";
import { formatEgp, LiquidityBars, MarketStateChart } from "./insight-charts";

export const instant = false;

const money = (value: number) =>
  new Intl.NumberFormat("en-EG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);

const percent = (value: number) => `${money(value)}%`;
const integer = new Intl.NumberFormat("en-EG", { maximumFractionDigits: 0 });

function quoteSourceLabel(source: string | null | undefined) {
  if (source === "egid_delayed") return "EGID الرسمي";
  if (source === "egid_public_delayed") return "EGID الرسمي (عام)";
  if (source === "tradingview_delayed") return "TradingView (غير رسمي)";
  if (source === "yahoo_delayed") return "Yahoo Finance";
  if (source === "mixed") return "مصادر أسعار مجمعة";
  return "مصدر أسعار متأخر";
}

function quoteStatusLabel(source: string | null | undefined, delayMinutes: number | null) {
  if (source === "yahoo_delayed") return "Yahoo Finance · آخر إغلاق يومي";
  return `${quoteSourceLabel(source)} · متأخر ${delayMinutes ?? "—"} د`;
}

function signalStyle(signal: string) {
  if (signal.includes("قوي")) return "bg-up-soft text-up";
  if (signal.includes("شراء")) return "bg-brand-soft text-brand";
  return "bg-warn-soft text-warn";
}

function stateStyle(state: MarketState | null) {
  if (state === "صاعد") return "bg-up-soft text-up";
  if (state === "هابط") return "bg-down-soft text-down";
  return "bg-warn-soft text-warn";
}

function Change({ value }: { value: number | null }) {
  if (value === null) return <span className="text-muted">—</span>;
  const style = value > 0 ? "text-up" : value < 0 ? "text-down" : "text-muted";
  return <span className={style} dir="ltr">{value > 0 ? "+" : ""}{money(value)}%</span>;
}

function SectionError({ name }: { name: string }) {
  return (
    <p className="p-8 text-center text-sm text-down">
      تعذّر تحميل قسم «{name}». لم نعرض أرقاماً بديلة؛ أعد تحميل الصفحة بعد قليل.
    </p>
  );
}

function SectionHead({ title, note, badge }: { title: string; note: string; badge?: string }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line p-5 sm:p-6">
      <div>
        <h2 className="text-lg font-bold">{title}</h2>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">{note}</p>
      </div>
      {badge && <span className="rounded-lg bg-brand-soft px-3 py-1.5 text-xs font-semibold text-brand">{badge}</span>}
    </div>
  );
}

function PickRows({ rows, quoteBySymbol }: { rows: Array<Recommendation | LiquidRisingPick>; quoteBySymbol: Map<string, LiveQuote> }) {
  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[960px] text-right">
          <thead>
            <tr className="border-b border-line text-sm text-muted">
              <th className="p-4 font-semibold">السهم</th>
              <th className="p-4 font-semibold">الدخول</th>
              <th className="p-4 font-semibold">الهدف</th>
              <th className="p-4 font-semibold">الوقف</th>
              <th className="p-4 font-semibold">الصعود</th>
              <th className="p-4 font-semibold">المخاطرة</th>
              <th className="p-4 font-semibold">العائد/المخاطرة</th>
              <th className="p-4 font-semibold">الاحتمال</th>
              <th
                className="p-4 font-semibold"
                title="درجة مركّبة من احتمال النموذج ونسبة العائد إلى المخاطرة والزخم والحجم. ليست احتمالاً."
              >
                القوة ⓘ
              </th>
              <th className="p-4 font-semibold">الإشارة</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const quote = quoteBySymbol.get(row.symbol);
              return (
                <tr key={row.id} className="border-b border-line/70 align-top last:border-0">
                  <td className="p-4">
                    <Link href={`/stocks/${row.symbol}`} className="font-bold text-brand hover:underline">{row.symbol}</Link>
                    <p className="mt-1 max-w-48 truncate text-xs text-muted">{row.name}</p>
                  </td>
                  <td className="p-4">
                    <p>{money(row.entry_price)}</p>
                    {quote && (
                      <p
                        className={`mt-1 text-xs ${quote.change_pct !== null && quote.change_pct < 0 ? "text-down" : "text-up"}`}
                        title={`${quoteSourceLabel(quote.source)} · وقت الجلب: ${formatCairoDateTime(quote.fetched_at)}`}
                      >
                        آخر سعر معروف {money(quote.price)}
                        {quote.change_pct === null ? "" : ` (${quote.change_pct >= 0 ? "+" : ""}${percent(quote.change_pct)})`}
                      </p>
                    )}
                  </td>
                  <td className="p-4 text-up">{money(row.target_price)}</td>
                  <td className="p-4 text-down">{money(row.stop_loss)}</td>
                  <td className="p-4 text-up">{percent(row.upside_pct)}</td>
                  <td className="p-4 text-down">{percent(row.risk_pct)}</td>
                  <td className="p-4">{money(row.reward_risk)} : 1</td>
                  <td className="p-4">{row.probability === null ? "—" : percent(row.probability * 100)}</td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-line">
                        <span className="block h-full rounded-full bg-brand" style={{ width: `${Math.min(100, row.score)}%` }} />
                      </span>
                      <span className="text-xs text-muted">{money(row.score)}</span>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${signalStyle(row.signal)}`}>{row.signal}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <ul className="grid gap-3 p-4 md:hidden">
        {rows.map((row) => (
          <li key={row.id} className="rounded-xl border border-line p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <Link href={`/stocks/${row.symbol}`} className="font-bold text-brand">{row.symbol}</Link>
                <p className="mt-1 text-xs text-muted">{row.name}</p>
              </div>
              <span className={`rounded-lg px-3 py-1 text-xs font-semibold ${signalStyle(row.signal)}`}>{row.signal}</span>
            </div>
            <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
              <div><dt className="text-xs text-muted">الدخول</dt><dd className="mt-1 font-semibold">{money(row.entry_price)}</dd></div>
              <div><dt className="text-xs text-muted">الهدف</dt><dd className="mt-1 font-semibold text-up">{money(row.target_price)}</dd></div>
              <div><dt className="text-xs text-muted">الوقف</dt><dd className="mt-1 font-semibold text-down">{money(row.stop_loss)}</dd></div>
              <div><dt className="text-xs text-muted">الصعود</dt><dd className="mt-1 font-semibold text-up">{percent(row.upside_pct)}</dd></div>
              <div><dt className="text-xs text-muted">الاحتمال</dt><dd className="mt-1 font-semibold">{row.probability === null ? "—" : percent(row.probability * 100)}</dd></div>
              <div><dt className="text-xs text-muted">القوة</dt><dd className="mt-1 font-semibold">{money(row.score)}</dd></div>
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}

function LeadersTable({ rows }: { rows: LiquidityLeader[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-right text-sm">
        <thead>
          <tr className="border-b border-line text-xs text-muted">
            <th className="p-3 font-semibold">#</th>
            <th className="p-3 font-semibold">السهم</th>
            <th className="p-3 font-semibold">آخر سعر</th>
            <th className="p-3 font-semibold">التغير</th>
            <th className="p-3 font-semibold">قيمة التداول</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.symbol} className="border-b border-line/70 last:border-0">
              <td className="p-3 text-muted">{row.liquidity_rank}</td>
              <td className="p-3">
                <Link href={`/stocks/${row.symbol}`} className="font-bold text-brand hover:underline">{row.symbol}</Link>
                <p className="mt-0.5 max-w-52 truncate text-xs text-muted">{row.name}</p>
              </td>
              <td className="p-3 font-semibold" dir="ltr">{money(row.close)}</td>
              <td className="p-3"><Change value={row.change_pct} /></td>
              <td className="p-3">{formatEgp(row.value_egp)} <span className="text-xs text-muted">جنيه</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function Page() {
  const [dashboard, insights] = await Promise.all([getDashboardData(), getInsights()]);
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
  } = dashboard;
  const quoteBySymbol = new Map(liveQuotes.map((quote) => [quote.symbol, quote]));
  const delayMinutes = marketRefresh?.delay_seconds === null || marketRefresh?.delay_seconds === undefined
    ? null
    : Math.round(marketRefresh.delay_seconds / 60);
  const refreshFailed = Boolean(
    marketRefresh?.last_error
    && (!marketRefresh.last_success_at
      || Date.parse(marketRefresh.updated_at) > Date.parse(marketRefresh.last_success_at)),
  );

  const latestState = insights.marketState.at(-1) ?? null;
  const latestLiquidity = insights.liquidityDays.at(-1) ?? null;

  return (
    <main dir="rtl" className="min-h-screen">
      <AutoRefresh />
      <section className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">محلل أسهم البورصة المصرية</h1>
            <p className="mt-2 text-sm text-muted">
              أفضل الفرص المتوقعة خلال 3 جلسات · تاريخ السوق: {marketDate ?? "—"}
            </p>
            <p className="mt-1 text-xs text-muted">
              آخر تشغيل ناجح: {formatCairoDateTime(lastRunAt)} · الجلسة المتوقعة: {expectedSession ?? "—"}
            </p>
          </div>
          <span
            className={`rounded-lg px-4 py-2 text-xs font-semibold ${isEmpty ? "bg-warn-soft text-warn" : "bg-brand-soft text-brand"}`}
          >
            {marketRefresh?.last_success_at
              ? quoteStatusLabel(marketRefresh.source, delayMinutes)
              : isEmpty
                ? "لا توجد نتائج منشورة بعد"
                : "تحديث الأسعار غير مفعّل"}
          </span>
        </header>

        {isStale && (
          <div className="mb-6 rounded-xl border border-warn/30 bg-warn-soft p-4 text-sm leading-7 text-warn">
            تنبيه: البيانات المعروضة أقدم من آخر جلسة متوقعة ({expectedSession ?? "—"}). قد يكون تشغيل التحليل متأخراً أو يوم عطلة؛ تحقق من تبويب Actions.
          </div>
        )}

        {marketRefresh?.last_error && (
          <div
            className={`mb-6 rounded-xl border p-4 text-sm leading-7 ${
              refreshFailed ? "border-down/30 bg-down-soft text-down" : "border-warn/30 bg-warn-soft text-warn"
            }`}
          >
            {refreshFailed
              ? "تعذّر آخر تحديث للأسهم. نعرض آخر بيانات ناجحة، والخطأ: "
              : "اكتمل آخر تحديث جزئياً أو بعد الرجوع لمصدر احتياطي. نعرض آخر بيانات ناجحة، والتفاصيل: "}
            {marketRefresh.last_error}
          </div>
        )}

        <div className="card mb-6 grid gap-4 p-5 text-sm sm:grid-cols-3">
          <div>
            <p className="text-muted">مصدر السعر</p>
            <p className={`mt-1 font-semibold ${marketRefresh?.last_success_at ? "text-brand" : "text-warn"}`}>
              {marketRefresh?.last_success_at
                ? quoteStatusLabel(marketRefresh.source, delayMinutes)
                : "تحديث الأسعار غير مفعّل بعد"}
            </p>
            <a
              href="https://www.egidegypt.com/index.html"
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-block text-xs text-brand underline-offset-4 hover:underline"
            >
              الموقع الرسمي للبورصة المصرية EGID
            </a>
          </div>
          <div>
            <p className="text-muted">آخر تحديث ناجح</p>
            <p className="mt-1 font-semibold">{formatCairoDateTime(marketRefresh?.last_success_at ?? null)}</p>
          </div>
          <div>
            <p className="text-muted">وقت بيانات المصدر</p>
            <p className="mt-1 font-semibold">{formatCairoDateTime(marketRefresh?.source_timestamp ?? null)}</p>
          </div>
        </div>

        <section className="card mb-6 overflow-hidden" aria-labelledby="market-state-title">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line p-5 sm:p-6">
            <div>
              <h2 id="market-state-title" className="text-lg font-bold">حالة السوق: صاعد أم هابط؟</h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
                مؤشر يُحسب من أعلى 100 سهم سيولة بوزن متساوٍ، ومعه متوسطه لـ 20 جلسة. يُعد الاتجاه صاعداً عندما يعلو المؤشر ومتوسط 5 جلسات فوق متوسط 20 جلسة، وهابطاً عندما يهبطان تحته.
              </p>
            </div>
            {latestState && (
              <div className="text-left" dir="rtl">
                <span className={`inline-block rounded-lg px-4 py-2 text-lg font-bold ${stateStyle(latestState.market_state)}`}>
                  {latestState.market_state ?? "غير محدد"}
                </span>
                <p className="mt-2 text-xs text-muted">{latestState.trade_date}</p>
              </div>
            )}
          </div>
          {insights.failed.includes("market_state") ? (
            <SectionError name="حالة السوق" />
          ) : (
            <div className="p-4 sm:p-6">
              {latestState && (
                <dl className="mb-5 grid gap-3 text-sm sm:grid-cols-3">
                  <div className="rounded-lg bg-up-soft p-3">
                    <dt className="text-xs text-up">أسهم صاعدة</dt>
                    <dd className="mt-1 text-xl font-bold text-up">{latestState.advancers}</dd>
                  </div>
                  <div className="rounded-lg bg-down-soft p-3">
                    <dt className="text-xs text-down">أسهم هابطة</dt>
                    <dd className="mt-1 text-xl font-bold text-down">{latestState.decliners}</dd>
                  </div>
                  <div className="rounded-lg bg-brand-soft p-3">
                    <dt className="text-xs text-brand">تغير المؤشر في آخر جلسة</dt>
                    <dd className="mt-1 text-xl font-bold" dir="ltr">{latestState.change_pct > 0 ? "+" : ""}{money(latestState.change_pct)}%</dd>
                  </div>
                </dl>
              )}
              <MarketStateChart points={insights.marketState} />
              <p className="mt-3 flex flex-wrap gap-5 text-xs text-muted">
                <span className="flex items-center gap-2"><i className="h-0.5 w-6 bg-brand" /> المؤشر</span>
                <span className="flex items-center gap-2"><i className="h-0.5 w-6 border-t-2 border-dashed border-[#b7791f]" /> متوسط 20 جلسة</span>
              </p>
              {latestState && latestState.symbols < 60 && (
                <p className="mt-3 rounded-lg bg-warn-soft p-3 text-xs leading-6 text-warn">
                  آخر قراءة مبنية على {latestState.symbols} سهماً فقط من أصل 100، فقد تتغير بعد اكتمال البيانات.
                </p>
              )}
            </div>
          )}
        </section>

        <div className="mb-6 grid gap-5 sm:grid-cols-3">
          <div className="card p-6">
            <p className="text-sm text-muted">الأسهم المفحصة</p>
            <h3 className="my-3 text-3xl font-bold text-brand">{stats.analyzed === null ? "—" : stats.analyzed}</h3>
            <p className="text-xs text-muted">من قائمة السوق بعد فلاتر الجودة والسيولة</p>
          </div>
          <div className="card p-6">
            <p className="text-sm text-muted">متوسط الصعود المتوقع</p>
            <h3 className="my-3 text-3xl font-bold text-brand">{percent(stats.avgUpside)}</h3>
            <p className="text-xs text-muted">لأفضل 10 فرص</p>
          </div>
          <div className="card p-6">
            <p className="text-sm text-muted">نسبة نجاح التوصيات</p>
            <h3 className="my-3 text-3xl font-bold text-brand">{stats.winRate === null ? "—" : percent(stats.winRate)}</h3>
            <p className="text-xs text-muted">بعد اكتمال فترة الاحتفاظ</p>
          </div>
        </div>

        <section className="card mb-6 overflow-hidden" aria-labelledby="top-picks-title">
          <SectionHead
            title="أهم 10 أسهم مرشحة للصعود"
            note="ترتيب الأسهم حسب قوة الفرصة المتوقعة في آخر تحليل. النموذج يقدّر الصعود خلال 3 جلسات."
            badge="فترة الاحتفاظ: حتى 3 جلسات"
          />
          {isEmpty ? (
            <p className="p-10 text-center text-sm text-muted">لا توجد توصيات منشورة بعد. شغّل محرك التحليل أو راجع إعدادات Supabase.</p>
          ) : (
            <PickRows rows={recommendations} quoteBySymbol={quoteBySymbol} />
          )}
        </section>

        <section className="card mb-6 overflow-hidden" aria-labelledby="liquid-picks-title">
          <SectionHead
            title="أسهم سيولتها عالية ومرشحة للارتفاع"
            note="من توصيات الشراء الحالية، الأسهم التي تقع ضمن أعلى 60 سهماً سيولة (وسيط قيمة التداول اليومية لآخر 20 جلسة)."
            badge="سيولة عالية"
          />
          {insights.failed.includes("rising_picks") ? (
            <SectionError name="أسهم السيولة العالية" />
          ) : insights.risingPicks.length === 0 ? (
            <p className="p-10 text-center text-sm text-muted">لا توجد حالياً توصيات شراء ضمن الأسهم الأعلى سيولة.</p>
          ) : (
            <PickRows rows={insights.risingPicks} quoteBySymbol={quoteBySymbol} />
          )}
        </section>

        <section className="card mb-6 overflow-hidden" aria-labelledby="liquidity-title">
          <SectionHead
            title="سيولة البورصة المصرية يومياً"
            note="إجمالي قيمة التداول (السعر × الكمية) لكل جلسة، ثم أعلى الأسهم سيولة في آخر جلسة."
            badge={latestLiquidity ? `آخر جلسة: ${formatEgp(latestLiquidity.total_value_egp)} جنيه` : undefined}
          />
          {insights.failed.includes("liquidity") ? (
            <SectionError name="سيولة السوق" />
          ) : (
            <div className="p-4 sm:p-6">
              <LiquidityBars days={insights.liquidityDays} />
            </div>
          )}
          <div className="border-t border-line">
            {insights.failed.includes("leaders") ? (
              <SectionError name="أعلى الأسهم سيولة" />
            ) : insights.leaders.length === 0 ? (
              <p className="p-8 text-center text-sm text-muted">لا توجد بيانات سيولة لآخر جلسة بعد.</p>
            ) : (
              <>
                <h3 className="px-5 pt-5 text-sm font-semibold sm:px-6">
                  أعلى الأسهم سيولة · جلسة {insights.leaders[0].trade_date}
                </h3>
                <LeadersTable rows={insights.leaders} />
              </>
            )}
          </div>
        </section>

        <div className="grid gap-5 md:grid-cols-2">
          <div className="card p-6">
            <h3 className="mb-3 font-bold">محرك التحليل الذكي</h3>
            <p className="text-sm leading-7 text-muted">
              Pandas لتجهيز المؤشرات الفنية، وXGBoost لتقدير احتمال الصعود خلال 3 جلسات، مع دمج أسعار من أكثر من مصدر قبل إصدار التوصية.
            </p>
            <p className="mt-4 text-sm text-warn">● يعمل عبر GitHub Actions</p>
          </div>
          <div className="card p-6">
            <h3 className="mb-3 font-bold">إدارة المخاطر</h3>
            <p className="text-sm leading-7 text-muted">
              سعر الدخول والهدف ووقف الخسارة تُحسب من متوسط المدى الحقيقي ATR، وتُخزّن النتائج في Supabase لتقييم دقتها تلقائياً.
            </p>
            <p className="mt-4 text-sm text-warn">● تقييم بعد 3 جلسات</p>
          </div>
        </div>

        <footer className="mt-12 border-t border-line py-6 text-center text-xs leading-6 text-muted">
          EGX SMART TRADER © 2026 — أداة بحث وتحليل، وليست نصيحة استثمارية. الأسعار متأخرة أو آخر إغلاق يومي حسب المصدر، وليست بيانات لحظية.
        </footer>
      </section>
    </main>
  );
}
