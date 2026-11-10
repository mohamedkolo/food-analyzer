# Recon map — تطبيق «كُل بذكاء» (على طريقة Nutrium)

تاريخ القراءة: 2026-11-10. كل المعلومات من مصادر عامة فقط (مركز المساعدة، المدونة، صفحة المتجر، مواقع المراجعات). لم يُستخدم أي حساب ولا كود ولا APIs خاصة.

## 1. النطاق (Scope)

- **الأصل:** Nutrium — برنامج ويب للأخصائي + تطبيق موبايل للعميل.
- **الجزء المطلوب (core loop):** عميل يحجز استشارة ويدفع → الأخصائي يقبل → جلسة أونلاين → الأخصائي يكتب خطة وجبات → العميل يتابعها ويسجّل وجباته ووزنه ويراسل الأخصائي.
- **لمين:** مشروع محمد الشخصي — أخصائي واحد، عملاء في مصر، عربي (RTL).
- **المنصة المقترحة:** ويب متجاوب (mobile-first / PWA) للعميل + لوحة ويب للأخصائي. تطبيقات المتاجر مرحلة لاحقة.
- **خارج النطاق الآن:** تعدد الأخصائيين/العيادات، تحليل غذائي متقدم، قاعدة أطعمة جاهزة، مزامنة Apple Health/Google Fit، تسجيل الوجبات بالذكاء الاصطناعي، مكالمات فيديو داخلية.

## 2. المصادر

| المصدر | الرابط | أعطانا إيه |
| --- | --- | --- |
| مركز المساعدة — مميزات تطبيق العميل | https://help.nutrium.com/en/articles/3372169-what-are-the-features-of-the-nutrium-mobile-app-for-nutrition-clients | قائمة المميزات + صلاحيات كل عميل |
| مركز المساعدة — دليل العميل للتطبيق | https://help.nutrium.com/en/articles/4325678-nutrium-mobile-app-instruction-guide-for-nutrition-clients | كل شاشات تطبيق العميل وحقولها |
| مركز المساعدة — طلب موعد (العميل) | https://intercom.help/nutrium/en/articles/5316857-how-can-i-request-a-nutrition-appointment-through-nutrium | خطوات الحجز، التسجيل، الدفع، حالات الطلب |
| مركز المساعدة — تفعيل الحجز الأونلاين | https://help.nutrium.com/en/articles/3779279-how-to-enable-online-scheduling-and-bookings | إعداد الأخصائي: أماكن العمل، ساعات العمل، رابط الحجز |
| مركز المساعدة — الدفع عند الحجز | https://help.nutrium.com/en/articles/5269057-can-my-clients-make-the-payment-upon-scheduling-an-appointment | الدفع المسبق، قبول/رفض، الرصيد المعلّق |
| مركز المساعدة — مكالمات الفيديو | https://intercom.help/nutrium/en/articles/3871221-how-to-integrate-video-calls-with-nutrium-online-consultations | ربط Google Meet / Zoom ومزامنة التقويم |
| المدونة — الحجز الأونلاين | https://nutrium.com/blog/online-booking-of-nutrition-appointments-in-nutrium/ | شاشة الحجز: المكان، نوع الخدمة، اليوم والساعة |
| المدونة — تطبيق العميل | https://nutrium.com/blog/nutrium-mobile-app-for-nutrition-clients/ | لوحة العميل، إعدادات التطبيق، صلاحيات |
| App Store | https://apps.apple.com/app/nutrium/id1136652584 | وصف التطبيق والمميزات الأساسية |
| GetApp | https://www.getapp.com/nutritionist-software/a/nutrium | قائمة مميزات برنامج الأخصائي، لا يوجد API عام |

**لم يُقرأ بعد (to do):** صفحة الأسعار وصفحة المميزات على nutrium.com (لم تُفتح من هنا)، وفيديوهات الشرح العامة. لقطات الشاشة المرجعية: المستخدم يضيفها في `replica/screens/` من صفحة المتجر.

## 3. جرد الشاشات

### تطبيق العميل

