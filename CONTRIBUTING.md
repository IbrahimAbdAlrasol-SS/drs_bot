# 🤝 المساهمة في المشروع

شكراً لاهتمامك بالمساهمة في بوت الواجبات الجامعي! نرحب بجميع المساهمات سواء كانت:
- 🐛 إصلاح أخطاء
- ✨ إضافة ميزات جديدة
- 📝 تحسين التوثيق
- 🎨 تحسين واجهة المستخدم
- 🔧 تحسين الأداء

---

## 📋 جدول المحتويات

- [قواعد السلوك](#-قواعد-السلوك)
- [كيفية المساهمة](#-كيفية-المساهمة)
- [إعداد بيئة التطوير](#-إعداد-بيئة-التطوير)
- [معايير الكود](#-معايير-الكود)
- [عملية المراجعة](#-عملية-المراجعة)
- [الإبلاغ عن الأخطاء](#-الإبلاغ-عن-الأخطاء)
- [اقتراح ميزات جديدة](#-اقتراح-ميزات-جديدة)

---

## 📜 قواعد السلوك

نتوقع من جميع المساهمين:
- ✅ الاحترام المتبادل
- ✅ قبول النقد البنّاء
- ✅ التركيز على ما هو أفضل للمجتمع
- ✅ إظهار التعاطف تجاه أعضاء المجتمع الآخرين

---

## 🔧 كيفية المساهمة

### 1. Fork المشروع

اضغط على زر "Fork" في أعلى الصفحة على GitHub.

### 2. استنساخ المشروع

```bash
git clone https://github.com/your-username/university-bot.git
cd university-bot
```

### 3. إنشاء Branch جديد

```bash
git checkout -b feature/amazing-feature
```

**تسمية الـ Branches:**
- `feature/` للميزات الجديدة (مثل: `feature/assignment-submission`)
- `fix/` لإصلاح الأخطاء (مثل: `fix/notification-error`)
- `docs/` للتوثيق (مثل: `docs/update-readme`)
- `refactor/` لإعادة الهيكلة (مثل: `refactor/database-class`)

### 4. قم بالتغييرات

اعمل على التغييرات المطلوبة مع الالتزام بمعايير الكود.

### 5. اختبر التغييرات

```bash
# تشغيل الاختبارات
python test_system.py

# تشغيل البوت للتأكد من عمله
python bot.py
```

### 6. Commit التغييرات

```bash
git add .
git commit -m "إضافة: ميزة رائعة"
```

**صيغة رسائل الـ Commit:**
- `إضافة:` للميزات الجديدة
- `إصلاح:` لإصلاح الأخطاء
- `تحديث:` للتحديثات
- `حذف:` للحذف
- `توثيق:` للتوثيق

### 7. Push إلى GitHub

```bash
git push origin feature/amazing-feature
```

### 8. إنشاء Pull Request

1. افتح صفحة المشروع على GitHub
2. اضغط "New Pull Request"
3. اختر Branch الخاص بك
4. اكتب وصف واضح للتغييرات
5. انتظر المراجعة

---

## 💻 إعداد بيئة التطوير

### المتطلبات

- Python 3.9+
- pip
- git

### خطوات الإعداد

```bash
# 1. استنساخ المشروع
git clone https://github.com/your-username/university-bot.git
cd university-bot

# 2. إنشاء بيئة افتراضية
python -m venv venv

# في Windows
venv\Scripts\activate

# في Linux/Mac
source venv/bin/activate

# 3. تثبيت المكتبات
pip install -r requirements.txt

# 4. تثبيت مكتبات التطوير (اختياري)
pip install pytest pylint black flake8

# 5. إعداد ملف .env
cp env_template.txt .env
# عدّل .env بالقيم الخاصة بك

# 6. إنشاء قاعدة البيانات
python create_database.py

# 7. إعداد المالك
python setup_owner.py

# 8. تشغيل الاختبارات
python test_system.py
```

---

## 📏 معايير الكود

### أسلوب Python

نتبع [PEP 8](https://www.python.org/dev/peps/pep-0008/) مع بعض الاستثناءات:

```python
# ✅ جيد
def create_user(telegram_id: int, full_name: str) -> Tuple[bool, str]:
    """
    إنشاء مستخدم جديد
    
    Args:
        telegram_id: معرف تلغرام
        full_name: الاسم الكامل
    
    Returns:
        (نجاح: bool, رسالة: str)
    """
    try:
        # الكود هنا
        return True, "تم بنجاح"
    except Exception as e:
        logger.error(f"خطأ: {e}")
        return False, "فشل"

# ❌ سيء
def CreateUser(TelegramId,FullName):
    #bad code
    return True
```

### التعليقات

- **التعليقات بالعربية** لشرح المنطق
- **Docstrings بالعربية** لتوثيق الدوال
- **أسماء المتغيرات بالإنجليزية**

```python
# ✅ جيد
def send_notification(student_id: int, message: str):
    """
    إرسال إشعار للطالب
    
    Args:
        student_id: معرف الطالب
        message: محتوى الرسالة
    """
    # التحقق من صلاحية الطالب
    if not is_student_active(student_id):
        return False
    
    # إرسال الرسالة
    bot.send_message(student_id, message)
```

### معالجة الأخطاء

**يجب** معالجة جميع الأخطاء المحتملة:

```python
# ✅ جيد
try:
    user = UserDatabase.get_user(telegram_id)
    if not user:
        return False, "المستخدم غير موجود"
    
    # العمليات...
    return True, "نجح"
    
except sqlite3.Error as e:
    logger.error(f"خطأ في قاعدة البيانات: {e}")
    return False, "خطأ في قاعدة البيانات"
    
except Exception as e:
    logger.error(f"خطأ غير متوقع: {e}")
    return False, "خطأ غير متوقع"
```

### Type Hints

استخدم Type Hints دائماً:

```python
# ✅ جيد
def get_students(section_id: int) -> List[Dict[str, Any]]:
    pass

# ❌ سيء
def get_students(section_id):
    pass
```

### السجلات (Logging)

```python
# ✅ جيد
logger.info("✅ تم إنشاء الشعبة بنجاح")
logger.warning("⚠️ عدد الطلاب يقترب من الحد الأقصى")
logger.error("❌ فشل الاتصال بقاعدة البيانات")

# ❌ سيء
print("success")
```

---

## 🔍 عملية المراجعة

### ما نبحث عنه

1. **الوظيفة:** هل يعمل الكود كما هو متوقع؟
2. **الأداء:** هل الكود محسّن؟
3. **الأمان:** هل توجد ثغرات أمنية؟
4. **التوثيق:** هل الكود موثّق بشكل جيد؟
5. **الاختبارات:** هل تم اختبار الكود؟

### زمن المراجعة

- نحاول مراجعة Pull Requests خلال **48 ساعة**
- قد تستغرق PR الكبيرة وقتاً أطول

### التعديلات المطلوبة

إذا طُلبت تعديلات:
1. اقرأ التعليقات بعناية
2. قم بالتعديلات المطلوبة
3. Push التعديلات إلى نفس Branch
4. رد على التعليقات

---

## 🐛 الإبلاغ عن الأخطاء

### قبل الإبلاغ

تأكد من:
- ✅ البحث في Issues الموجودة
- ✅ استخدام أحدث إصدار
- ✅ قراءة التوثيق

### كيفية الإبلاغ

افتح Issue جديد وأدخل:

```markdown
### 🐛 وصف الخطأ
وصف واضح ومختصر للخطأ.

### 📋 خطوات إعادة إنتاج الخطأ
1. اذهب إلى '...'
2. اضغط على '...'
3. انتقل إلى '...'
4. ظهر الخطأ

### ✅ السلوك المتوقع
ما كنت تتوقع حدوثه.

### 📸 لقطات الشاشة
إذا كانت متوفرة، أضف لقطات شاشة.

### 🖥️ معلومات النظام
- نظام التشغيل: [مثل: Windows 10]
- Python Version: [مثل: 3.9.5]
- إصدار المشروع: [مثل: v1.0.0]

### 📝 معلومات إضافية
أي معلومات أخرى عن المشكلة.
```

---

## ✨ اقتراح ميزات جديدة

### قبل الاقتراح

- ✅ تأكد من أن الميزة غير موجودة
- ✅ تحقق من Issues الموجودة
- ✅ فكّر في الفائدة للمستخدمين

### كيفية الاقتراح

افتح Issue جديد:

```markdown
### 💡 الميزة المقترحة
وصف واضح للميزة المقترحة.

### 🎯 المشكلة التي تحلها
ما هي المشكلة أو الحاجة التي تعالجها هذه الميزة؟

### 📝 الحل المقترح
وصف واضح لكيفية عمل الميزة.

### 🔄 البدائل المحتملة
هل فكرت في حلول بديلة؟

### 📸 نماذج أو رسومات
إذا كانت متوفرة.

### 📊 الأولوية
- [ ] عاجل
- [ ] مهم
- [ ] عادي
- [ ] منخفض

### 👥 المستخدمون المستفيدون
من سيستفيد من هذه الميزة؟
```

---

## 🎯 أفكار للمساهمة

### ميزات سهلة للمبتدئين

- [ ] إضافة رسائل ترحيب مخصصة
- [ ] تحسين رسائل الأخطاء
- [ ] إضافة إيموجي للرسائل
- [ ] ترجمة الرسائل
- [ ] تحسين التوثيق

### ميزات متوسطة

- [ ] نظام التذكيرات التلقائية
- [ ] إحصائيات متقدمة
- [ ] تصدير البيانات إلى Excel
- [ ] نظام النسخ الاحتياطي
- [ ] واجهة ويب للإدارة

### ميزات متقدمة

- [ ] نظام تسليم الواجبات (ملفات، صور)
- [ ] نظام التقييم والدرجات
- [ ] القوائم التصنيفية
- [ ] نظام الإشعارات المتقدم
- [ ] دعم متعدد اللغات

---

## 📚 موارد مفيدة

### التوثيق
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Python Documentation](https://docs.python.org/3/)

### دروس
- [Python PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [Git Workflow](https://guides.github.com/introduction/flow/)
- [Writing Good Commit Messages](https://chris.beams.io/posts/git-commit/)

---

## 🙏 شكر للمساهمين

نشكر جميع الذين ساهموا في هذا المشروع:

<!-- يمكنك إضافة قائمة المساهمين هنا -->

---

## 📧 التواصل

لأي استفسارات عن المساهمة:
- 📧 البريد الإلكتروني: contribute@example.com
- 💬 تلغرام: [@ProjectChannel]
- 🐛 GitHub Issues: [افتح Issue](https://github.com/your-repo/university-bot/issues)

---

<div align="center">

**شكراً لمساهمتك! ❤️**

كل مساهمة، مهما كانت صغيرة، تساعد في تحسين المشروع.

</div>

