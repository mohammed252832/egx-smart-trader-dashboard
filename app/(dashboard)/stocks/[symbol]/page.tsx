import Link from "next/link";
import { notFound } from "next/navigation";
import { AutoRefresh } from "@/app/auto-refresh";
import { getStockChartData } from "@/lib/market-data";
import { MonthlyChart } from "./monthly-chart";

export const instant = false;

export default async function StockPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = await params;
  if (!/^[A-Za-z0-9]{1,12}$/.test(symbol)) notFound();
  const stock = await getStockChartData(symbol);
  if (!stock) notFound();

  const sources = [...new Set(stock.bars.flatMap((bar) => bar.sources))];

  return (
    <main dir="rtl" className="min-h-screen bg-[#0a1120] px-5 py-10 text-white sm:px-8">
      <AutoRefresh />
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <Link href="/market" className="text-sm text-emerald-400 hover:text-emerald-300">← العودة لآخر تحديث السوق</Link>
          <Link href="/charts" className="text-sm text-gray-400 hover:text-white">اختيار سهم آخر</Link>
        </div>
        <header className="mb-8">
          <p className="text-sm text-emerald-400">الرسم الشهري · {stock.symbol}</p>
          <h1 className="mt-2 text-3xl font-black">{stock.name}</h1>
          <p className="mt-2 text-sm text-gray-500">{stock.sector ?? "قطاع غير متاح"} · آخر {stock.bars.length} شهراً متاحاً</p>
        </header>

        {stock.bars.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-[#111c30] p-10 text-center">
            <p className="font-bold">لا يوجد تاريخ شهري منشور لهذا السهم بعد.</p>
            <p className="mt-3 text-sm text-gray-500">سيظهر هنا تلقائياً بعد جمع بيانات يومية حقيقية كافية من Yahoo Finance أو المصادر المدعومة.</p>
          </div>
        ) : (
          <MonthlyChart bars={stock.bars} />
        )}

        <footer className="mt-10 border-t border-white/10 py-6 text-center text-xs leading-6 text-gray-600">
          المصدر: {sources.length ? sources.join(" + ") : "غير متاح"}. أداة بحث وتحليل، وليست نصيحة استثمارية.
        </footer>
      </div>
    </main>
  );
}
