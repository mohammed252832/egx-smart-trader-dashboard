# EGX Smart Trader

محلل ذكي لأسهم البورصة المصرية (EGX) يهدف لاكتشاف أفضل فرص التداول قصيرة الأجل (2–3 أيام)، مع تحديد سعر الدخول والهدف ووقف الخسارة، وتقييم دقة التوصيات تلقائياً بعد انتهاء فترة الاحتفاظ.

> ⚠️ الأداة لأغراض البحث والتحليل فقط، وليست نصيحة استثمارية.

## روابط الإنتاج

- **الداشبورد:** https://egx-smart-trader-dashboard.vercel.app
- **API:** https://egx-smart-trader-dashboard.vercel.app/api/recommendations ويتطلب جلسة الدخول المشتركة.
- **المستودع:** `mohammed252832/egx-smart-trader-dashboard`.
- **محرك التحليل:** GitHub Actions على المستودع نفسه (الأحد–الخميس 13:30 UTC، بعد إغلاق السوق بتوقيت القاهرة).
- الدخول بكلمة مرور مشتركة عبر حساب Supabase داخلي واحد؛ لا يوجد تسجيل عام. النشر يتم من الفرع `main` عبر ربط Vercel بالمستودع.

## المعمارية

```
مصادر البيانات (Yahoo .CA / EGID / Borsa / OANOR / EGX.news / CSV)
        ↓  Python + Pandas + XGBoost  (GitHub Actions cron, post-close)
     Supabase (Postgres)
        ↓  authenticated member only (publishable key + RLS)
   Next.js Dashboard على Vercel
```

- **Vercel** يستضيف الواجهة فقط؛ لا يشغّل Python.
- **GitHub Actions** يشغّل محرك Python بعد إغلاق السوق، ويفشل بوضوح عند غياب البيانات أو قلة السهم المؤهلة.
- الواجهة تقرأ من Supabase عبر مفتاح `sb_publishable_...` فقط بعد التحقق من جلسة Supabase ودور `member` للحساب الداخلي المشترك. RLS يتحقق أيضاً من وجود المستخدم والجلسة في قاعدة البيانات. لا توجد بيانات تجريبية؛ إذا تعذّر القراءة تظهر حالة فارغة وتنبيه وضوح.
- `proxy.ts` يجدد كوكيز الجلسة ويحمي الصفحات وAPI قبل rendering، بينما تبقى صفحات لوحة التحميل محمية بتحقق مستقل على الخادم.

## محتويات المشروع

| المسار | الوصف |
| --- | --- |
| `app/(dashboard)/` | لوحة التوصيات، قائمة السوق، اختيار الأسهم، وصفحة الرسم الشهري |
| `app/sidebar.tsx` | القائمة الجانبية العائمة: الرئيسية، السوق، الرسوم الشهرية، وتسجيل الخروج |
| `app/login/` و`app/auth/` | الدخول بكلمة المرور المشتركة والخروج |
| `proxy.ts` | تجديد جلسة Supabase وحماية المسارات الخاصة |
| `app/api/recommendations/route.ts` | JSON API محمي بجلسة حساب معتمد |
| `lib/market-data.ts` | قراءة أعلى الأسهم سيولة والبيانات الشهرية الحقيقية |
| `supabase/schema.sql` | الجداول، العروض، قائمة الحسابات، وسياسات RLS الخاصة |
| `supabase/migrations/20261125225651_market_auth_views.sql` | ترحيل حماية البيانات وعروض السوق والرسوم الشهرية |
| `supabase/migrations/20261127005539_shared_password_account.sql` | إضافة الحساب الداخلي المشترك |
| `supabase/migrations/20261127011012_remove_legacy_dashboard_accounts.sql` | إزالة الحسابات الثلاثة القديمة بعد التحقق |
| `engine/` | محرك التحليل بلغة Python |
| `engine/providers/` | موائمات المصادر الحقيقية (HTTP / CSV) |
| `.github/workflows/analyze.yml` | تشغيل محرك التحليل وكتابة النتائج في Supabase |
| `.github/workflows/refresh.yml` | تحديث الأسعار المتأخرة كل 10 دقائق |
| `.github/workflows/provision-accounts.yml` | إعداد الحساب المشترك وحذف الحسابات القديمة عند تفعيل الخيار |
| `.github/workflows/deploy.yml` | تشغيل نشر الداشبورد على Vercel |

