# النسخ الاحتياطي

## الوضع قبل كده

مكانش فيه أي نسخ احتياطي في المشروع — ولا `pg_dump` ولا أي حاجة. وقاعدة بيانات
Postgres المجانية على Render ليها تاريخ انتهاء وبتحتاج تتعمل من الأول. يعني
بيانات العملاء كانت في نسخة واحدة بس.

## النسخة الأوتوماتيك (كل يوم)

`.github/workflows/db-backup.yml` بياخد نسخة كل يوم ٣:١٧ الفجر، ويشفّرها
بـgpg، ويرفعها على **Cloudflare R2** (ببلاش لحد ١٠ جيجا)، ويسيب آخر
نسخة بس (`KEEP` في الملف -- صاحب المشروع طلب كل نسخة تمسح اللي قبلها). اتعمل لأن صاحب المشروع مالوش كمبيوتر ياخد منه النسخة اليدوي.

‏الريبو Public، فالنسخة **مابتطلعش من غير تشفير**، ومفيش artifact (بيتنزّل
لأي حد مسجّل على GitHub)، والسجل مافيهوش غير اسم الملف وحجمه.

### الأسرار المطلوبة

GitHub → الريبو → Settings → Secrets and variables → Actions → New repository secret:

| الاسم | منين |
|---|---|
| `DATABASE_URL` | Neon → المشروع → Connect → Connection string |
| `R2_ACCOUNT_ID` | Cloudflare → R2 → Account ID (على اليمين) |
| `R2_BUCKET` | اسم الـbucket اللي عملته (مثلًا `nutrax-backups`) |
| `R2_ACCESS_KEY_ID` و`R2_SECRET_ACCESS_KEY` | R2 → Manage API tokens → Create token (Object Read & Write على الـbucket ده بس) |
| `BACKUP_PASSPHRASE` | باسورد طويلة إنت اللي تختارها. **من غيرها النسخ كلها مالهاش لازمة**: احفظها في مكان تاني غير GitHub |

### تتأكد إنها شغالة

GitHub → Actions → DB backup → Run workflow. لو الأسرار ناقصة، السجل بيقول
أنهي واحد. ولو فشلت أي ليلة، GitHub بيبعت إيميل لصاحب الريبو.

### الاسترجاع من نسخة R2

```bash
# نزّل الملف من Cloudflare → R2 → الـbucket، وبعدين:
gpg --decrypt nutrax-2026-11-24_0117.sql.gz.gpg | gunzip > nutrax.sql
psql "$DATABASE_URL" < nutrax.sql
```

## إزاي تاخد نسخة يدوي

من جهازك انت (مش من Render):

```bash
# 1. هات رابط الاتصال: Render → الداتابيز → External Database URL
export DATABASE_URL='postgres://...'

# 2. خد النسخة
python3 tools/backup_db.py
```

بيطلع ملف في `backups/nutrax-2026-08-20_1430.sql`.

### لو `pg_dump` مش متسطب عندك

```bash
python3 tools/backup_db.py --json
```

نسخة JSON، مش محتاجة أي برنامج، وتقدر تفتحها وتقراها. بس الـ SQL هي اللي
بتسترجع منها بضغطة، فحاول تسطّب الـ client:

- **Mac**: `brew install libpq`
- **Ubuntu/WSL**: `sudo apt install postgresql-client`
- **Windows**: نزّل PostgreSQL من الموقع الرسمي، محتاج `pg_dump.exe` بس

## الاسترجاع

```bash
psql "$DATABASE_URL" < backups/nutrax-2026-08-20_1430.sql
```

**جرّب الاسترجاع مرة على داتابيز فاضية قبل ما تحتاجه بجد.** نسخة احتياطية
محدش جرّبها مش نسخة احتياطية — دي أمنية.

## كل قد إيه

- **دلوقتي**: مرة كل أسبوع، ويوم ما تعمل تغيير كبير
- **لما يبقى فيه عملاء بيدفعوا**: كل يوم. وخلي آخر 7 نسخ على الأقل

الأوتوماتيك أحسن من إنك تفتكر: ده اللي `db-backup.yml` بيعمله كل يوم (فوق).

## مهم جداً

الملف ده فيه **بيانات صحية وشخصية لكل عملائك**: أسماء، تليفونات، أوزان،
أمراض. عاملها معاملة الملف الطبي:

- خزّنها **مشفّرة** (Disk encryption أو ملف مضغوط بباسورد)
- **متحطهاش** على Google Drive أو Dropbox مشترك من غير تشفير
- **متبعتهاش** في واتساب أو إيميل
- امسح النسخ القديمة اللي مش محتاجها

الباسوردات جوه النسخة **مشفّرة** (scrypt) مش مكتوبة صريح — دي حاجة معمولة صح
في المشروع من الأصل.

الريبو فيه `.gitignore` بيمنع أي نسخة تتدفع بالغلط على GitHub. متشيلهوش.
