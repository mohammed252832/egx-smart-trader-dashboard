import { AutoRefresh } from "@/app/auto-refresh";
import { getLatestMarket } from "@/lib/market-data";
import { MarketTable } from "./market-table";

export const instant = false;

export default async function MarketPage() {
  const rows = await getLatestMarket(250);
  const liveCount = rows.filter((row) => row.price_origin === "live_quote").length;
  const dailyCount = rows.length - liveCount;

  return (
    <main dir="rtl" className="min-h-screen px-5 py-10 sm:px-8">
      <AutoRefresh />
      <div className="mx-auto max-w-7xl">
        <header className="mb-8">
          <h1 className="text-3xl font-bold">آخر تحديث لأسهم البورصة المصرية</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
            أعلى 250 سهماً حسب سيولة آخر 20 جلسة، مع عرض العدد الفعلي المتاح. اضغط على أي سهم لفتح رسمه الشهري.
          </p>
        </header>

        <div className="mb-6 grid gap-3 sm:grid-cols-3">
          <div className="card p-5">
            <p className="text-sm text-muted">أسهم متاحة الآن</p>
            <p className="mt-2 text-3xl font-bold text-brand">{rows.length}</p>
          </div>
          <div className="card p-5">
            <p className="text-sm text-muted">بسعر تحديث متأخر</p>
            <p className="mt-2 text-3xl font-bold text-up">{liveCount}</p>
          </div>
          <div className="card p-5">
            <p className="text-sm text-muted">بآخر إغلاق يومي</p>
            <p className="mt-2 text-3xl font-bold text-warn">{dailyCount}</p>
          </div>
        </div>

        <div className="mb-6 rounded-xl border border-warn/30 bg-warn-soft p-4 text-sm leading-7 text-warn">
          المصادر المجانية متأخرة أو يومية. تاريخ كل سعر ظاهر بجوار المصدر، ولا نملأ البيانات الناقصة بأرقام تقديرية.
        </div>

        <MarketTable rows={rows} />
      </div>
    </main>
  );
}
