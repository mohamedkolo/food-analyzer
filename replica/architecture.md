# Architecture — إضافة الحجز والمتابعة على NutraX

تاريخ: 2026-11-10. يقرأ `replica/recon.md` و`replica/features.csv`، وكود الريبو `mohamedkolo/food-analyzer` (NutraX).

## القرار الأساسي: لا نبني تطبيق جديد

NutraX فيه بالفعل أغلب ما في خريطة الـ recon. بناء تطبيق تاني من الصفر = تكرار شهور شغل وقاعدتين بيانات للعملاء. الخطة: **نكمّل الناقص داخل NutraX** بنفس تقنياته وأسلوبه.

### موجود بالفعل في NutraX (لا يُعاد بناؤه)

| من الـ recon | الموجود | الملفات/المسارات |
| --- | --- | --- |
| حسابات العملاء + تسجيل/دخول + أدوار | users (role: client / nutritionist / admin) | `/register` `/login` `core.py` |
| قائمة العملاء وملف العميل | patients, plan_visits, followups | `/patients` `/followups` `/admin/users/<id>` |
| محرّر خطة الوجبات + توليد أسبوعي + PDF | plan_engine, meal_database | `/generate` `/planner` `/edit_meal` `/swap_meal` |
| العميل يشوف خطته | my-plan + روابط عامة | `/my-plan` `/p/<token>` |
| تعليم الوجبة كمنفّذة | meal_checks | `/track/meal` |
| تسجيل الوزن | weight_log | `/log_weight` |
| شات عميل ↔ أخصائي | messages | `/messages` |
| تذكير الوجبات + Push | push_subscriptions, meal_reminders_sent | `push.py` `notifications.py` |
| قائمة التسوق | shopping_list | `/shopping` |
| الدفع | Stripe + تفعيل يدوي (InstaPay) | `payments.py` `routes_billing.py` `/admin/users/<id>/manual-activate` |
| طلبات بقبول/رفض | plan_requests | `/request-plan` `/admin/requests` |
| عربي RTL + إنجليزي | meal_i18n, `/lang/<l>` | |

### الناقص (ده اللي هيتبني)

| # | الميزة | الأولوية | شاشات الـ recon |
| --- | --- | --- | --- |
| 1 | **حجز استشارة أونلاين**: خدمات، ساعات عمل، مواعيد متاحة، طلب حجز، قبول/رفض | must | S01 S04 S20 S21 |
| 2 | **رابط جلسة (Google Meet) على الموعد** + ظهور الموعد القادم للعميل | must | S05 S20 |
| 3 | **دفع الاستشارة**: InstaPay/تحويل بتأكيد يدوي أولًا، ثم بوابة دفع | must | S03 S29 |
| 4 | تذكير بالموعد (Push + إيميل) | should | F10 |
| 5 | تأجيل/إلغاء من العميل | should | S05 |
| 6 | يوميات: تعليق وصورة على الوجبة | should | S11 |
| 7 | صور في الشات | should | S17 |
| 8 | سجل المياه + هدف | could | S12 |
| 9 | تقييم الاستشارة | could | S18 |
| 10 | صلاحيات لكل عميل | could | S28 |

## 1. التقنيات (Stack)

نفس الموجود، بلا إضافات:

| الطبقة | الاختيار | ليه |
| --- | --- | --- |
| التطبيق | Flask + Jinja | الموجود؛ 740 اختبار عليه |
| القاعدة | Postgres (Neon) في النشر، SQLite محليًا | الموجود؛ كل جدول يُعرّف بالصيغتين في `core.py` |
| الدخول | جلسات Flask الحالية + flask-wtf (CSRF) | الموجود |
| الدفع | التفعيل اليدوي الحالي (InstaPay) → بوابة لاحقًا | Stripe لا يُعتمد عليه لعملاء مصر — to verify |
| الإشعارات | pywebpush + SMTP الحاليين | الموجود |
| الفيديو | رابط Google Meet يلصقه الأخصائي | لا نبني خدمة مكالمات |
| النشر | Render + gunicorn (worker واحد) | الموجود |

## 2. الجداول الجديدة

بأسلوب الريبو: `CREATE TABLE IF NOT EXISTS`، مفاتيح INTEGER، نسختان (Postgres: `SERIAL PRIMARY KEY` / SQLite: `INTEGER PRIMARY KEY AUTOINCREMENT`). المعروض صيغة Postgres. الأوقات تُخزَّن **UTC**. المبالغ **بالقرش** (integer) + عملة.

