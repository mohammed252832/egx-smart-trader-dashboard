import { AutoRefresh } from "@/app/auto-refresh";
import { getLatestMarket } from "@/lib/market-data";
import { StockPicker } from "./stock-picker";

export const instant = false;

export default async function ChartsPage() {
  const rows = await getLatestMarket(250);

  return (
    <main dir="rtl" className="min-h-screen px-5 py-10 sm:px-8">
      <AutoRefresh />
      <div className="mx-auto max-w-5xl">
        <header className="mb-8">
          <h1 className="text-3xl font-bold">الرسوم الشهرية للأسهم</h1>
          <p className="mt-3 text-sm leading-7 text-muted">اختر أي سهم متاح لعرض صعود وهبوطه الشهري، ومستويي الدعم والمقاومة المشتقين من الشهر السابق.</p>
        </header>
        <StockPicker rows={rows} />
        <div className="mt-6 card p-5 text-sm leading-7 text-muted">
          «حد الأمان» هو الدعم S1، و«حد الخطر» هو المقاومة R1 في طريقة نقاط الارتكاز الكلاسيكية. المستوىان إرشاديان فقط، وليسا وقف خسارة أو هدفاً مضموناً.
        </div>
      </div>
    </main>
  );
}