## 1) إعداد Supabase

1. في مشروع قائم، شغّل ترحيلات Supabase بالترتيب في **SQL Editor** بعد مراجعة الفروقات. أضف الحساب المشترك أولاً، ثم طبّق `20261127011012_remove_legacy_dashboard_accounts.sql` بعد التحقق من الدخول. لا تعدّل الجداول يدوياً خارج ملفات الترحيل، ولا تحذف بيانات الإنتاج.
2. في تثبيت جديد فقط، يحتوي `supabase/schema.sql` على الجداول والعروض وسياسات RLS الخاصة المحدثة.
3. من **Project Settings** خذ:
   - **General → Project URL** → `https://xxxx.supabase.co` (لـ Vercel + GitHub).
   - **API Keys → Publishable key** → يبدأ بـ `sb_publishable_...` (للواجهة فقط).
   - **API Keys → Secret key** → يبدأ بـ `sb_secret_...` (لـ GitHub Actions فقط). **لا** تضعه في Vercel ولا تسبقه بـ `NEXT_PUBLIC_`.

> لا يستخدم الكود مفاتيح `anon` / `service_role` القديمة. الترحيل يبقي `private.allowed_accounts` محصوراً في حساب Supabase داخلي واحد بدور `member`، ويمنع التسجيل العام وتغيير البريد، ويقيّد القراءة بجلسة موجودة فعلاً.

الجداول: `stocks`, `price_bars`, `analysis_runs`, `recommendations`, `recommendation_outcomes`, `data_source_status`, `live_quotes`. العروض: `top_recommendations`, `market_daily_bars`, `latest_market`, `monthly_price_bars`.

## 2) إعداد Vercel

أضف المتغيرات التالية في **Project → Settings → Environment Variables**:

```
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
NEXT_PUBLIC_SITE_URL=https://egx-smart-trader-dashboard.vercel.app
```

`NEXT_PUBLIC_SITE_URL` هو النطاق الرسمي بدون مسار أو `/` نهائية، ويُستخدم في روابط استعادة كلمة المرور. في التطوير المحلي استخدم `http://localhost:3000`. ثم أعد النشر. إذا لم تضاف الإعدادات، ستظهر رسالة خطأ واضحة بدلاً من روابط استعادة غير آمنة. احذف المتغير القديم `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

## 3) إعداد GitHub Secrets

في **Repo → Settings → Secrets and variables → Actions** أضف:

```
SUPABASE_URL
SUPABASE_SECRET_KEY           # sb_secret_... — استبدل الاسم القديم SUPABASE_SERVICE_ROLE_KEY
DASHBOARD_SHARED_PASSWORD     # كلمة مرور الدخول المشتركة — GitHub Secret فقط
EGX_YAHOO_ENABLED=true
EGX_BORSA_ENABLED=true
EGX_HISTORY_DAYS=400
EGX_HORIZON_DAYS=3
EGX_TOP_N=10
EGX_MARKET_UNIVERSE_SIZE=250
EGX_MODEL_VERSION=xgboost-v1
VERCEL_DEPLOY_HOOK          # اختياري؛ النشر التلقائي من GitHub يكفي بدون هذا الـhook
```

> لم يعد `EGX_USE_SAMPLE` موجوداً؛ البيانات التجريبية غير مستخدمة في الإنتاج. حدّد القائمة والحدود في `engine/config/universe.json` أو اضبط `EGX_UNIVERSE_CONFIG`.

### البيانات الحقيقية (موصى بها، بلا مفتاح API)

بعد البحث في المصادر تبيّن أن:

- [الموقع الرسمي للبورصة المصرية EGID](https://www.egidegypt.com/index.html) هو المرجع الرسمي. صفحة الأسعار العامة تستدعي `https://feed.egitdns.net/api/DelayedFeed/getTickerInfo` بدون بيانات دخول؛ تحققنا أثناء جلسة 2026-11-26 من 235 سهماً فردياً مع `LAST_TRADE_DATE` وأسعار الافتتاح والأعلى والأدنى والإغلاق والحجم وقيمة التداول. يُفسَّر التاريخ والوقت بتوقيت القاهرة.
- قائمة الرموز العامة متاحة أيضاً من `https://ticker.egidegypt.com/api/Feed/GetAllMarketWatchNames` (308 رموزاً بصيغة Reuters `.CA`). endpoints الخاصة بـ Delayed Feed في Swagger تتطلب Bearer token من `/api/Settings/GetToken` (بيانات دخول EGID).
- صفحة `https://egx.com.eg/en/infograph.aspx` محمية بتحدّي F5 ولا تعرض JSON يمكن استخدامه مباشرة.
- Yahoo Finance يوفّر شموعاً يومية حقيقية لرموز EGX بصيغة `.CA` (مثل `FWRY.CA`) بدون مفتاح.

