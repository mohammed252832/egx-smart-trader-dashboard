import type { LiquidityDay, MarketStatePoint } from "@/lib/types";

const number = new Intl.NumberFormat("en-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const dayLabel = new Intl.DateTimeFormat("ar-EG", { day: "numeric", month: "short", timeZone: "UTC" });

const shortDate = (value: string) => dayLabel.format(new Date(`${value}T00:00:00Z`));

export function formatEgp(value: number): string {
  if (value >= 1_000_000_000) return `${new Intl.NumberFormat("en-EG", { maximumFractionDigits: 2 }).format(value / 1_000_000_000)} مليار`;
  if (value >= 1_000_000) return `${new Intl.NumberFormat("en-EG", { maximumFractionDigits: 0 }).format(value / 1_000_000)} مليون`;
  return new Intl.NumberFormat("en-EG", { maximumFractionDigits: 0 }).format(value);
}

/** Equal-weighted index of the most liquid stocks, with its 20-session average. */
export function MarketStateChart({ points }: { points: MarketStatePoint[] }) {
  const data = points.slice(-60);
  if (data.length < 2) {
    return <p className="p-8 text-center text-sm text-muted">لا توجد جلسات كافية لرسم اتجاه السوق بعد.</p>;
  }

  const width = 840;
  const height = 280;
  const pad = { top: 20, right: 20, bottom: 40, left: 56 };
  const values = data.flatMap((point) => [point.index_value, ...(point.ma20 === null ? [] : [point.ma20])]);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const span = Math.max(rawMax - rawMin, 1);
  const min = rawMin - span * 0.1;
  const max = rawMax + span * 0.1;
  const x = (index: number) => pad.left + (index * (width - pad.left - pad.right)) / (data.length - 1);
  const y = (value: number) => pad.top + ((max - value) / (max - min)) * (height - pad.top - pad.bottom);
  const line = data.map((point, index) => `${index === 0 ? "M" : "L"}${x(index).toFixed(1)} ${y(point.index_value).toFixed(1)}`).join(" ");
  const avgPoints = data
    .map((point, index) => (point.ma20 === null ? null : `${x(index).toFixed(1)} ${y(point.ma20).toFixed(1)}`))
    .filter((value): value is string => value !== null);
  const avgLine = avgPoints.length > 1 ? `M${avgPoints.join(" L")}` : null;
  const labelStep = Math.max(1, Math.ceil(data.length / 6));
  const last = data[data.length - 1];

  return (
    <div dir="ltr" className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="min-w-[620px] w-full"
        role="img"
        aria-label="رسم اتجاه السوق: مؤشر الأسهم الأعلى سيولة ومتوسطه لـ 20 جلسة"
      >
        <title>اتجاه السوق خلال آخر {data.length} جلسة</title>
        {[0, 1, 2, 3].map((step) => {
          const value = min + ((max - min) * step) / 3;
          return (
            <g key={step}>
              <line x1={pad.left} x2={width - pad.right} y1={y(value)} y2={y(value)} stroke="#cfdfdb" strokeWidth="1" />
              <text x={pad.left - 8} y={y(value) + 4} textAnchor="end" fill="#5d6f69" fontSize="11">{number.format(value)}</text>
            </g>
          );
        })}
        {avgLine && <path d={avgLine} fill="none" stroke="#b7791f" strokeWidth="2" strokeDasharray="6 5" />}
        <path d={line} fill="none" stroke="#006844" strokeWidth="2.5" strokeLinejoin="round" />
        <circle cx={x(data.length - 1)} cy={y(last.index_value)} r="5" fill="#006844" stroke="#fcfffe" strokeWidth="2" />
        {data.map((point, index) =>
          index % labelStep === 0 ? (
            <text key={point.trade_date} x={x(index)} y={height - 14} textAnchor="middle" fill="#5d6f69" fontSize="11">
              {shortDate(point.trade_date)}
            </text>
          ) : null,
        )}
      </svg>
    </div>
  );
}

/** Daily traded value for the whole market. Sessions with thin coverage are drawn lighter. */
export function LiquidityBars({ days }: { days: LiquidityDay[] }) {
  const data = days.slice(-20);
  if (data.length === 0) {
    return <p className="p-8 text-center text-sm text-muted">لا توجد بيانات سيولة منشورة بعد.</p>;
  }

  const counts = data.map((day) => day.symbols_traded).sort((a, b) => a - b);
  const median = counts[Math.floor(counts.length / 2)];
  const width = 840;
  const height = 260;
  const pad = { top: 20, right: 16, bottom: 40, left: 16 };
  const max = Math.max(...data.map((day) => day.total_value_egp), 1);
  const slot = (width - pad.left - pad.right) / data.length;
  const barWidth = Math.min(34, slot * 0.62);
  const labelStep = Math.max(1, Math.ceil(data.length / 8));
  const hasPartial = data.some((day) => day.symbols_traded < median * 0.7);

  return (
    <div>
      <div dir="ltr" className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="min-w-[620px] w-full"
          role="img"
          aria-label="رسم السيولة اليومية للبورصة المصرية بالجنيه"
        >
          <title>السيولة اليومية خلال آخر {data.length} جلسة</title>
          <line x1={pad.left} x2={width - pad.right} y1={height - pad.bottom} y2={height - pad.bottom} stroke="#cfdfdb" />
          {data.map((day, index) => {
            const barHeight = (day.total_value_egp / max) * (height - pad.top - pad.bottom);
            const cx = pad.left + slot * index + slot / 2;
            const partial = day.symbols_traded < median * 0.7;
            return (
              <g key={day.trade_date}>
                <rect
                  x={cx - barWidth / 2}
                  y={height - pad.bottom - barHeight}
                  width={barWidth}
                  height={barHeight}
                  rx="3"
                  fill={partial ? "#9fc9b8" : "#006844"}
                >
                  <title>{`${shortDate(day.trade_date)}: ${formatEgp(day.total_value_egp)} جنيه، ${day.symbols_traded} سهماً متداولاً`}</title>
                </rect>
                {index % labelStep === 0 && (
                  <text x={cx} y={height - 14} textAnchor="middle" fill="#5d6f69" fontSize="11">{shortDate(day.trade_date)}</text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
      {hasPartial && (
        <p className="mt-3 flex items-center gap-2 text-xs text-muted">
          <i className="inline-block h-3 w-3 rounded-sm bg-[#9fc9b8]" />
          أعمدة فاتحة: جلسات وصلتنا عنها بيانات لعدد أقل من الأسهم المعتاد، فقد تكون السيولة الحقيقية أعلى.
        </p>
      )}
    </div>
  );
}
