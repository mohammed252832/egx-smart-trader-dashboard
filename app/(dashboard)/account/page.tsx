import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { getSupabaseServerClient } from "@/lib/supabase";
import { addToWatchlist, removeFromWatchlist, saveProfile } from "./actions";

export const instant = false;

const MESSAGES: Record<string, string> = {
  name: "اكتب اسماً من حرفين على الأقل.",
  symbol: "رمز السهم غير صالح.",
  unknown: "هذا الرمز غير موجود في قائمة الأسهم المتاحة.",
  save: "تعذّر حفظ التغيير. حاول مرة أخرى.",
  config: "إعدادات الخادم غير مكتملة.",
};

type WatchRow = { ticker: string };
type StockRow = { symbol: string; name: string };

export default async function AccountPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; saved?: string }>;
}) {
  const user = await requireUser();
  const { error, saved } = await searchParams;
  const supabase = await getSupabaseServerClient();
  if (!supabase) throw new Error("Supabase is not configured");

  const [profileResult, watchResult] = await Promise.all([
    supabase
      .from("profiles")
      .select("display_name,alert_market_summary,alert_watchlist")
      .eq("id", user.id)
      .maybeSingle(),
    supabase.from("watchlist").select("ticker").eq("user_id", user.id).order("created_at", { ascending: true }),
  ]);
  if (profileResult.error || watchResult.error) {
    throw new Error(`Account read failed: ${profileResult.error?.message ?? watchResult.error?.message}`);
  }

  const tickers = ((watchResult.data as WatchRow[] | null) ?? []).map((row) => row.ticker);
  const namesResult = tickers.length
    ? await supabase.from("stocks").select("symbol,name").in("symbol", tickers)
    : { data: [] as StockRow[], error: null };
  const nameBySymbol = new Map(((namesResult.data as StockRow[] | null) ?? []).map((row) => [row.symbol, row.name]));

  const profile = profileResult.data as {
    display_name: string | null;
    alert_market_summary: boolean;
    alert_watchlist: boolean;
  } | null;
  const message = error ? MESSAGES[error] ?? null : null;

  return (
    <main dir="rtl" className="min-h-screen px-5 py-10 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-brand">حسابك الخاص</p>
            <h1 className="mt-1 text-3xl font-bold">الملف الشخصي والمتابعة</h1>
          </div>
          <Link href="/" className="text-sm font-semibold text-brand hover:underline">
            العودة إلى السوق
          </Link>
        </div>

        <div className="card mb-6 flex flex-wrap items-center justify-between gap-2 px-5 py-4 text-sm">
          <span>
            <span className="text-muted">مسجل الدخول: </span>
            <span className="font-semibold" dir="ltr">{user.email}</span>
          </span>
          <span className="text-muted">بياناتك خاصة بحسابك</span>
        </div>

        {message && (
          <p className="mb-6 rounded-lg border border-down/30 bg-down-soft p-3 text-sm text-down" role="alert">{message}</p>
        )}
        {saved === "1" && (
          <p className="mb-6 rounded-lg border border-up/30 bg-up-soft p-3 text-sm text-up" role="status">تم حفظ التغييرات.</p>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <section className="card overflow-hidden">
            <div className="border-b border-line p-6">
              <p className="text-sm font-semibold text-brand">البيانات الشخصية</p>
              <h2 className="mt-1 text-xl font-bold">الاسم والتنبيهات</h2>
            </div>
            <form action={saveProfile} className="space-y-6 p-6">
              <label className="block text-sm font-semibold">
                الاسم الظاهر
                <input
                  name="display_name"
                  defaultValue={profile?.display_name ?? user.displayName}
                  required
                  minLength={2}
                  maxLength={60}
                  className="field mt-2"
                />
              </label>

              <div>
                <h3 className="mb-3 text-sm font-semibold text-brand">تفضيلات التنبيه</h3>
                <div className="divide-y divide-line">
                  <div className="flex items-center justify-between gap-4 py-4">
                    <div>
                      <p className="font-semibold">ملخص حركة السوق</p>
                      <p className="mt-1 text-xs text-muted">حفظ تفضيل التنبيه على تغيرات السوق</p>
                    </div>
                    <label className="switch">
                      <input type="checkbox" name="alert_market_summary" defaultChecked={profile?.alert_market_summary ?? true} aria-label="ملخص حركة السوق" />
                      <span />
                    </label>
                  </div>
                  <div className="flex items-center justify-between gap-4 py-4">
                    <div>
                      <p className="font-semibold">حركة الأسهم المفضلة</p>
                      <p className="mt-1 text-xs text-muted">حفظ تفضيل التنبيه على قائمتك المتابعة</p>
                    </div>
                    <label className="switch">
                      <input type="checkbox" name="alert_watchlist" defaultChecked={profile?.alert_watchlist ?? true} aria-label="حركة الأسهم المفضلة" />
                      <span />
                    </label>
                  </div>
                </div>
                <p className="mt-3 text-xs leading-6 text-muted">
                  تُحفظ هذه التفضيلات في حسابك؛ إرسال التنبيهات نفسها يحتاج إلى توفر مصدر بيانات موثوق.
                </p>
              </div>

              <button type="submit" className="btn-primary w-full">حفظ التغييرات</button>
            </form>
          </section>

          <section className="card overflow-hidden">
            <div className="flex items-center justify-between gap-3 border-b border-line p-6">
              <div>
                <p className="text-sm font-semibold text-brand">قائمة خاصة</p>
                <h2 className="mt-1 text-xl font-bold">الأسهم المفضلة</h2>
              </div>
              <span className="rounded-lg border border-line px-3 py-1 text-xs text-muted">{tickers.length} سهم</span>
            </div>
            <form action={addToWatchlist} className="flex gap-3 border-b border-line p-6">
              <label className="flex-1 text-xs font-semibold text-muted">
                رمز السهم
                <input name="symbol" dir="ltr" placeholder="COMI" required maxLength={12} className="field mt-2 text-left uppercase" />
              </label>
              <button type="submit" className="btn-primary self-end">إضافة</button>
            </form>
            {tickers.length === 0 ? (
              <div className="p-10 text-center">
                <p className="font-semibold">قائمتك فارغة حتى الآن</p>
                <p className="mt-2 text-sm text-muted">أضف رموز الأسهم التي تود متابعتها.</p>
              </div>
            ) : (
              <ul className="divide-y divide-line">
                {tickers.map((ticker) => (
                  <li key={ticker} className="flex items-center justify-between gap-3 px-6 py-4">
                    <Link href={`/stocks/${ticker}`} className="min-w-0">
                      <span className="font-bold text-brand" dir="ltr">{ticker}</span>
                      <span className="mt-0.5 block truncate text-xs text-muted">{nameBySymbol.get(ticker) ?? ""}</span>
                    </Link>
                    <form action={removeFromWatchlist}>
                      <input type="hidden" name="symbol" value={ticker} />
                      <button type="submit" className="btn-quiet !px-3 !py-1.5 text-sm text-down">إزالة</button>
                    </form>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