لذلك اضبط في GitHub Secrets (أو `.env` محلياً):

```
EGID_PUBLIC_ENABLED=true
EGID_PUBLIC_TICKER_URL=https://feed.egitdns.net/api/DelayedFeed/getTickerInfo
EGID_PUBLIC_DELAY_SECONDS=900
EGX_YAHOO_ENABLED=true
EGX_YAHOO_RANGE=2y
EGX_YAHOO_UNIVERSE_URL=https://ticker.egidegypt.com/api/Feed/GetAllMarketWatchNames
```

قائمة الرموز والسيولة والحدود موجودة الآن في `engine/config/universe.json` (لا في الكود). القائمة مشتقة من قائمة EGID العامة وتضم 306 رموزاً بتاريخ 2026-11-25؛ Yahoo لا يغطي كل الرموز بنفس العمق، لذلك يُسجّل المحرك عدد المطلوب والمتاح والمؤهل بعد فلاتر الجودة والسيولة. المصدر يظهر في Supabase باسم `yahoo`، وعدد الصفوف يُسجّل في `data_source_status`.

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

### تحديث الأسعار كل 10 دقائق

- المصدر الأول المجاني هو صفحة الأسعار الرسمية العامة من EGID، بدون مفتاح، للأسهم المتابعة فقط. يُسجّل باسم `egid_public_delayed` وبتأخير افتراضي 15 دقيقة (`EGID_PUBLIC_DELAY_SECONDS=900`). قد يعيد endpoint قائمة فارغة خارج جلسة التداول، ولا نعتبره تحديثاً لحظياً أو نضمن تغطيته لكل الرموز.
- EGID المرخّص له الأولوية عند إضافة `EGID_USERNAME` و`EGID_PASSWORD` في GitHub Actions Secrets، ويُسجّل باسم `egid_delayed`. `EGID_BASE_URL=https://ticker.egidegypt.com` و`EGID_DELAY_SECONDS=900` هما الافتراضييان. لا تُخزَّن بيانات الدخول في المستودع أو الواجهة.
- عند تعذّر EGID أو نقص رموز منه، يكمل المحرك من [TradingView public EGX scanner](https://www.tradingview.com/) ثم Yahoo Finance، مع حفظ مصدر وتاريخ كل سهم على حدة. TradingView عام وغير رسمي، بلا ضمان خدمة أو SLA. Yahoo يظهر بوضوح كـ **آخر إغلاق يومي** وليس كتحديث أثناء الجلسة، ويظل أيضاً مصدر التاريخ اليومي للتحليل.
- الرموز هي أعلى `EGX_MARKET_UNIVERSE_SIZE` سهماً نشطةً في آخر جلسة متاحة، حسب وسيط قيمة تداول آخر 20 جلسة من عرض `latest_market` (الافتراضي 250)؛ وقبل إنشاء العرض تُستخدم أول رموز قائمة التحليل في `engine/config/universe.json`.
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

### الدخول المشترك

صفحة الدخول تطلب كلمة المرور فقط، وتستخدم حساب Supabase داخلياً واحداً بدور `member`. كلمة المرور نفسها لا تُخزَّن في الكود أو متغيرات Vercel؛ تُحفظ كـ hash داخل Supabase Auth، ويُضبطها GitHub Actions من سر `DASHBOARD_SHARED_PASSWORD`.

1. شغّل ترحيل `20261127005539_shared_password_account.sql` أولاً.
2. من **Actions → Configure shared dashboard access → Run workflow** اضبط الحساب المشترك وكلمة المرور مع إبقاء خياري الحذف والتحقق من الموقع متوقفين. يتأكد الـ workflow من نجاح الدخول إلى Supabase قبل متابعة أي خطوة.
3. بعد نجاح تهيئة الحساب، انشر واجهة الدخول الجديدة، ثم شغّل الـ workflow مرة أخرى مع تفعيل **Verify shared password login against the deployed dashboard** وإبقاء الحذف متوقفاً.
4. فقط بعد نجاح التحقق من الموقع، طبّق ترحيل `20261127011012_remove_legacy_dashboard_accounts.sql`، ثم شغّل الـ workflow مع تفعيل التحقق من الموقع و**Delete the three legacy dashboard accounts**.
5. أي شخص يملك كلمة المرور يمكنه الدخول. لا توجد استعادة كلمة مرور بالبريد ولا يمكن للمستخدم المشترك تغيير كلمة المرور من داخل الموقع.

### قائمة السوق والرسوم الشهرية

- `/market` يعرض حتى 250 سهماً حقيقياً نشطاً في آخر جلسة متاحة، مرتبة حسب وسيط قيمة تداول آخر 20 جلسة، مع إظهار العدد الفعلي المتاح ومصدر وتاريخ كل سعر. لا يُملأ النقص بأسعار تقديرية، وإغلاق اليوم يتقدم على أي سعر متأخر من اليوم نفسه.
- `/stocks/[symbol]` يجمع الشموع اليومية الحقيقية في أشهر، مع تفضيل `aggregated` ثم `yahoo`. يظهر آخر 36 شهراً متاحاً، ويمكن أن يكون الشهر الأخير جزئياً.
- **حد الأمان** = `2P − H` للشهر السابق، أي دعم S1. **حد الخطر** = `2P − L` للشهر السابق، أي مقاومة R1، حيث `P = (H + L + C) / 3`. لا تظهر المستويات إلا إذا كان الشهر السابق مباشرةً موجوداً؛ وهما إرشاديان وليسا وقف خسارة أو هدفاً مضموناً.
- يشغّل التحليل الكامل تخزين التاريخ المجمّع للأسهم كلها حتى لو لم توجد جلسة جديدة، كي تظهر الرسوم للأسهم التي انضم حديثاً إلى قائمة السيولة.

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

مستودع الإنتاج هو `https://github.com/mohammed252832/egx-smart-trader-dashboard`. اعمل على فرع مخصص، راجع الفروقات، ثم ادمجها في `main` بدون force-push:

```bash
git switch -c feat/market-sidebar-auth-live
git push -u origin feat/market-sidebar-auth-live
```

بعد الدفع إلى `main` ينشر Vercel الواجهة، ويستمر cron في تشغيل `python -m engine.run` يومياً (الأحد–الخميس). يمكنك تجربة التحليل وتحديث الأسعار وإنشاء الحسابات فوراً من أزرار **Run workflow** في تبويب Actions.

## Phase 1 notes (English)

- Scheduler: `30 13 * * 0-4` UTC (15:30 EET / 16:30 EEST, after the 14:30 Cairo close). GitHub cron cannot follow DST; the later summer offset is intentional.
- A run with no new market date is recorded as `skipped` and does not publish duplicate recommendations, but it still persists newly collected aggregated history for the expanded market universe.
- Raw bars are quality-checked before persistence; symbols need `quality.min_history_bars` and minimum 20-session median traded value from `engine/config/universe.json`.
- "Stocks scanned" now comes from `analysis_runs.universe_size`. The dashboard shows last successful run time, market date, and a stale-data banner.
- Manual steps after merging: set `NEXT_PUBLIC_SITE_URL`, apply `supabase/migrations/20261125225651_market_auth_views.sql`, run the account-provisioning workflow, then redeploy Vercel and run the analysis and quote-refresh workflows once.

## Phase 2 notes (English)

- All signal, risk, tick-size and scoring thresholds live in `engine/config/signals.json`; `EGX_TARGET_PCT` and the old ATR env vars are no longer used.
- Targets and stops use per-stock ATR plus recent support/resistance, capped by configured upside/stop limits, the EGX ±10% daily price limit and tick sizes.
- Signals are `شراء قوي / شراء / مراقبة / تجنّب`; the raw model probability is stored in `recommendations.probability` and shown in the dashboard.
- Model validation uses a chronological split with a purge window around the boundary. Precision, recall and buy hit rate are written to `docs/MODEL_REPORT.md` on every successful run.
- Existing installations must also have `supabase/migrations/0002_phase2_signals.sql` applied before running the current engine.