| ID | الشاشة | الوصول | الغرض | المكوّنات | الحالات |
| --- | --- | --- | --- | --- | --- |
| S01 | صفحة الحجز العامة | رابط الحجز | اختيار نوع الخدمة واليوم والساعة | قائمة خدمات (مدة + سعر)، تقويم، شبكة مواعيد | لا مواعيد متاحة، موعد اتحجز أثناء الاختيار |
| S02 | تسجيل / دخول عند الحجز | بعد S01 | عميل جديد يسجّل، قديم يدخل | فورم (اسم، نوع، تاريخ ميلاد، بلد، موبايل، إيميل، كلمة سر)، تبويب "مسجّل بالفعل" | خطأ تحقق، إيميل مستخدم |
| S03 | الدفع | بعد S02 لو الدفع المسبق مفعّل | دفع قيمة الاستشارة | ملخص الطلب، وسيلة الدفع | فشل الدفع، نجاح |
| S04 | تأكيد الطلب | بعد S03/S02 | يوضح إن الطلب في انتظار قبول الأخصائي | رسالة حالة | pending / accepted / rejected / expired |
| S05 | الرئيسية | أول أيقونة في القائمة السفلية | نظرة يومية | آخر وجبات اليوميات بحالة ملوّنة، تقدّم المياه، ملخص النشاط، الموعد القادم (تأجيل/إلغاء)، كارت تقييم، أيقونة رسائل بعدّاد | فاضية (مفيش خطة)، مفيش موعد |
| S06 | خطة الوجبات | القائمة السفلية | عرض الخطة وجبة وجبة، خطط مختلفة لأيام مختلفة | تبويب أيام، كروت وجبات، روابط وصفات، تذكير بالوجبات | مفيش خطة منشورة |
| S07 | التسجيل السريع (+) | زر وسط القائمة | مياه / وزن / نشاط / رسالة من أي شاشة | Bottom sheet بأربع اختيارات | — |
| S08 | التوصيات والأهداف | القائمة السفلية | أهداف، أطعمة تُتجنب، ملاحظات الأخصائي | قوائم نصية | فاضية |
| S09 | المزيد | القائمة السفلية | باقي الشاشات | قائمة روابط | — |
| S10 | يوميات الأكل | S09 أو S05 | وجبات اليوم وحالتها، أيام سابقة، إضافة وجبة خارج الخطة | تنقل بين الأيام، كروت وجبات، زر + | يوم فاضي |
| S11 | تفاصيل وجبة في اليوميات | S10 | تعديل: لم يؤكل، رجوع للأصل، إضافة طعام، تغيير الوقت، صورة وتعليق | قائمة أطعمة، بحث طعام + كمية، رفع صورة | — |
| S12 | سجل المياه | S09 / S07 | إضافة كوب 200 مل / زجاجة 500 مل / كمية مخصصة، تذكير | أزرار سريعة، فورم مخصص، جرس | الهدف اتحقق |
| S13 | القياسات والوزن | S09 / S07 | رسم تقدّم الوزن، إضافة قراءة (وزن + تاريخ) | رسم خطي، قائمة قراءات، فورم | مفيش قراءات |
| S14 | النشاط البدني | S09 / S07 | ملخص أسبوعي، إضافة تمرين (نشاط، تاريخ، مدة، طاقة، مسافة) | كروت إحصائية، فورم | فاضي |
| S15 | الوصفات | S06 / S09 | مكونات وخطوات الوصفات الموجودة في الخطة | قائمة + تفاصيل | فاضية |
| S16 | قوائم التسوق | S09 | قائمة تلقائية من الخطة لعدد أسابيع، أو يدوية؛ تعديل/حذف/تكرار | قوائم، عناصر، قائمة ⋯ | فاضية |
| S17 | الرسائل | S05 / S09 / S07 | شات مع الأخصائي + صور؛ رسائل آلية عند تغيير الخطة/الموعد | فقاعات، إرفاق صورة، عدّاد غير مقروء | مفيش رسائل، الشات مقفول للعميل |
| S18 | تقييم الاستشارة | كارت في S05 | تقييم 1–10 + محاور، ممكن مجهول | مقياس، اختيارات، إرسال | — |
| S19 | الإعدادات والملف الشخصي | S09 | صورة وبيانات، تشغيل/إيقاف الإشعارات، أوقات تذكير الوجبات والمياه، الوحدات | مفاتيح، منتقي وقت | — |

### لوحة الأخصائي

