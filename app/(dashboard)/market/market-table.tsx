"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import type { MarketStock } from "@/lib/types";

const number = new Intl.NumberFormat("en-EG", { maximumFractionDigits: 2 });
const integer = new Intl.NumberFormat("en-EG", { maximumFractionDigits: 0 });

function sourceLabel(stock: MarketStock) {
  if (stock.price_origin === "daily_close") return "آخر إغلاق يومي";
  if (stock.source === "egid_delayed") return "EGID الرسمي";
  if (stock.source === "egid_public_delayed") return "EGID الرسمي (عام)";
  if (stock.source === "tradingview_delayed") return "TradingView (غير رسمي)";
  if (stock.source === "yahoo_delayed") return "Yahoo Finance";
  return "مصدر متأخر";
}

function Change({ value }: { value: number | null }) {
  if (value === null) return <span className="text-muted">—</span>;
  const style = value > 0 ? "text-up" : value < 0 ? "text-down" : "text-muted";
  return <span className={style} dir="ltr">{value > 0 ? "+" : ""}{number.format(value)}%</span>;
}

export function MarketTable({ rows }: { rows: MarketStock[] }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return rows;
    return rows.filter((row) => `${row.symbol} ${row.name} ${row.sector ?? ""}`.toLowerCase().includes(term));
  }, [query, rows]);

  const openStock = (symbol: string) => router.push(`/stocks/${symbol}`);

  return (
    <section className="card p-5 sm:p-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <label className="w-full sm:w-80">
          <span className="sr-only">ابحث عن سهم</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="ابحث بالرمز أو اسم الشركة"
            className="field text-sm"
          />
        </label>
        <p className="text-xs text-muted">يعرض {filtered.length} من أصل {rows.length} سهماً متاحاً</p>
      </div>

      {filtered.length === 0 ? (
        <p className="rounded-xl border border-line p-8 text-center text-sm text-muted">لا توجد أسهم مطابقة للبحث أو لم تتوفر بيانات سوق كافية بعد.</p>
      ) : (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[900px] text-right text-sm">
              <thead>
                <tr className="border-b border-line text-xs text-muted">
                  <th className="p-3">#</th>
                  <th className="p-3">السهم</th>
                  <th className="p-3">القطاع</th>
                  <th className="p-3">آخر سعر</th>
                  <th className="p-3">التغير</th>
                  <th className="p-3">الافتتاح</th>
                  <th className="p-3">أعلى / أدنى</th>
                  <th className="p-3">الحجم</th>
                  <th className="p-3">المصدر والتاريخ</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((stock) => (
                  <tr
                    key={stock.symbol}
                    role="link"
                    tabIndex={0}
                    aria-label={`عرض الرسم الشهري لسهم ${stock.symbol}`}
                    onClick={() => openStock(stock.symbol)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        openStock(stock.symbol);
                      }
                    }}
                    className="cursor-pointer border-b border-line/70 align-middle transition hover:bg-brand-soft focus:bg-brand-soft focus:outline-none"
                  >
                    <td className="p-3 text-muted">{stock.liquidity_rank}</td>
                    <td className="p-3">
                      <p className="font-bold text-brand">{stock.symbol}</p>
                      <p className="mt-1 max-w-52 truncate text-xs text-muted">{stock.name}</p>
                    </td>
                    <td className="p-3 text-muted">{stock.sector ?? "—"}</td>
                    <td className="p-3 font-bold" dir="ltr">{number.format(stock.price)}</td>
                    <td className="p-3"><Change value={stock.change_pct} /></td>
                    <td className="p-3" dir="ltr">{stock.open === null ? "—" : number.format(stock.open)}</td>
                    <td className="p-3" dir="ltr">{stock.high === null || stock.low === null ? "—" : `${number.format(stock.high)} / ${number.format(stock.low)}`}</td>
                    <td className="p-3" dir="ltr">{integer.format(stock.volume)}</td>
                    <td className="p-3">
                      <p className="text-xs">{sourceLabel(stock)}</p>
                      <p className="mt-1 text-xs text-muted" dir="ltr">{stock.effective_market_date ?? "—"}</p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 md:hidden">
            {filtered.map((stock) => (
              <button
                key={stock.symbol}
                type="button"
                onClick={() => openStock(stock.symbol)}
                className="card p-4 text-right transition hover:border-brand"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-bold text-brand">{stock.symbol}</p>
                    <p className="mt-1 text-xs text-muted">{stock.name}</p>
                  </div>
                  <div className="text-left">
                    <p className="font-bold" dir="ltr">{number.format(stock.price)}</p>
                    <p className="mt-1 text-xs"><Change value={stock.change_pct} /></p>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between gap-2 text-xs text-muted">
                  <span>{sourceLabel(stock)}</span>
                  <span dir="ltr">{stock.effective_market_date ?? "—"}</span>
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
