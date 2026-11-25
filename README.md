# EGX Smart Trader

محلل ذكي لأسهم البورصة المصرية (EGX) يهدف لاكتشاف أفضل فرص التداول قصيرة الأجل (2–3 أيام)، مع تحديد سعر الدخول والهدف ووقف الخسارة، وتقييم دقة التوصيات تلقائياً بعد انتهاء فترة الاحتفاظ.

> ⚠️ الأداة لأغراض البحث والتحليل فقط، وليست نصيحة استثمارية.

## النشر الحالي

- **الداشبورد:** https://egx-smart-trader.vercel.app
- **API:** https://egx-smart-trader.vercel.app/api/recommendations
- **محرك التحليل:** GitHub Actions على `mohammedfathi2532-code/egx-smart-trader` (الأحد–الخميس 13:30 UTC، بعد إغلاق السوق بتوقيت القاهرة).
- أي تعديل على ملفات الواجهة في الفرع `main` ينشر تلقائياً على Vercel عبر Deploy Hook.

## المعمارية

```
مصادر البيانات (Yahoo .CA / EGID / Borsa / OANOR / EGX.news / CSV)
        ↓  Python + Pandas + XGBoost  (GitHub Actions cron, post-close)
     Supabase (Postgres)
        ↓  read-only (publishable key + RLS)
   Next.js Dashboard على Vercel
```

- **Vercel** يستضيف الواجهة فقط؛ لا يشغّل Python.
- **GitHub Actions** يشغّل محرك Python بعد إغلاق السوق، ويفشل بوضوح عند غياب البيانات أو قلة السهم المؤهلة.
- الواجهة تقرأ من Supabase عبر مفتاح `sb_publishable_...` للقراءة فقط. لا توجد بيانات تجريبية؛ إذا تعذّر القراءة تظهر حالة فارغة وتنبيه وضوح.

## محتويات المشروع

| المسار | الوصف |
| --- | --- |
| `app/page.tsx` | لوحة التوصيات (أفضل 10 فرص) |
| `app/api/recommendations/route.ts` | JSON API للوحة |
| `lib/data.ts` | طبقة قراءة م cache + حالة فارغة صادقة عند تعذّر القراءة |
| `supabase/schema.sql` | الجداول، الـ view، وسياسات RLS |
| `engine/` | محرك التحليل بلغة Python |
| `engine/providers/` | موائمات المصادر (HTTP / CSV / Sample) |
| `.github/workflows/analyze.yml` | تشغيل محرك التحليل وكتابة النتائج في Supabase |
| `.github/workflows/deploy.yml` | نشر الداشبورد على Vercel عند تعديل الواجهة |
| `.github/workflows/analyze.yml` | جدولة التحليل |

## 1) إعداد Supabase

1. افتح مشروع Supabase.
2. اذهب إلى **SQL Editor** وشغّل محتوى `supabase/schema.sql`.
   - لو ظهر خطأ `column "symbol" referenced in foreign key constraint does not exist`، شغّل أولاً محتوى `supabase/reset.sql` ثم أعد تشغيل `supabase/schema.sql`. الملف ده بيحذف الهياكل القديمة فقط، والمشروع جديد فلاً بيانات مهمة فيه.
3. من **Project Settings** خذ:
   - **General → Project URL** → `https://xxxx.supabase.co` (لـ Vercel + GitHub)
   - **API Keys → Publishable key** → يبدأ بـ `sb_publishable_...` (للواجهة فقط).
   - **API Keys → Secret key** → يبدأ بـ `sb_secret_...` (لـ GitHub Actions فقط). **لا** تضعه في Vercel ولا تسبقه بـ `NEXT_PUBLIC_`.
   - شغّل أيضاً `supabase/migrations/0001_phase1_reliability.sql` لإضافة أعمدة بيانات التشغيل وحالة `skipped`، ثم `supabase/migrations/0002_phase2_signals.sql` لإضافة عمود الاحتمال وتحديث الـ view، و`supabase/migrations/0003_live_quotes.sql` لتحديث الأسعار كل 10 دقائق.

> لا يستخدم الكود مفاتيح `anon` / `service_role` القديمة. حدّث أسماء المتغيرات في Vercel وGitHub Secrets كما هو موضح أدناه.