| ID | الشاشة | الغرض | الحالات |
| --- | --- | --- | --- |
| S20 | التقويم | مواعيد اليوم/الأسبوع، إنشاء موعد، طلبات الحجز المعلّقة (قبول/رفض)، رابط الحجز | مفيش مواعيد، طلب منتهي |
| S21 | إعداد الحجز | أنواع الخدمات (مدة، سعر)، ساعات العمل، تفعيل الدفع المسبق، رابط فيديو | غير مكتمل الإعداد |
| S22 | قائمة العملاء | بحث وفتح ملف عميل، دعوة عميل للتطبيق | فاضية |
| S23 | ملف العميل | بيانات، تاريخ صحي، قياسات، مواعيد، ملفات مرفقة | — |
| S24 | محرّر خطة الوجبات | وجبات وأوقات، أطعمة وكميات، وصفات، خطط لأيام مختلفة، نشر للعميل | مسودة / منشورة |
| S25 | التوصيات والأهداف | أهداف (وزن، مياه)، أطعمة تُتجنب، ملاحظات | — |
| S26 | متابعة يوميات العميل | مشاهدة الوجبات المسجّلة والصور والتعليق عليها | مفيش تسجيلات |
| S27 | الرسائل | صندوق محادثات كل العملاء | — |
| S28 | صلاحيات العميل | تشغيل/إيقاف لكل عميل: يوميات، تسجيل وزن، شات، تأكيد المواعيد، معلومات غذائية، تقييم | — |
| S29 | المدفوعات | المدفوعات المستلمة والمعلّقة والمستردة | فاضية |

المجموع: 29 شاشة (19 عميل + 10 أخصائي).

## 4. مسارات المستخدم

```
F01 عميل جديد يحجز ويدفع
    S01 → S02 → S03 → S04
    edge: مفيش مواعيد، الموعد اتاخد أثناء ملء الفورم، فشل الدفع، فرق التوقيت (الأخصائي في الإمارات والعميل في مصر)
    نقرات المسار السعيد: ~8

F02 الأخصائي يقبل/يرفض الطلب
    S20 (طلب معلّق) → قبول | رفض
    edge: رفض أو انتهاء المهلة بعد دفع مسبق → استرداد كامل وإشعار العميل

F03 جلسة أونلاين
    S20 موعد برابط فيديو → العميل يفتح الرابط من S05 أو الإيميل
    edge: العميل ما حضرش، تأجيل/إلغاء من S05

F04 الأخصائي يكتب الخطة وينشرها
    S22 → S23 → S24 → نشر → رسالة آلية في S17 → العميل يشوفها في S06
    edge: خطط مختلفة لأيام مختلفة، تعديل خطة منشورة

F05 العميل يتابع يومه
    S05 → S10 → S11 (كما في الخطة | تخطّي | تعديل + صورة)
    edge: وجبة خارج الخطة، تعديل يوم سابق

F06 تسجيل سريع
    S07 → S12 مياه | S13 وزن | S14 نشاط
    نقرات: 3

F07 شات
    S17 عميل ↔ S27 أخصائي، مع صور
    edge: الشات مقفول للعميل من S28

F08 متابعة التقدّم
    الأخصائي: S23 قياسات + S26 يوميات → تعديل S24/S25
    العميل: S13 رسم الوزن مقابل الهدف

F09 تقييم بعد الجلسة
    S05 كارت → S18 → إرسال (ممكن مجهول)

F10 تذكيرات
    إشعارات وجبات/مياه/موعد حسب إعدادات S19
```

## 5. المكوّنات

| المكوّن | الأشكال | الحالات | يُستخدم في |
| --- | --- | --- | --- |
| Button | primary, secondary, ghost, danger | default, pressed, disabled, loading | الكل |
| Bottom nav + زر (+) وسطي | 5 عناصر | active, badge | S05–S09 |
| Bottom sheet | اختيارات سريعة | open/closed | S07 |
| Meal card | خطة / يوميات | planned, as-planned, skipped, logged | S05, S06, S10 |
| Status chip | ألوان الحالة | pending, accepted, rejected, expired | S04, S20, S29 |
| Date strip / calendar | يوم، أسبوع، شهر | selected, disabled, today | S01, S10, S20 |
| Time-slot grid | — | available, taken, selected | S01 |
| Form inputs | نص، رقم، تاريخ، وقت، select | focus, error, disabled | S02, S12–S14, S21 |
| Search + quantity picker | بحث طعام/نشاط | نتائج، لا نتائج | S11, S14, S24 |
| Progress ring/bar | مياه، هدف الوزن | 0%–100%+ | S05, S12, S13 |
| Line chart | وزن عبر الزمن | فاضي، نقطة واحدة، متعدد | S13, S23 |
| Chat bubbles + مرفق صورة | مرسل/مستقبل/آلي | sending, sent, failed | S17, S27 |
| Toggle list | صلاحيات وإشعارات | on/off | S19, S28 |
| Rating scale 1–10 | — | selected | S18 |
| Empty state | لكل قائمة | — | الكل |
| Toast / banner | نجاح، خطأ | — | الكل |
| Table | عملاء، مدفوعات | sort, empty | S22, S29 |

## 6. نموذج البيانات المستنتج

