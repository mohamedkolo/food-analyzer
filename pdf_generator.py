"""
=====================================================
NutraX — Meal Plan PDF Generator
=====================================================
- HTML-based template with proper Arabic RTL rendering
- Uses WeasyPrint for PDF generation
- Flask Blueprint ready to register in your main app

USAGE:
  1. Put meal_plan.html in your templates/ folder
  2. Put this file (pdf_generator.py) in your project root
  3. In app.py:   from pdf_generator import pdf_bp
                  app.register_blueprint(pdf_bp)
  4. Test by visiting:  /meal-plan/preview        (HTML preview)
                        /meal-plan/pdf            (Download PDF)
                        /meal-plan/patient/1.pdf  (Real patient)
=====================================================
"""

from flask import Blueprint, render_template, make_response
from weasyprint import HTML
from datetime import datetime
import io

pdf_bp = Blueprint('pdf', __name__)


# =====================================================
# SAMPLE DATA (for testing — replace with DB call later)
# =====================================================
def get_sample_data():
    return {
        'file_number': 'NX-2026-002',
        'date': '18 أبريل 2026',
        'client': {
            'name': 'عميل 2',
            'age': 53,
            'gender': 'أنثى',
            'height': 162,
            'weight': 69.5,
            'bmi': 26.5,
            'body_fat': 37.5,
            'tdee': 1742,
            'target_kcal': 1142,
            'deficit': 600,
        },
        'conditions': ['إمساك مزمن', 'حرق بطيء', 'سمنة'],
        'clinical_notes': 'متابعة الحديد • فيتامين D3 • صحة القولون • ثلاسيميا • G6PD',
        'allowed': [
            'فول مدمس + شوربات + سمك مشوي',
            'دجاج مشوي أو فرن (بدون جلد) + بيض',
            'شوفان + خبز أسمر + أرز بني + برغل',
            'زبادي يوناني سادة + جبن قريش',
            'ملوخية + كوسة + خضار مطبوخة',
            'زيت زيتون (ملعقة) + فاكهة طازجة',
            'شاي أخضر + ماء دافئ بالليمون صباحاً',
        ],
        'forbidden': [
            'الخبز الأبيض والعيش الفينو',
            'الأكل المقلي + الدهانة + السمن',
            'المشروبات الغازية + العصائر المعلبة',
            'التوابل الحارة (تستفز القولون)',
            'الحلويات والسكريات المضافة',
            'الكافيين الزائد (أكتر من كوب)',
            'البقوليات بكميات كبيرة دفعة واحدة',
        ],
        'days': [
            {
                'name': 'الأحد', 'total_kcal': 1274,
                'breakfast': 'فول مدمس بزيت الزيتون + بيضتان مسلوقتان',
                'lunch': 'صدر دجاج مشوي + أرز بني + سلطة خضار',
                'dinner': 'شوربة عدس أحمر + خبز أسمر',
                'snack': 'تفاحة بالقشر (80 kcal) + زبادي يوناني سادة',
            },
            {
                'name': 'الاثنين', 'total_kcal': 1187,
                'breakfast': 'شوفان بالحليب + موزة + لوز',
                'lunch': 'سمك بلطي مشوي + بطاطا حلوة + كوسة مطبوخة',
                'dinner': 'عدس مطبوخ بجزر وكرفس + خبز',
                'snack': 'لوز نيء 20 جم (120 kcal) + كمثرى',
            },
            {
                'name': 'الثلاثاء', 'total_kcal': 1069,
                'breakfast': 'بيض أومليت بالخضار + خبز أسمر',
                'lunch': 'فخذ دجاج فرن + برغل + سلطة فتوش',
                'dinner': 'شوربة خضار + جبن قريش',
                'snack': 'برتقالة (62 kcal) + حليب دافئ خالي الدسم',
            },
            {
                'name': 'الأربعاء', 'total_kcal': 1169,
                'breakfast': 'فول بطحينة وليمون + خبز أسمر',
                'lunch': 'كبدة دجاج مشوية + أرز بني + ملوخية',
                'dinner': 'حمص بطحينة + خبز أسمر + طماطم',
                'snack': 'تمرتان (66 kcal) + زبادي يوناني',
            },
            {
                'name': 'الخميس', 'total_kcal': 1216,
                'breakfast': 'شوفان بالموز والقرفة + لوز نيء',
                'lunch': 'سمكة بلطي كاملة + بطاطا مسلوقة + سلطة',
                'dinner': 'شوربة عدس أصفر + خبز',
                'snack': 'كيوي (61 kcal) + تفاحة بالقشر',
            },
            {
                'name': 'الجمعة', 'total_kcal': 1215,
                'breakfast': 'فول مدمس + بيضتان + طماطم وخيار',
                'lunch': 'صدر دجاج فرن بالخضار + أرز بني',
                'dinner': 'عدس مطبوخ + جبن قريش',
                'snack': 'نصف رمانة (53 kcal) + زبادي يوناني',
            },
            {
                'name': 'السبت', 'total_kcal': 1142,
                'breakfast': 'شوفان بالكيوي والعسل',
                'lunch': 'كشري مصري (كمية معتدلة)',
                'dinner': 'سمك بلطي مشوي + برغل + سلطة فتوش',
                'snack': 'موزة صغيرة (89 kcal)',
            },
        ],
        'tips': {
            'water': [
                'كوب ماء دافئ + نصف ليمونة فور الاستيقاظ',
                '8 أكواب ماء يومياً (2 لتر على الأقل)',
                'كوب ماء قبل كل وجبة بـ 30 دقيقة',
                'تجنب الماء البارد جداً مع الأكل',
            ],
            'habits': [
                '3 وجبات رئيسية + سناك واحد',
                'مضغ بطيء — الشبع بعد 20 دقيقة',
                'لا تأكل أمام الشاشة — يزيد الكمية',
                'الفطار إجباري خلال ساعة من الاستيقاظ',
            ],
            'metabolism': [
                'بروتين في كل وجبة (بيض / دجاج / سمك / عدس)',
                'توابل آمنة: كركم + قرفة + زنجبيل',
                'مشي 30 دقيقة بعد الغداء',
                'قم وتحرك 5 دقائق كل ساعة',
            ],
            'warnings': [
                'لا تخفض السعرات أكثر من المحدد — يوقف الحرق',
                'لو جعت بين الوجبات: ماء أولاً ثم فاكهة',
                'راجع مع أخصائي التغذية كل 4 أسابيع',
                'أي أعراض غير عادية — راجع طبيبك فوراً',
            ],
        },
        'clinic_name': 'NutraX Clinical Nutrition',
        'author': 'إعداد د. محمد — أخصائي التغذية الإكلينيكية',
        'review_weeks': 4,
    }


