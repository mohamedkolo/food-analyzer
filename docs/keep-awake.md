# منع Render من تنييم الموقع

## المشكلة

خطة Render المجانية بتوقف الـ instance بعد حوالي **15 دقيقة** من غير أي trafic.
أول زيارة بعد كده لازم تستنى الكونتينر يقوم من الأول — من **30 لـ 60 ثانية**
والصفحة بتفضل بايظة/بتحمّل. ده سبب إن الموقع "بيفتح بالعافية" لو محدش دخل عليه
من شوية، ودي كمان سبب إن أول تست في أي run على TestSprite بيفشل بـ timeout.

## الحل

في الكود endpoint خفيفة مخصوص للغرض ده:

```
GET https://food-analyzer-duag.onrender.com/health   ->   200 "ok"
```

مش بتفتح الداتابيز ولا بتقرا الـ session — مجرد رد نصي، فمفيش أي حمل عليها.
لو حاجة خارجية بتضربها كل أقل من 15 دقيقة، الـ instance مايناموش أصلاً.

## الإعداد على cron-job.org (مجاني)

1. اعمل حساب على <https://cron-job.org> وأكّد الإيميل.
2. **Create cronjob**.
3. املا الحقول:

   | الحقل | القيمة |
   |---|---|
   | Title | `NutraX keep-awake` |
   | URL | `https://food-analyzer-duag.onrender.com/health` |
   | Schedule | Every 10 minutes |
   | Request method | GET |
   | Enable job | ✅ |

4. من **Advanced**: خلي الـ timeout 30 ثانية، وشيل علامة
   "Notify me when the job fails" لو مش عايز إيميلات كل شوية وقت الـ deploy
   (وقت النشر بيكون فيه فترة قصيرة الموقع فيها نازل).
5. Save. من صفحة الـ job نفسها هتشوف آخر النتائج — لازم تكون كلها 200.

## البديل: UptimeRobot

نفس الفكرة، وبيديك كمان صفحة status ومراقبة uptime:

1. حساب على <https://uptimerobot.com>.
2. **Add New Monitor** → Monitor type: **HTTP(s)**.
3. Friendly name: `NutraX` — URL: `https://food-analyzer-duag.onrender.com/health`
4. Monitoring interval: **5 minutes** (أقل حد في الخطة المجانية، وكفاية جداً).
5. Create Monitor.

## ملاحظة

ده workaround لخطة مجانية، مش حل نهائي. لو الموقع بقى عليه عملاء فعليين،
خطة Render المدفوعة مفيهاش spin-down من أصله والموضوع بيبقى أنضف —
ساعتها الـ ping ده يبقى مراقبة uptime بس مش ضرورة.

## لو غيّرت الدومين

الـ URL فوق هو دومين Render الافتراضي. لو ربطت دومين خاص، حدّث اللينك في
الـ cronjob — الـ endpoint نفسها `/health` مش بتتغير.
