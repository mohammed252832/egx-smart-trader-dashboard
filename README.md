# EGX Smart Trader

محلل ذكي لأسهم البورصة المصرية (EGX) يهدف لاكتشاف أفضل فرص التداول قصيرة الأجل (2–3 أيام)، مع تحديد سعر الدخول والهدف ووقف الخسارة، وتقييم دقة التوصيات تلقائياً بعد انتهاء فترة الاحتفاظ.

> ⚠️ الأداة لأغراض البحث والتحليل فقط، وليست نصيحة استثمارية.

## المعمارية

```
مصادر البيانات (EGX / EGID / DataCedar / Borsa / CSV / Sample)
        ↓  Python + Pandas + XGBoost  (GitHub Actions cron)
     Supabase (Postgres)
        ↓  read-only (anon key + RLS)
   Next.js Dashboard على Vercel
```

- **Vercel** يستضيف الواجهة فقط؛ لا يشغّل Python.
- **GitHub Actions** يشغّل محرك Python بشكل دوري ويكتب النتائج في Supabase.
- الواجهة تقرأ من Supabase عبر مفتاح `anon` للقراءة فقط، وتعرض بيانات تجريبية تلقائياً إذا لم يتم ضبط المتغيرات.

## محتويات المشروع

| المسار | الوصف |
| --- | --- |
| `app/page.tsx` | لوحة التوصيات (أفضل 10 فرص) |
| `app/api/recommendations/route.ts` | JSON API للوحة |
| `lib/data.ts` | طبقة قراءة م cache + بيانات تجريبية احتياطية |
| `supabase/schema.sql` | الجداول، الـ view، وسياسات RLS |
| `engine/` | محرك التحليل بلغة Python |
| `engine/providers/` | موائمات المصادر (HTTP / CSV / Sample) |
| `.github/workflows/analyze.yml` | جدولة التحليل |

## 1) إعداد Supabase

1. افتح مشروع Supabase.
2. اذهب إلى **SQL Editor** وشغّل محتوى `supabase/schema.sql`.
   - لو ظهر خطأ `column "symbol" referenced in foreign key constraint does not exist`، شغّل أولاً محتوى `supabase/reset.sql` ثم أعد تشغيل `supabase/schema.sql`. الملف ده بيحذف الهياكل القديمة فقط، والمشروع جديد فلاً بيانات مهمة فيه.
3. من **Project Settings** خذ:
   - **General → Project URL** → `https://xxxx.supabase.co` (لـ Vercel + GitHub)
   - **API Keys → Publishable key** → يبدأ بـ `sb_publishable_...` (للواجهة). أو الـ `anon` القديم من **View legacy API keys / JWT Keys**.
   - **API Keys → Secret key** → يبدأ بـ `sb_secret_...` (لـ GitHub Actions فقط). أو الـ `service_role` القديم. **لا** تضعه في Vercel ولا تسبقه بـ `NEXT_PUBLIC_`.

> Supabase غيّر الأسماء: Publishable = anon، و Secret = service_role. الاتنين شغالين مع الكود من غير تعديل.

الجداول التي تنشئها: `stocks`, `price_bars`, `analysis_runs`, `recommendations`, `recommendation_outcomes`, `data_source_status`، plus view اسمه `top_recommendations` يرجع أفضل 10 من آخر تشغيل ناجح.

## 2) إعداد Vercel

أضف متغيرين في **Project → Settings → Environment Variables**:

```
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

ثم أعد النشر. إذا لم يضيفا، ستظهر رسالة «بيانات تجريبية» أعلى اللوحة.

## 3) إعداد GitHub Secrets

في **Repo → Settings → Secrets and variables → Actions** أضف:

```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
EGX_USE_SAMPLE=true          # اتركها true حتى تربط مصادر حقيقية
EGX_HISTORY_DAYS=400
EGX_HORIZON_DAYS=3
EGX_TOP_N=10
EGX_MODEL_VERSION=xgboost-v1
```

ولكل مزود حقيقي (اختياري) أضف الثلاثة:

```
DATACEDAR_API_KEY / DATACEDAR_UNIVERSE_URL / DATACEDAR_HISTORY_URL
EGID_API_KEY      / EGID_UNIVERSE_URL      / EGID_HISTORY_URL
BORSA_API_KEY     / BORSA_UNIVERSE_URL     / BORSA_HISTORY_URL
EGX_API_KEY       / EGX_UNIVERSE_URL       / EGX_HISTORY_URL
```

صيغة الروابط تدعم العناصر النائبة `{symbol}` و `{days}` و `{api_key}`، مثال:

```
https://api.example.com/v1/history?symbol={symbol}&days={days}&api_key={api_key}
```

> رخصة EGID/DataCedar تجارية؛ تأكد من شروط الوصول قبل استخدام بياناتها تجارياً.

## 4) التشغيل محلياً

```bash
# واجهة Next.js
npm install
cp .env.example .env      # عدّل القيم
npm run dev

# محرك Python
python -m pip install -r engine/requirements.txt
python -m engine.run
```

المحرك يعمل حتى بدون مفاتيح API بفضل مولّد البيانات التجريبية الحتمي في `engine/providers/sample_provider.py` والقائمة في `engine/sample_data/universe.csv`. عيّن `EGX_USE_SAMPLE=false` بعد تجهيز مصادر حقيقية.

## 5) كيف تُحسب التوصية؟

1. **الجمع:** أسعار يومية من كل المصادر، ثم دمجها ( Median للإغلاق، max للأعلى، min للأدنى ) في سلسلة موحدة لكل سهم.
2. **المؤشرات:** عوائد 1/3/5/10 أيام، SMAs، EMAs، MACD، RSI14، ATR14، Bollinger، حجم التداول، التقلب، وميل الاتجاه.
3. **التنبؤ:** نموذج `XGBClassifier` يتنبأ باحتمال أن يتحقق صعود ≥ `EGX_TARGET_PCT` خلال `EGX_HORIZON_DAYS` جلسات. يتم التدريب على أقدم 80% والتحقق على أحدث 20%.
4. **المخاطرة:** `الدخول = آخر إغلاق`، `الوقف = الدخول - 1.4 × ATR`، `الهدف = الدخول + 2.4 × ATR` (بحد أدنى 2% صعود وبحد أقصى 8% مخاطرة).
5. **الترتيب:** `score = 70 × الاحتمال + 20 × (العائد/المخاطرة) + 10 × زخم الاتجاه`، ثم تُؤخذ أعلى 10.
6. **التقييم:** بعد مرور فترة الاحتفاظ تُقارن الأسعار اللاحقة بالهدف والوقف وتُخزّن النتيجة `win / loss / flat`.

## 6) رفع الكود إلى GitHub

إذا لم يكن الـ remote مضافاً محلياً:

```bash
git remote add origin https://github.com/<USERNAME>/egx-smart-trader.git
git push -u origin master
```

بعد الدفع سيقوم Vercel بنشر الواجهة، وسيبدأ الـ cron بتشغيل `python -m engine.run` يومياً (الأحد–الخميس). يمكنك تجربة التشغيل فوراً من زر **Run workflow** في تبويب Actions.
