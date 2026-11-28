"use client";

import type { MonthlyBar } from "@/lib/types";

const number = new Intl.NumberFormat("en-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const monthLabel = new Intl.DateTimeFormat("ar-EG", { month: "short", year: "2-digit", timeZone: "UTC" });

function previousCalendarMonth(monthStart: string): string {
  const date = new Date(`${monthStart}T00:00:00Z`);
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() - 1, 1)).toISOString().slice(0, 10);
}

export function MonthlyChart({ bars }: { bars: MonthlyBar[] }) {
  const latest = bars.at(-1);
  const previous = bars.at(-2);
  const priorMonth = latest && previous && previous.month_start === previousCalendarMonth(latest.month_start)
    ? previous
    : null;
  const pivot = priorMonth ? (priorMonth.high + priorMonth.low + priorMonth.close) / 3 : null;
  const safety = pivot === null || !priorMonth ? null : 2 * pivot - priorMonth.high;
  const risk = pivot === null || !priorMonth ? null : 2 * pivot - priorMonth.low;
  const monthChange = latest && priorMonth && priorMonth.close !== 0
    ? ((latest.close - priorMonth.close) / priorMonth.close) * 100
    : null;

  if (!latest) {
    return <p className="card p-8 text-center text-sm text-muted">لا توجد أشهر كافية لعرض الرسم.</p>;
  }

  const width = 840;
  const height = 330;
  const padding = { top: 24, right: 24, bottom: 48, left: 72 };
  const values = bars.flatMap((bar) => [bar.low, bar.high, bar.close]);
  if (safety !== null) values.push(safety);
  if (risk !== null) values.push(risk);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const span = Math.max(rawMax - rawMin, rawMax * 0.04, 1);
  const min = rawMin - span * 0.08;
  const max = rawMax + span * 0.08;
  const x = (index: number) => padding.left + (index * (width - padding.left - padding.right)) / Math.max(1, bars.length - 1);
  const y = (value: number) => padding.top + ((max - value) / (max - min)) * (height - padding.top - padding.bottom);
  const labelStep = Math.max(1, Math.ceil(bars.length / 6));

  return (
    <div>
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card p-4">
          <p className="text-xs text-muted">آخر إغلاق شهري</p>
          <p className="mt-2 text-xl font-bold" dir="ltr">{number.format(latest.close)}</p>
          <p className="mt-1 text-xs text-muted" dir="ltr">{latest.last_trade_date}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-muted">تغير الشهر</p>
          <p className={`mt-2 text-xl font-bold ${monthChange !== null && monthChange < 0 ? "text-down" : "text-up"}`} dir="ltr">
            {monthChange === null ? "—" : `${monthChange > 0 ? "+" : ""}${number.format(monthChange)}%`}
          </p>
          <p className="mt-1 text-xs text-muted">{latest.sessions} جلسة</p>
        </div>
        <div className="rounded-xl border border-up/30 bg-up-soft p-4">
          <p className="text-xs text-up">حد الأمان · دعم S1</p>
          <p className="mt-2 text-xl font-bold text-up" dir="ltr">{safety === null ? "—" : number.format(safety)}</p>
        </div>
        <div className="rounded-xl border border-down/30 bg-down-soft p-4">
          <p className="text-xs text-down">حد الخطر · مقاومة R1</p>
          <p className="mt-2 text-xl font-bold text-down" dir="ltr">{risk === null ? "—" : number.format(risk)}</p>
        </div>
      </div>

      <div className="card overflow-x-auto p-3">
        <svg viewBox={`0 0 ${width} ${height}`} className="min-w-[680px] w-full" role="img" aria-label="رسم إغلاق الأسهم شهرياً مع نطاق أعلى وأدنى سعر ومستويي الأمان والخطر">
          <title>الرسم الشهري لآخر {bars.length} شهراً</title>
          {[0, 1, 2, 3, 4].map((step) => {
            const value = min + ((max - min) * step) / 4;
            return (
              <g key={step}>
                <line x1={padding.left} x2={width - padding.right} y1={y(value)} y2={y(value)} stroke="#cfdfdb" />
                <text x={padding.left - 10} y={y(value) + 4} textAnchor="end" fill="#5d6f69" fontSize="11">{number.format(value)}</text>
              </g>
            );
          })}

          {bars.map((bar, index) => (
            <line key={`range-${bar.month_start}`} x1={x(index)} x2={x(index)} y1={y(bar.high)} y2={y(bar.low)} stroke="#9fb3ad" strokeWidth="2" />
          ))}

          {bars.slice(1).map((bar, index) => {
            const prior = bars[index];
            const rising = bar.close >= prior.close;
            return (
              <line
                key={`close-${bar.month_start}`}
                x1={x(index)}
                y1={y(prior.close)}
                x2={x(index + 1)}
                y2={y(bar.close)}
                stroke={rising ? "#0a7a4f" : "#c43d2f"}
                strokeWidth="3"
              />
            );
          })}

          {safety !== null && (
            <g>
              <line x1={padding.left} x2={width - padding.right} y1={y(safety)} y2={y(safety)} stroke="#0a7a4f" strokeDasharray="7 6" strokeWidth="1.5" />
              <text x={width - padding.right} y={y(safety) - 7} textAnchor="end" fill="#0a7a4f" fontSize="12">الأمان {number.format(safety)}</text>
            </g>
          )}
          {risk !== null && (
            <g>
              <line x1={padding.left} x2={width - padding.right} y1={y(risk)} y2={y(risk)} stroke="#c43d2f" strokeDasharray="7 6" strokeWidth="1.5" />
              <text x={width - padding.right} y={y(risk) - 7} textAnchor="end" fill="#c43d2f" fontSize="12">الخطر {number.format(risk)}</text>
            </g>
          )}

          {bars.map((bar, index) => {
            const prior = bars[index - 1];
            const color = !prior || bar.close >= prior.close ? "#0a7a4f" : "#c43d2f";
            return (
              <g key={bar.month_start}>
                <circle cx={x(index)} cy={y(bar.close)} r="4.5" fill={color} stroke="#fcfffe" strokeWidth="2">
                  <title>{monthLabel.format(new Date(`${bar.month_start}T00:00:00Z`))}: إغلاق {number.format(bar.close)}، أعلى {number.format(bar.high)}، أدنى {number.format(bar.low)}</title>
                </circle>
                {index % labelStep === 0 && (
                  <text x={x(index)} y={height - 18} textAnchor="middle" fill="#5d6f69" fontSize="11">{monthLabel.format(new Date(`${bar.month_start}T00:00:00Z`))}</text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="mt-5 flex flex-wrap gap-5 text-xs text-muted">
        <span className="flex items-center gap-2"><i className="h-0.5 w-6 bg-up" /> شهر صاعد</span>
        <span className="flex items-center gap-2"><i className="h-0.5 w-6 bg-down" /> شهر هابط</span>
        <span className="flex items-center gap-2"><i className="h-0.5 w-6 border-t border-dashed border-up" /> حد الأمان</span>
        <span className="flex items-center gap-2"><i className="h-0.5 w-6 border-t border-dashed border-down" /> حد الخطر</span>
      </div>

      <div className="mt-6 card p-5 text-sm leading-7 text-muted">
        <p className="mb-2 font-bold text-ink">طريقة حساب المستويين</p>
        {priorMonth ? (
          <p>
            نقطة الارتكاز = (أعلى {number.format(priorMonth.high)} + أدنى {number.format(priorMonth.low)} + إغلاق {number.format(priorMonth.close)}) ÷ 3.
            حد الأمان = 2 × نقطة الارتكاز − أعلى الشهر السابق. حد الخطر = 2 × نقطة الارتكاز − أدنى الشهر السابق.
          </p>
        ) : (
          <p>يلزم وجود الشهر السابق مباشرةً وبياناته الكاملة لإظهار المستويين؛ لا نستخدم شهراً أقدم بديلاً.</p>
        )}
        <p className="mt-2 text-warn">هذه مستويات دعم ومقاومة إرشادية، وليست وقف خسارة أو هدفاً مضموناً. الشهر الأخير قد يكون جزئياً.</p>
      </div>
    </div>
  );
}