# =====================================================
# ROUTE 1: HTML PREVIEW (for testing in browser)
# =====================================================
@pdf_bp.route('/meal-plan/preview')
def preview_meal_plan():
    """View the template in browser before generating PDF"""
    data = get_sample_data()
    return render_template('meal_plan.html', **data)


# =====================================================
# ROUTE 2: GENERATE PDF (sample data)
# =====================================================
@pdf_bp.route('/meal-plan/pdf')
def generate_meal_plan_pdf():
    """Generate PDF with sample data — for testing"""
    data = get_sample_data()
    html_string = render_template('meal_plan.html', **data)
    pdf_bytes = HTML(string=html_string).write_pdf()

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="meal_plan_sample.pdf"'
    return response


# =====================================================
# ROUTE 3: REAL PATIENT PDF (connects to your DB)
# =====================================================
@pdf_bp.route('/meal-plan/patient/<int:patient_id>.pdf')
def patient_meal_plan_pdf(patient_id):
    """
    Generate PDF for a real patient from the DB.
    TODO: Replace the build_data_from_patient() function below
          with your actual DB query once you're ready.
    """
    data = build_data_from_patient(patient_id)
    html_string = render_template('meal_plan.html', **data)
    pdf_bytes = HTML(string=html_string).write_pdf()

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    safe_name = data['client']['name'].replace(' ', '_')
    response.headers['Content-Disposition'] = f'inline; filename="nutrax_{safe_name}_{patient_id}.pdf"'
    return response


def build_data_from_patient(patient_id):
    """
    ============================================
    ADAPT THIS to your Patient/MealPlan models
    ============================================
    For now: returns sample data. Replace with:

        from models import Patient, MealPlan
        patient = Patient.query.get_or_404(patient_id)
        plan = MealPlan.query.filter_by(patient_id=patient_id).first()

        return {
            'file_number': f'NX-{datetime.now().year}-{patient.id:03d}',
            'date': datetime.now().strftime('%d %B %Y'),
            'client': {
                'name': patient.name,
                'age': patient.age,
                'gender': patient.gender,
                'height': patient.height,
                'weight': patient.weight,
                'bmi': round(patient.weight / (patient.height/100)**2, 1),
                'body_fat': patient.body_fat,
                'tdee': plan.tdee,
                'target_kcal': plan.target_kcal,
                'deficit': plan.tdee - plan.target_kcal,
            },
            'conditions': patient.conditions.split(',') if patient.conditions else [],
            'clinical_notes': patient.clinical_notes or '',
            'allowed': plan.allowed_foods.split('\\n') if plan.allowed_foods else [],
            'forbidden': plan.forbidden_foods.split('\\n') if plan.forbidden_foods else [],
            'days': [{'name': d.day_name, 'total_kcal': d.total_kcal,
                      'breakfast': d.breakfast, 'lunch': d.lunch,
                      'dinner': d.dinner, 'snack': d.snack} for d in plan.days],
            'tips': {...},  # can be static or from config
            'clinic_name': 'NutraX Clinical Nutrition',
            'author': f'إعداد {plan.nutritionist.name}',
            'review_weeks': plan.review_weeks or 4,
        }
    """
    # For now — just return sample data
    return get_sample_data()
