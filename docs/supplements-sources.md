# مصادر قواعد محلل المكملات

‏كل قاعدة في `supplements.py` و`whey_analyzer.py` (غير معادلات الواي اللي
جاية من صاحب المشروع) طالعة من مصدر من دول. المفتاح بين علامتين هو
اللي في `SOURCES`. قاعدة جديدة تتكتب هنا الأول.

‏القواعد دي بتحذّر بس، مابتفتحش حاجة لحالة مرضية. وكلها للكبار الأصحاء:
الحوامل والأطفال وأصحاب الأمراض المزمنة ليهم حدود تانية.

## كرياتين

- `issn_creatine`: Kreider RB et al. *ISSN position stand: safety and efficacy
  of creatine supplementation in exercise, sport, and medicine.* JISSN 2017;14:18.
  - ‏جرعة الصيانة ٣-٥ جم في اليوم (بعد تحميل اختياري ٠.٣ جم/كجم لمدة ٥-٧ أيام).
  - ‏الـMonohydrate هو أكتر نوع مدروس. الأنواع التانية مااتثبتش إنها أحسن،
    والـEthyl Ester طلع أضعف منه في المقارنة المباشرة.

## أوميجا ٣

- `efsa_epa_dha`: EFSA NDA Panel. *Scientific Opinion on Dietary Reference Values
  for fats.* EFSA Journal 2010;8(3):1461. ‏الاحتياج للكبار ٢٥٠ مجم EPA+DHA في اليوم.
- `efsa_epa_dha_ul`: EFSA NDA Panel. *Scientific Opinion on the Tolerable Upper
  Intake Level of EPA, DHA and DPA.* EFSA Journal 2012;10(7):2815. ‏لحد ٥ جم في
  اليوم من المكملات مفيهاش قلق على الأمان.
- `nih_omega3`: NIH Office of Dietary Supplements, *Omega-3 Fatty Acids — Fact
  Sheet for Health Professionals.* ‏كبسولة زيت السمك العادية ١٠٠٠ مجم فيها حوالي
  ١٨٠ EPA و١٢٠ DHA، يعني ٣٠٪. أقل من كده يبقى أضعف من الزيت العادي.

## مالتي فيتامين

- `nih_ul`: NIH ODS / National Academies (IOM), *Dietary Reference Intakes:
  Tolerable Upper Intake Levels*، للكبار ١٩ سنة وأكتر. الحدود المستخدمة:
  ‏فيتامين A ٣٠٠٠ ميكروجم (ريتينول بس، مش بيتا كاروتين)، D ١٠٠ ميكروجم
  (٤٠٠٠ وحدة)، E ١٠٠٠ مجم، C ٢٠٠٠ مجم، B6 ١٠٠ مجم، نياسين ٣٥ مجم (من المكمل)،
  حمض الفوليك ١٠٠٠ ميكروجم، حديد ٤٥ مجم، زنك ٤٠ مجم، سيلينيوم ٤٠٠ ميكروجم،
  يود ١١٠٠ ميكروجم، نحاس ١٠ مجم، منجنيز ١١ مجم، ماغنيسيوم ٣٥٠ مجم (من المكمل)،
  كالسيوم ٢٥٠٠ مجم (١٩-٥٠ سنة؛ بعد ٥٠ الحد ٢٠٠٠).

## بري وورك أوت

- `efsa_caffeine`: EFSA NDA Panel. *Scientific Opinion on the safety of caffeine.*
  EFSA Journal 2015;13(5):4102. ‏لحد ٢٠٠ مجم في المرة و٤٠٠ مجم في اليوم آمن
  للكبار الأصحاء. الحوامل ٢٠٠ مجم في اليوم كله.
- `issn_beta_alanine`: Trexler ET et al. *ISSN position stand: Beta-Alanine.*
  JISSN 2015;12:30. ‏٤-٦ جم في اليوم لمدة أسبوعين على الأقل.
- `fda_blend`: 21 CFR 101.36(c). ‏الـProprietary Blend بيتكتب وزنه الكلي بس،
  من غير كمية كل مادة.

## EAA / BCAA

- `issn_protein`: Jäger R et al. *ISSN position stand: protein and exercise.*
  JISSN 2017;14:20. ‏الجرعة لازم يبقى فيها ٧٠٠-٣٠٠٠ مجم ليوسين.
- `wolfe_bcaa`: Wolfe RR. *Branched-chain amino acids and muscle protein synthesis
  in humans: myth or reality?* JISSN 2017;14:30. ‏الـBCAA لوحدها مابتبنيش عضل؛
  لازم الـ٩ أحماض الأساسية.

## أنواع الواي

- `usdec_wpi`: U.S. Dairy Export Council, *Reference Manual for U.S. Whey and
  Lactose Products.* ‏الـIsolate فيه ٩٠٪ بروتين أو أكتر (على الوزن الجاف).
  ‏الحد في الكود ٨٠٪ من الحصة، عشان النكهة والمحلّي بياخدوا جزء منها.
  **ده افتراض مننا**، مش رقم من المصدر.
- `who_sugars`: WHO, *Guideline: Sugars intake for adults and children*, 2015.
  ‏السكر الحر أقل من ١٠٪ من السعرات، يعني حوالي ٥٠ جم على ٢٠٠٠ سعر. جينر فيه
  أكتر من ٢٥ جم سكر في الحصة بياخد نص الحد ده لوحده.