الجداول التي تنشئها: `stocks`, `price_bars`, `analysis_runs`, `recommendations`, `recommendation_outcomes`, `data_source_status`، plus view اسمه `top_recommendations` يرجع أفضل 10 من آخر تشغيل ناجح.

## 2) إعداد Vercel

أضف متغيرين في **Project → Settings → Environment Variables**:

```
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

ثم أعد النشر. إذا لم يضيفا، ستظهر حالة فارغة وتنبيه بعدم توفر البيانات. احذف المتغير القديم `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

## 3) إعداد GitHub Secrets

في **Repo → Settings → Secrets and variables → Actions** أضف:

```
SUPABASE_URL
SUPABASE_SECRET_KEY           # sb_secret_... — استبدل الاسم القديم SUPABASE_SERVICE_ROLE_KEY
EGX_YAHOO_ENABLED=true
EGX_BORSA_ENABLED=true
EGX_HISTORY_DAYS=400
EGX_HORIZON_DAYS=3
EGX_TOP_N=10
EGX_MODEL_VERSION=xgboost-v1
```

> لم يعد `EGX_USE_SAMPLE` موجوداً؛ البيانات التجريبية غير مستخدمة في الإنتاج. حدّد القائمة والحدود في `engine/config/universe.json` أو اضبط `EGX_UNIVERSE_CONFIG`.

### البيانات الحقيقية (موصى بها، بلا مفتاح API)

بعد البحث في المصادر تبيّن أن:

- `https://ticker.egidegypt.com/api/Feed/GetAllMarketWatchNames` متاح للعموم ويعيد قائمة EGID الرسمية للأسهم (308 رمزاً بصيغة Reuters `.CA`). باقي endpoints في Swagger تتطلب Bearer token من `/api/Settings/GetToken` (بيانات دخول EGID).
- صفحة `https://egx.com.eg/en/infograph.aspx` محمية بتحدّي F5 ولا تعرض JSON يمكن استخدامه مباشرة.
- Yahoo Finance يوفّر شموعاً يومية حقيقية لرموز EGX بصيغة `.CA` (مثل `FWRY.CA`) بدون مفتاح.

لذلك اضبط في GitHub Secrets (أو `.env` محلياً):

```
EGX_YAHOO_ENABLED=true
EGX_YAHOO_RANGE=2y
EGX_YAHOO_UNIVERSE_URL=https://ticker.egidegypt.com/api/Feed/GetAllMarketWatchNames
```

قائمة الرموز والسيولة والحدود موجودة الآن في `engine/config/universe.json` (لا في الكود). المصدر يظهر في Supabase باسم `yahoo`، وعدد الصفوف يُسجّل في `data_source_status`.

### Borsa (مصدر مفتوح المصدر، اختياري)

