"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { MarketStock } from "@/lib/types";

export function StockPicker({ rows }: { rows: MarketStock[] }) {
  const [query, setQuery] = useState("");
  const [symbol, setSymbol] = useState(rows[0]?.symbol ?? "");
  const matches = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return rows;
    return rows.filter((row) => `${row.symbol} ${row.name}`.toLowerCase().includes(term));
  }, [query, rows]);

  return (
    <section className="card p-5 sm:p-6">
      <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
        <label className="block text-sm font-semibold">
          ابحث عن الشركة
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="الرمز أو اسم الشركة"
            className="field mt-2"
          />
        </label>
        <label className="block text-sm font-semibold">
          اختر السهم
          <select
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
            className="field mt-2"
          >
            {matches.map((row) => <option key={row.symbol} value={row.symbol}>{row.symbol} — {row.name}</option>)}
          </select>
        </label>
        {symbol ? (
          <Link href={`/stocks/${symbol}`} className="btn-primary">
            عرض الرسم الشهري
          </Link>
        ) : (
          <button type="button" disabled className="btn-quiet opacity-60">لا توجد بيانات</button>
        )}
      </div>
      <p className="mt-4 text-xs text-muted">يعرض {matches.length} سهماً. يمكنك أيضاً الضغط على أي سهم في صفحة «آخر تحديث للسوق».</p>
    </section>
  );
}