```sql
CREATE TABLE IF NOT EXISTS services (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  duration_min INTEGER NOT NULL,
  price INTEGER NOT NULL DEFAULT 0,          -- بالقرش
  currency TEXT NOT NULL DEFAULT 'EGP',
  is_online INTEGER NOT NULL DEFAULT 1,
  active INTEGER NOT NULL DEFAULT 1,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS availability (
  id SERIAL PRIMARY KEY,
  weekday INTEGER NOT NULL,                   -- 0 = الاثنين … 6 = الأحد
  start_min INTEGER NOT NULL,                 -- دقائق من منتصف الليل بتوقيت الأخصائي
  end_min INTEGER NOT NULL,
  CHECK (end_min > start_min)
);

CREATE TABLE IF NOT EXISTS availability_blocks (  -- إجازات / أوقات مقفولة
  id SERIAL PRIMARY KEY,
  start_at TIMESTAMP NOT NULL,
  end_at TIMESTAMP NOT NULL,
  reason TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
  id SERIAL PRIMARY KEY,
  client_id INTEGER NOT NULL,                 -- users.id
  service_id INTEGER NOT NULL,                -- services.id
  start_at TIMESTAMP NOT NULL,                -- UTC
  end_at TIMESTAMP NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',     -- pending | accepted | rejected | expired | cancelled | completed | no_show
  slot_key TEXT,                              -- start_at كنص؛ NULL لما الموعد يتلغي/يترفض
  video_url TEXT,
  client_note TEXT,
  admin_note TEXT,
  price INTEGER NOT NULL DEFAULT 0,           -- نسخة من سعر الخدمة وقت الحجز
  currency TEXT NOT NULL DEFAULT 'EGP',
  pay_status TEXT NOT NULL DEFAULT 'unpaid',  -- unpaid | claimed | paid | refunded
  pay_method TEXT,                            -- instapay | wallet | gateway
  pay_ref TEXT,                               -- رقم العملية اللي العميل كتبه
  reminder_sent INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (slot_key)
);
CREATE INDEX IF NOT EXISTS idx_appt_client ON appointments (client_id, start_at);
CREATE INDEX IF NOT EXISTS idx_appt_start ON appointments (start_at);

-- مرحلة 2
CREATE TABLE IF NOT EXISTS appointment_ratings (
  id SERIAL PRIMARY KEY,
  appointment_id INTEGER NOT NULL UNIQUE,
  score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 10),
  comment TEXT,
  anonymous INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS water_log (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  amount_ml INTEGER NOT NULL,
  logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_water_user ON water_log (user_id, logged_at);
```

تعديلات أعمدة (بنفس أسلوب `ALTER TABLE … ADD COLUMN` في `core.py`):

```sql
ALTER TABLE meal_checks ADD COLUMN comment TEXT;
ALTER TABLE meal_checks ADD COLUMN photo_path TEXT;
ALTER TABLE messages ADD COLUMN image_path TEXT;
ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Africa/Cairo';
```

**منع الحجز المزدوج:** `UNIQUE (slot_key)`. الموعد النشط (pending/accepted) بياخد `slot_key = start_at`؛ عند الرفض/الإلغاء/الانتهاء يتحوّل `NULL` فيتفتح الموعد تاني. القيد شغال في Postgres و SQLite. الإدراج المتعارض يرجّع "الموعد اتحجز، اختار غيره". (المدد كلها مضاعفات شبكة واحدة — 30 دقيقة — فالتداخل الجزئي ممنوع من توليد المواعيد نفسه.)

**الصلاحيات:** فحص في كل route بالحارس الحالي: العميل لا يقرأ ولا يعدّل إلا `client_id = session uid`؛ الإدارة للأدوار admin/nutritionist. اختبار: عميل ثاني لا يرى موعد الأول.

## 3. المسارات (ملف جديد `routes_booking.py`)

