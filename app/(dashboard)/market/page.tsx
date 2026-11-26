import { AutoRefresh } from "@/app/auto-refresh";
import { getLatestMarket } from "@/lib/market-data";
import { MarketTable } from "./market-table";

export const instant = false;

export default async function MarketPage() {
  const rows = await getLatestMarket(250);
  const liveCount = rows.filter((row) => row.price_origin === "live_quote").length;
  const dailyCount = rows.length - liveCount;

  return (
    <main dir="rtl" className="min-h-screen bg-[#0a1120] px-5 py-10 text-white sm:px-8">
      <AutoRefresh />
      <div className="mx-auto max-w-7xl">
        <header className="mb-8">
          <p className="text-sm text-emerald-400">EGX SMART TRADER</p>
          <h1 className="mt-2 text-3xl font-black">آخر تحديث لأسهم البورصة المصرية</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-gray-500">
            أعلى 250 سهماً حسب سيولة آخر 20 جلسة، مع عرض العدد الفعلي المتاح. اضغط على أي سهم لفتح رسمه الشهري.
          </p>
        </header>

        <div className="mb-6 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-[#111c30] p-5">
            <p className="text-sm text-gray-500">أسهم متاحة الآن</p>
            <p className="mt-2 text-3xl font-black text-emerald-400">{rows.length}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#111c30] p-5">
            <p className="text-sm text-gray-500">بسعر تحديث متأخر</p>
            <p className="mt-2 text-3xl font-black text-cyan-400">{liveCount}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#111c30] p-5">
            <p className="text-sm text-gray-500">بآخر إغلاق يومي</p>
            <p className="mt-2 text-3xl font-black text-yellow-400">{dailyCount}</p>
          </div>
        </div>

        <div className="mb-6 rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-4 text-sm leading-7 text-yellow-200/80">
          المصادر المجانية متأخرة أو يومية. تاريخ كل سعر ظاهر بجوار المصدر، ولا نملأ البيانات الناقصة بأرقام تقديرية.
        </div>

        <MarketTable rows={rows} />
      </div>
    </main>
  );
}
