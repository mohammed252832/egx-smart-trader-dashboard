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
    <section className="rounded-2xl border border-white/10 bg-[#111c30] p-5 sm:p-6">
      <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
        <label className="block text-sm text-gray-400">
          ابحث عن الشركة
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="الرمز أو اسم الشركة"
            className="mt-2 w-full rounded-xl border border-white/10 bg-[#0a1120] px-4 py-3 text-white outline-none focus:border-emerald-400"
          />
        </label>
        <label className="block text-sm text-gray-400">
          اختر السهم
          <select
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
            className="mt-2 w-full rounded-xl border border-white/10 bg-[#0a1120] px-4 py-3 text-white outline-none focus:border-emerald-400"
          >
            {matches.map((row) => <option key={row.symbol} value={row.symbol}>{row.symbol} — {row.name}</option>)}
          </select>
        </label>
        {symbol ? (
          <Link href={`/stocks/${symbol}`} className="rounded-xl bg-emerald-500 px-6 py-3 text-center font-bold text-[#07120d] transition hover:bg-emerald-400">
            عرض الرسم الشهري
          </Link>
        ) : (
          <button type="button" disabled className="rounded-xl bg-white/10 px-6 py-3 font-bold text-gray-500">لا توجد بيانات</button>
        )}
      </div>
      <p className="mt-4 text-xs text-gray-500">يعرض {matches.length} سهماً. يمكنك أيضاً الضغط على أي سهم في صفحة «آخر تحديث للسوق».</p>
    </section>
  );
}