[Borsa](https://github.com/7ashraf/borsa) خدمة FastAPI مفتوحة المصدر توحّد بيانات EGX من عدة مزودين. دمجناها في المحرك كمصدر للـ universe والقطاعات وتأكيد سعر اليوم:

- `/v1/stocks`: قائمة 223 سهماً مع اسم الشركة والقطاع → تُستخدم لتحديث جدول `stocks`.
- `/v1/quotes`: أسعار موحّدة مجمّعة (النسخة العامة تستخدم Yahoo خلف الكواليس) → شمعة واحدة ليوم التداول الأخير تُضاف إلى `price_bars` باسم `borsa`.
- لا يوجد endpoint للتاريخ في Borsa، لذلك المحرك يربط شمعة Borsa بآخر تاريخ تداول حقيقي جاي من Yahoo قبل الجمع، ولا يستخدم `timestamp` الخاص بالـ quote (ده وقت الجلب مش تاريخ الجلسة).
- الحجم يبقى صفر في شمعة Borsa حتى لا يتضاعف حجم Yahoo عند الدمج.

لتفعيله (بدون مفتاح على النسخة التجريبية):

```
EGX_BORSA_ENABLED=true
EGX_BORSA_BASE_URL=https://demo.borsa.ashh.me
EGX_BORSA_API_KEY=        # اختياري، لنسخة مستضافة ذاتياً
```

النسخة العامة لها حد يومي، لذلك في الإنتاج يفضّل استضافتها ذاتياً من [Docker image](https://ghcr.io/7ashraf/borsa:latest) مع مفاتيحك (BYOK). تظهر النتائج في `data_source_status` باسم `borsa` وتضاف إلى حقل `sources` في التوصيات.

### تحديث الأسعار كل 10 دقائق بمصدر مجاني

- الوضع المجاني لا يحتاج أي مفتاح: يستخدم [TradingView public EGX scanner](https://www.tradingview.com/) لجلب أسعار متأخرة للأسهم المتابعة فقط، عادةً بتأخير 15 دقيقة. هذا endpoint عام وغير رسمي، بلا ضمان خدمة أو SLA، وقد يتغير أو يُحظر؛ لا نعتبره بيانات لحظية.
- عند تعذّر TradingView يرجع المحرك إلى Yahoo Finance، لكنه يعرضها بوضوح كـ **آخر إغلاق يومي** وليس كتحديث أثناء الجلسة. Yahoo يظل أيضاً مصدر التاريخ اليومي للتحليل.
- EGID اختياري: إذا أضفت `EGID_USERNAME` و`EGID_PASSWORD` يصبح المصدر الأول تلقائياً، مع الرجوع إلى TradingView ثم Yahoo عند الفشل. `EGID_DELAY_SECONDS=900` هو الافتراضي.
- الرموز هي أحدث توصيات `top_recommendations` بحد `EGX_TOP_N`؛ وقبل وجود توصيات تُستخدم رموز البداية من `engine/config/universe.json`.
- شغّل `supabase/migrations/0003_live_quotes.sql`. في المشاريع الجديدة قد تحتاج إلى تفعيل جدول `live_quotes` من **Integrations → Data API → Exposed tables**.
- workflow الملف `.github/workflows/refresh.yml` مجدول كل 10 دقائق خلال نافذة تغطي جلسة EGX، ويتخطى التنفيذ خارج الساعة 10:00–15:00 بتوقيت القاهرة. زر **Run workflow** ينفّذ تحديثاً يدوياً حتى خارج الجلسة. مواعيد GitHub Actions قد تتأخر حسب ضغط الخدمة.
- التحديث لا يعيد تدريب النموذج؛ التحليل الكامل يظل بعد الإغلاق. الأخطاء الجزئية تظهر كتحذير، وإذا فشلت كل المصادر تبقى آخر أسعار ناجحة مع آخر وقت نجاح بدل اختلاق تحديث جديد.

ولكل مزود HTTP حقيقي (اختياري، إن توفرت لديك رخصة/مفتاح) أضف المتغيرات المناسبة. البادئات المدعومة: `DATACEDAR`, `EGID`, `BORSA`, `EGX`, `OANOR`, `EGXNEWS`.

```
{PREFIX}_API_KEY
{PREFIX}_UNIVERSE_URL
{PREFIX}_HISTORY_URL
{PREFIX}_AUTH_HEADER       # مثال: x-oanor-key أو "Authorization: Bearer {token}"
{PREFIX}_EXTRA_HEADERS     # مثال: "x-rapidapi-host: egx-live.p.rapidapi.com"
```

الروابط تدعم `{symbol}` و `{days}` و `{start}` و `{end}` و `{api_key}`. المفتاح يُرسل في الهيدر فقط، أبداً في الـ URL. مقارنة المصادر والتكاليف والتراخيص في `docs/DATA_SOURCES.md`.

> رخصة EGID/EGX.news/EODHD تجارية؛ تأكد من شروط الوصول قبل استخدام بياناتها تجارياً. TradingView وYahoo/Borsa مصادر غير رسمية أو متأخرة وليست تغذية EGX الرسمية.

## 4) التشغيل محلياً

```bash
# واجهة Next.js
npm install
cp .env.example .env      # عدّل القيم
npm run dev

# محرك Python
python -m pip install -r engine/requirements.txt
python -m engine.run

# تحديث الأسعار المتأخرة فقط
python -m pip install -r engine/requirements-refresh.txt
python -m engine.refresh
```

المحرك يحتاج إلى مصدر حقيقي واحد على الأقل (`EGX_YAHOO_ENABLED=true` هو الافتراضي). لا يُستخدم مولّد البيانات التجريبية في التشغيل العادي، ولا تُعرض بيانات وهمية في اللوحة. للتشغيل محلياً انسخ `.env.example` إلى `.env` واضبط المفاتيح ثم شغّل الأوامر أعلاه.

## 5) كيف تُحسب التوصية؟

1. **الجمع:** أسعار يومية من كل المصادر، ثم دمجها ( Median للإغلاق، max للأعلى، min للأدنى ) في سلسلة موحدة لكل سهم.
2. **المؤشرات:** عوائد 1/3/5/10 أيام، SMAs، EMAs، MACD، RSI14، ATR14، Bollinger، حجم التداول، التقلب، وميل الاتجاه.
3. **التنبؤ:** نموذج `XGBClassifier` يتنبأ باحتمال أن يتحقق صعود ≥ `model.label_target_pct` خلال `EGX_HORIZON_DAYS` جلسات. التدريب زمني مع فاصل تطهير `purge_sessions` لمنع تسرب النوافذ المستقبلية.
4. **المخاطرة:** الدخول = آخر إغلاق، والهدف/الوقف يُحسبان من ATR النسبي مع دعم/مقاومة آخر 20 جلسة، بحدود قصوى للصعود والخسارة، واحترام حدّ الإغلاق اليومي ±10% وتدرّج السعر. كل المعاملات في `engine/config/signals.json`.
5. **الإشارة والترتيب:** الاحتمال + العائد/المخاطرة + الزخم + الحجم تُنتج `شراء قوي / شراء / مراقبة / تجنّب`. درجة القوة مركّبة وموثّقة في `docs/MODEL_REPORT.md`، ثم تُؤخذ أعلى 10.
6. **التقييم:** بعد مرور فترة الاحتفاظ تُقارن الأسعار اللاحقة بالهدف والوقف وتُخزّن النتيجة `win / loss / flat`.

## 6) رفع الكود إلى GitHub

إذا لم يكن الـ remote مضافاً محلياً:

```bash
git remote add origin https://github.com/<USERNAME>/egx-smart-trader.git
git push -u origin master
```

بعد الدفع سيقوم Vercel بنشر الواجهة، وسيبدأ الـ cron بتشغيل `python -m engine.run` يومياً (الأحد–الخميس). يمكنك تجربة التشغيل فوراً من زر **Run workflow** في تبويب Actions.

## Phase 1 notes (English)

- Scheduler: `30 13 * * 0-4` UTC (15:30 EET / 16:30 EEST, after the 14:30 Cairo close). GitHub cron cannot follow DST; the later summer offset is intentional.
- A run with no new market date is recorded as `skipped` and does not publish duplicate recommendations.
- Raw bars are quality-checked before persistence; symbols need `quality.min_history_bars` and minimum 20-session median traded value from `engine/config/universe.json`.
- "Stocks scanned" now comes from `analysis_runs.universe_size`. The dashboard shows last successful run time, market date, and a stale-data banner.
- Manual steps after merging: rename the Vercel key to `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, rename the GitHub secret to `SUPABASE_SECRET_KEY`, apply `supabase/migrations/0001_phase1_reliability.sql` and `supabase/migrations/0003_live_quotes.sql`, expose `live_quotes` in Supabase Data API if required, then redeploy Vercel and run the workflow manually once.

## Phase 2 notes (English)

- All signal, risk, tick-size and scoring thresholds live in `engine/config/signals.json`; `EGX_TARGET_PCT` and the old ATR env vars are no longer used.
- Targets and stops use per-stock ATR plus recent support/resistance, capped by configured upside/stop limits, the EGX ±10% daily price limit and tick sizes.
- Signals are `شراء قوي / شراء / مراقبة / تجنّب`; the raw model probability is stored in `recommendations.probability` and shown in the dashboard.
- Model validation uses a chronological split with a purge window around the boundary. Precision, recall and buy hit rate are written to `docs/MODEL_REPORT.md` on every successful run.
- Apply `supabase/migrations/0002_phase2_signals.sql` before running the new engine.