| method path | بيعمل إيه | مين | المسار |
| --- | --- | --- | --- |
| GET `/book` | صفحة الحجز: الخدمات + الأيام + المواعيد المتاحة بتوقيت العميل | عام | F01 |
| GET `/book/slots?service=&date=` | JSON بالمواعيد المتاحة ليوم | عام | F01 |
| POST `/book` | إنشاء طلب (pending). يطلب دخول/تسجيل أولًا | عميل | F01 |
| GET `/book/<id>` | حالة الطلب + تعليمات الدفع + رابط الجلسة لما يتقبل | صاحب الموعد | F01 F03 |
| POST `/book/<id>/paid` | العميل يكتب رقم عملية التحويل → pay_status=claimed | صاحب الموعد | F01 |
| POST `/book/<id>/cancel` | إلغاء (قبل الموعد بمدة محددة) | صاحب الموعد | F03 |
| POST `/book/<id>/reschedule` | اختيار موعد جديد → يرجع pending | صاحب الموعد | F03 |
| GET `/admin/calendar` | مواعيد الأسبوع + الطلبات المعلّقة + رابط الحجز | إدارة | F02 |
| POST `/admin/appointments/<id>/accept` | قبول + رابط Meet | إدارة | F02 |
| POST `/admin/appointments/<id>/reject` | رفض + سبب | إدارة | F02 |
| POST `/admin/appointments/<id>/confirm-payment` | تأكيد استلام التحويل → paid | إدارة | F02 |
| POST `/admin/appointments/<id>/status/<s>` | completed / no_show | إدارة | F03 |
| POST `/admin/appointments/new` | حجز يدوي لعميل | إدارة | F02 |
| GET/POST `/admin/booking-settings` | الخدمات، ساعات العمل، الإجازات، بيانات InstaPay | إدارة | — |

**مهام مجدولة** (بنفس آلية تذكير الوجبات الحالية، تُراجع في `notifications.py`): تذكير قبل الموعد بـ 24 ساعة وبساعة؛ تحويل الطلبات pending الأقدم من 48 ساعة إلى expired وفتح الموعد.

**ربط بالموجود:** كارت "موعدك القادم" في `/dashboard` و`/my-plan`؛ إشعار للأدمن عند كل طلب (جدول notifications الحالي)؛ رسالة آلية في `/messages` عند القبول/الرفض.

## 4. الأجزاء اللي بتلسع

- **التوقيت:** الأخصائي بتوقيت دبي (UTC+4، بلا توقيت صيفي) والعملاء بتوقيت القاهرة (فيه توقيت صيفي). التخزين UTC، العرض بـ `zoneinfo` حسب `users.timezone`؛ صفحة الحجز تكتب "المواعيد بتوقيت القاهرة" صراحة.
- **السباق على الموعد:** يحسمه قيد UNIQUE، مش الواجهة.
- **الدفع اليدوي:** claimed ≠ paid. الموعد لا يتأكد كمدفوع إلا بتأكيد الأدمن. الاسترداد يدوي ويتسجّل.
- **قاعدة `/health`:** لا تلمس القاعدة (README بند 1). المهام المجدولة لا تُربط بالـ ping.
- **حصة Neon/Render:** لا polling دوري من الواجهة للتقويم.
- **رفع الصور (مرحلة 2):** قرص Render المجاني مؤقت → تخزين خارجي (R2/Supabase Storage)، حد حجم ونوع.
- **بيانات صحية:** لا بيانات عملاء في الريبو (README بند 6)؛ تحديث `/privacy` بذكر المواعيد والدفع.
- **worker واحد:** لا حالة في الذاكرة بين الطلبات.

## 5. ترتيب البناء

1. **الشريحة الأولى (M1):** جداول services/availability/appointments + `/admin/booking-settings` + `/book` + `/book/<id>` + `/admin/calendar` بقبول/رفض ورابط Meet. اختبارات: توليد المواعيد، الحجز المزدوج، التوقيت، الصلاحيات.
2. **M2 الدفع:** تعليمات InstaPay + `/book/<id>/paid` + تأكيد الأدمن + ظهورها في `/admin/payments`.
3. **M3 الربط:** كارت الموعد القادم، إشعارات الأدمن، رسائل آلية، تذكيرات، انتهاء الطلبات.
4. **M4:** إلغاء/تأجيل من العميل، الإجازات، الحجز اليدوي.
5. **M5 (should/could):** تعليق وصورة على الوجبة، صور الشات، سجل المياه، التقييم.
6. **بعدها:** إصلاحات replica-entrepreneur.

كل الشغل على فرع `booking`، وكل مرحلة Pull Request منفصل؛ لا دمج في `main` إلا بعد نجاح `python3 tests/run_all.py`.

## الملخص

- **Stack:** Flask + Jinja + Postgres/SQLite (الموجود).
- **جداول جديدة:** 4 أساسية + 2 مرحلة ثانية + 4 أعمدة.
- **مسارات جديدة:** 14.
- **أخطر 3:** التوقيت، الدفع اليدوي والاسترداد، التذكيرات على استضافة مجانية بتنام.
- **التالي:** `/replica-design` غير مطلوب (التصميم الحالي يُستخدم كما هو) → مباشرة `/replica-build` لـ M1.