```
User            id, role (professional | client), name, email, phone, password_hash, avatar
                evidence: S02 فورم التسجيل، S19 — confidence: high

ClientProfile   user_id, gender, birth_date, country, timezone, health_notes, goal_weight
                evidence: S02، S23 — confidence: medium (health_notes تخمين)

ClientPermissions  client_id, can_food_diary, can_log_weight, can_chat,
                can_confirm_appointments, show_nutrition_info, can_rate
                evidence: مقال مميزات التطبيق (Deliverables) — confidence: high

Service         id, name, duration_min, price, currency, is_online
                evidence: S01 نوع الخدمة بالمدة والسعر — confidence: high

Availability    id, weekday, start_time, end_time
                evidence: إعداد ساعات العمل — confidence: medium

Appointment     id, client_id, service_id, start_at, end_at,
                status (pending | accepted | rejected | expired | cancelled | completed),
                video_url, created_via (booking_link | professional)
                evidence: حالات الطلب، S20 — confidence: high

Payment         id, appointment_id, amount, currency, provider, provider_ref,
                status (pending | paid | refunded | failed)
                evidence: الدفع المسبق والاسترداد — confidence: medium

MealPlan        id, client_id, title, status (draft | published), published_at
MealPlanDay     id, plan_id, label (أيام مختلفة)
Meal            id, day_id, name, time
MealItem        id, meal_id, food_name, quantity, unit, recipe_id?
                evidence: S06، S11، S24 — confidence: medium

Recipe          id, title, ingredients (json), steps (json)
                evidence: S15 — confidence: medium

Recommendation  id, client_id, type (goal | avoid | note), text; water_goal_ml
                evidence: S08 — confidence: medium

DiaryEntry      id, client_id, date, meal_id?, status (as_planned | skipped | logged),
                items (json), photo_url, comment, time
                evidence: S10، S11 — confidence: high

WaterLog        id, client_id, amount_ml, logged_at            — high
Measurement     id, client_id, type (weight | ...), value, unit, measured_on — high
ActivityLog     id, client_id, activity, date, duration_min, energy, distance — high

ShoppingList    id, client_id, title, source (auto | manual), weeks
ShoppingItem    id, list_id, name, quantity, checked          — medium

Message         id, client_id, sender (client | professional | system), body,
                image_url, read_at, created_at                 — high

Rating          id, appointment_id, score (1–10), aspects (json), anonymous — high

NotificationSettings  client_id, all_on, meals_on, meal_times (json), water_on,
                water_prefs (json), messages_on, units (json)  — high
```

## 7. جدول المميزات

في `replica/features.csv`.

## 8. اللي مش هيتنسخ (skip)

- **قاعدة بيانات الأطعمة والتحليل الغذائي بتاعة Nutrium:** ملكهم. البديل: قائمة أطعمة مصرية يكتبها محمد بنفسه + مصدر مفتوح مرخّص لو لزم.
- **الوصفات والنصوص والأيقونات والاسم:** كلها تتكتب/تتعمل من جديد.
- **شبكة الأخصائيين وصفحات "اعثر على أخصائي":** خارج النطاق.
- **Stripe:** الأصل بيعتمد عليه. يُتحقق أولًا من توفره لنشاط في مصر؛ الأرجح محتاج مزوّد دفع مصري (Paymob / Fawry) أو تحويل يدوي (InstaPay / محفظة) مع تأكيد يدوي — **to verify**.
- **مكالمات فيديو داخلية:** نستخدم رابط Google Meet خارجي بدل بناء خدمة مكالمات.
- **مزامنة Apple Health / Google Fit وتسجيل الوجبات بالـ AI:** مرحلة لاحقة.

## 9. الحجم

- 29 شاشة، 10 مسارات، ~20 كيان.
- **الأجزاء الصعبة:**
  1. الدفع لعملاء مصر + الاسترداد عند الرفض/الانتهاء.
  2. الحجز: فرق التوقيت (الإمارات/مصر)، منع الحجز المزدوج لنفس الموعد.
  3. الإشعارات والتذكيرات (وجبات، مياه، مواعيد) على الويب/الموبايل.
  4. خصوصية البيانات الصحية: صلاحيات صارمة (العميل لا يرى إلا بياناته)، وسياسة خصوصية واضحة.
- **الحجم: M** (أسابيع). الشريحة الأولى (F01 → F02 → F04 → F05) ممكن تشتغل في أسبوع–أسبوعين.
- **ملاحظة تنظيمية:** تقديم استشارات تغذية أونلاين ودفع إلكتروني لهما اشتراطات ترخيص حسب البلد — تُراجع قبل الإطلاق.

## الخطوة الجاية

`/replica-architect`
