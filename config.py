#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ملف التكوين والإعدادات لبوت التلغرام الجامعي
يحتوي على جميع الثوابت والإعدادات المطلوبة
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env
load_dotenv()


class Config:
    """كلاس الإعدادات الرئيسي"""
    
    # ==================== إعدادات قاعدة البيانات ====================
    
    # مسار قاعدة البيانات
    DB_PATH = os.getenv('DB_PATH', 'university_bot.db')
    
    # ==================== إعدادات البوت ====================
    
    # Telegram Bot Token (يجب تعيينه في ملف .env)
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    
    if not BOT_TOKEN:
        raise ValueError(
            "❌ خطأ: لم يتم تعيين BOT_TOKEN\n"
            "الرجاء إنشاء ملف .env وإضافة:\n"
            "BOT_TOKEN=your_bot_token_here"
        )
    
    # اسم البوت
    BOT_NAME = os.getenv('BOT_NAME', 'بوت الواجبات الجامعي')
    
    # معرف البوت (username)
    BOT_USERNAME = os.getenv('BOT_USERNAME', 'UniversityAssignmentsBot')
    
    # ==================== إعدادات المالك ====================
    
    # معرف تلغرام للمالك (يجب تعيينه)
    OWNER_TELEGRAM_ID = os.getenv('OWNER_TELEGRAM_ID', '')
    
    if not OWNER_TELEGRAM_ID:
        raise ValueError(
            "❌ خطأ: لم يتم تعيين OWNER_TELEGRAM_ID\n"
            "الرجاء إضافة في ملف .env:\n"
            "OWNER_TELEGRAM_ID=your_telegram_id"
        )
    
    try:
        OWNER_TELEGRAM_ID = int(OWNER_TELEGRAM_ID)
    except ValueError:
        raise ValueError("❌ خطأ: OWNER_TELEGRAM_ID يجب أن يكون رقم")
    
    # اسم المالك (اختياري)
    OWNER_NAME = os.getenv('OWNER_NAME', 'المسؤول')
    
    # ==================== إعدادات الشعب ====================
    
    # الحد الأقصى للطلاب في الشعبة الواحدة
    MAX_STUDENTS_PER_SECTION = int(os.getenv('MAX_STUDENTS_PER_SECTION', '50'))
    
    # أنواع الدراسة المسموحة
    STUDY_TYPES = ['صباحي', 'مسائي']
    
    # الشعب المسموحة
    DIVISIONS = ['A', 'B']
    
    # ==================== إعدادات الواجبات ====================
    
    # مدة صلاحية تعديل الواجب (بالساعات)
    ASSIGNMENT_EDIT_DURATION_HOURS = int(
        os.getenv('ASSIGNMENT_EDIT_DURATION_HOURS', '24')
    )
    
    # الحد الأقصى لطول عنوان الواجب
    MAX_ASSIGNMENT_TITLE_LENGTH = 200
    
    # الحد الأقصى لطول وصف الواجب
    MAX_ASSIGNMENT_DESCRIPTION_LENGTH = 2000
    
    # ==================== إعدادات التاريخ والوقت ====================
    
    # المنطقة الزمنية
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Baghdad')
    
    # صيغة عرض التاريخ
    DATE_FORMAT = '%Y-%m-%d'
    
    # صيغة عرض الوقت
    TIME_FORMAT = '%H:%M'
    
    # صيغة عرض التاريخ والوقت معاً
    DATETIME_FORMAT = '%Y-%m-%d %H:%M'
    
    # ==================== إعدادات السجلات (Logging) ====================
    
    # مستوى السجلات
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # مسار ملف السجلات
    LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
    
    # الحد الأقصى لحجم ملف السجلات (بالميجابايت)
    MAX_LOG_FILE_SIZE_MB = int(os.getenv('MAX_LOG_FILE_SIZE_MB', '10'))
    
    # عدد ملفات السجلات الاحتياطية
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # ==================== إعدادات الرسائل ====================
    
    # اللغة الافتراضية
    DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'ar')
    
    # الحد الأقصى لطول الرسالة في تلغرام
    MAX_MESSAGE_LENGTH = 4096
    
    # الحد الأقصى لطول Caption في تلغرام
    MAX_CAPTION_LENGTH = 1024
    
    # ==================== إعدادات الإشعارات ====================
    
    # تأخير بين إرسال الإشعارات (بالثواني) لتجنب الحظر
    NOTIFICATION_DELAY_SECONDS = float(
        os.getenv('NOTIFICATION_DELAY_SECONDS', '0.05')
    )
    
    # عدد المحاولات لإرسال الإشعار في حالة الفشل
    NOTIFICATION_RETRY_ATTEMPTS = int(
        os.getenv('NOTIFICATION_RETRY_ATTEMPTS', '3')
    )
    
    # ==================== إعدادات الأمان ====================
    
    # طول الكود الفريد للشعبة
    SECTION_CODE_LENGTH = 12
    
    # بادئة كود الشعبة
    SECTION_CODE_PREFIX = 'SEC_'
    
    # عدد المحاولات لتوليد كود فريد
    MAX_CODE_GENERATION_ATTEMPTS = 10
    
    # ==================== إعدادات الأداء ====================
    
    # حجم دفعة الإشعارات (عدد الطلاب في كل دفعة)
    NOTIFICATION_BATCH_SIZE = int(os.getenv('NOTIFICATION_BATCH_SIZE', '30'))
    
    # مهلة الاتصال بقاعدة البيانات (بالثواني)
    DB_TIMEOUT_SECONDS = int(os.getenv('DB_TIMEOUT_SECONDS', '10'))
    
    # ==================== حالات المحادثة (States) ====================
    
    class States:
        """حالات المحادثة للبوت"""
        
        # حالات عامة
        MAIN_MENU = 'main_menu'
        
        # حالات التسجيل
        WAITING_FOR_NAME = 'waiting_for_name'
        REGISTRATION_PENDING = 'registration_pending'
        
        # حالات إنشاء الشعبة
        CREATE_SECTION_LEVEL = 'create_section_level'
        CREATE_SECTION_TYPE = 'create_section_type'
        CREATE_SECTION_DIVISION = 'create_section_division'
        CREATE_SECTION_ADMIN = 'create_section_admin'
        
        # حالات إنشاء الواجب
        CREATE_ASSIGNMENT_SUBJECT = 'create_assignment_subject'
        CREATE_ASSIGNMENT_TITLE = 'create_assignment_title'
        CREATE_ASSIGNMENT_DESCRIPTION = 'create_assignment_description'
        CREATE_ASSIGNMENT_DATE = 'create_assignment_date'
        CREATE_ASSIGNMENT_TIME = 'create_assignment_time'
        
        # حالات تعديل الواجب
        EDIT_ASSIGNMENT_SELECT = 'edit_assignment_select'
        EDIT_ASSIGNMENT_FIELD = 'edit_assignment_field'
        EDIT_ASSIGNMENT_VALUE = 'edit_assignment_value'
        
        # حالات إدارة الطلاب
        MANAGE_STUDENTS_LIST = 'manage_students_list'
        MANAGE_STUDENTS_ACTION = 'manage_students_action'
        ADD_STUDENT_MANUAL = 'add_student_manual'
        BLOCK_STUDENT = 'block_student'
    
    # ==================== رسائل البوت ====================
    
    class Messages:
        """رسائل البوت المعيارية"""
        
        # رسائل الترحيب
        WELCOME_OWNER = """
مرحباً بك في لوحة تحكم المالك! 👑

يمكنك إدارة جميع جوانب البوت من هنا.
استخدم الأزرار أدناه للوصول إلى الميزات.
"""
        
        WELCOME_ADMIN = """
مرحباً بك أيها الأدمن! 👨‍💼

يمكنك إدارة شعبتك ونشر الواجبات.
استخدم الأزرار أدناه للبدء.
"""
        
        WELCOME_STUDENT = """
مرحباً بك! 👋

يمكنك استلام الواجبات والإشعارات من هنا.
"""
        
        WELCOME_NEW_USER = """
مرحباً بك في بوت الواجبات الجامعي! 🎓

للتسجيل، استخدم رابط التسجيل الخاص بشعبتك.
"""
        
        # رسائل الأخطاء
        ERROR_GENERAL = "❌ حدث خطأ غير متوقع. الرجاء المحاولة لاحقاً."
        ERROR_NO_PERMISSION = "❌ ليس لديك صلاحية لتنفيذ هذا الأمر."
        ERROR_BLOCKED = "🚫 أنت محظور من استخدام البوت."
        ERROR_INVALID_INPUT = "❌ المدخلات غير صحيحة. الرجاء المحاولة مرة أخرى."
        ERROR_NOT_REGISTERED = "❌ أنت غير مسجل. استخدم رابط التسجيل الخاص بشعبتك."
        
        # رسائل النجاح
        SUCCESS_REGISTRATION_SENT = """
✅ تم إرسال طلب التسجيل!

سيتم مراجعة طلبك من قبل الأدمن.
سنرسل لك إشعاراً عند الموافقة.
"""
        
        SUCCESS_REGISTRATION_APPROVED = """
🎉 مبروك! تمت الموافقة على تسجيلك

يمكنك الآن استلام الواجبات والإشعارات.
"""
        
        SUCCESS_ASSIGNMENT_CREATED = """
✅ تم إنشاء الواجب بنجاح!

سيتم إرسال إشعارات لجميع الطلاب المسجلين.
"""
        
        SUCCESS_ASSIGNMENT_EDITED = """
✅ تم تعديل الواجب بنجاح!

سيتم إرسال إشعارات التعديل للطلاب.
"""
        
        # رسائل الانتظار
        WAITING_FOR_ADMIN_APPROVAL = """
⏳ طلبك قيد المراجعة

تم إرسال طلب التسجيل للأدمن.
الرجاء الانتظار حتى تتم الموافقة.
"""
        
        SENDING_NOTIFICATIONS = """
📤 جارِ إرسال الإشعارات...

الرجاء الانتظار حتى يتم إرسال الإشعارات لجميع الطلاب.
"""
    
    # ==================== أزرار لوحة المفاتيح ====================
    
    class Keyboards:
        """أزرار لوحات المفاتيح"""
        
        # أزرار المالك
        OWNER_MAIN = [
            ['➕ إنشاء شعبة', '📋 عرض الشعب'],
            ['👥 إدارة الأدمنز', '📊 الإحصائيات'],
            ['⚙️ الإعدادات', '🔧 الميزات']
        ]
        
# أزر        ار الأدمن
        ADMIN_MAIN = [
            ['➕ نشر واجب', '📝 الواجبات'],
            ['👥 إدارة الطلاب', '📊 الإحصائيات'],
            ['⏳ الطلبات المعلقة']
        ]
        
        # أزرار الطالب
        STUDENT_MAIN = [
            ['📚 واجباتي', 'ℹ️ معلومات الشعبة']
        ]
        
        # أزرار الموافقة/الرفض
        APPROVE_REJECT = [
            ['✅ موافقة', '❌ رفض']
        ]
        
        # أزرار نعم/لا
        YES_NO = [
            ['نعم', 'لا']
        ]
        
        # أزرار العودة والإلغاء
        BACK_CANCEL = [
            ['🔙 رجوع', '❌ إلغاء']
        ]
    
    # ==================== الأوامر ====================
    
    class Commands:
        """أوامر البوت"""
        
        START = 'start'
        HELP = 'help'
        CANCEL = 'cancel'
        STATS = 'stats'
        SETTINGS = 'settings'
        
        # أوامر المالك
        CREATE_SECTION = 'create_section'
        LIST_SECTIONS = 'list_sections'
        MANAGE_ADMINS = 'manage_admins'
        
        # أوامر الأدمن
        CREATE_ASSIGNMENT = 'create_assignment'
        LIST_ASSIGNMENTS = 'list_assignments'
        MANAGE_STUDENTS = 'manage_students'
        PENDING_REQUESTS = 'pending_requests'
        
        # أوامر الطالب
        MY_ASSIGNMENTS = 'my_assignments'
        SECTION_INFO = 'section_info'
    
    # ==================== أنواع الأحداث للسجلات ====================
    
    class ActivityTypes:
        """أنواع الأحداث التي يتم تسجيلها"""
        
        # أحداث المستخدمين
        USER_REGISTERED = 'user_registered'
        USER_BLOCKED = 'user_blocked'
        USER_UNBLOCKED = 'user_unblocked'
        
        # أحداث الشعب
        SECTION_CREATED = 'section_created'
        SECTION_UPDATED = 'section_updated'
        SECTION_DELETED = 'section_deleted'
        ADMIN_ASSIGNED = 'admin_assigned'
        
        # أحداث التسجيل
        REGISTRATION_REQUESTED = 'registration_requested'
        REGISTRATION_APPROVED = 'registration_approved'
        REGISTRATION_REJECTED = 'registration_rejected'
        
        # أحداث الواجبات
        ASSIGNMENT_CREATED = 'assignment_created'
        ASSIGNMENT_EDITED = 'assignment_edited'
        ASSIGNMENT_DELETED = 'assignment_deleted'
        NOTIFICATION_SENT = 'notification_sent'
        
        # أحداث الإعدادات
        SETTING_CHANGED = 'setting_changed'
        FEATURE_TOGGLED = 'feature_toggled'


class Development:
    """إعدادات خاصة ببيئة التطوير"""
    
    # تفعيل وضع التطوير
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    
    # إظهار رسائل SQL في وضع التطوير
    SHOW_SQL_QUERIES = os.getenv('SHOW_SQL_QUERIES', 'False').lower() == 'true'
    
    # تفعيل الاختبارات التلقائية
    AUTO_TESTING = os.getenv('AUTO_TESTING', 'False').lower() == 'true'


# ==================== دوال مساعدة ====================

def get_bot_link(code: str = '') -> str:
    """
    إنشاء رابط البوت
    
    Args:
        code: كود الشعبة (اختياري)
    
    Returns:
        رابط البوت الكامل
    """
    base_url = f"https://t.me/{Config.BOT_USERNAME}"
    
    if code:
        return f"{base_url}?start={code}"
    
    return base_url


def ensure_directories() -> None:
    """إنشاء المجلدات المطلوبة إذا لم تكن موجودة"""
    
    directories = [
        'logs',
        'backups',
        'temp'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)


# ==================== التحقق من الإعدادات ====================

def validate_config() -> bool:
    """
    التحقق من صحة الإعدادات
    
    Returns:
        True إذا كانت الإعدادات صحيحة
    """
    errors = []
    
    # التحقق من وجود BOT_TOKEN
    if not Config.BOT_TOKEN:
        errors.append("BOT_TOKEN غير موجود")
    
    # التحقق من وجود OWNER_TELEGRAM_ID
    if not Config.OWNER_TELEGRAM_ID:
        errors.append("OWNER_TELEGRAM_ID غير موجود")
    
    # التحقق من صحة القيم الرقمية
    if Config.MAX_STUDENTS_PER_SECTION <= 0:
        errors.append("MAX_STUDENTS_PER_SECTION يجب أن يكون أكبر من 0")
    
    if errors:
        print("❌ أخطاء في الإعدادات:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


# ==================== مثال ملف .env ====================

ENV_TEMPLATE = """
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
BOT_USERNAME=UniversityAssignmentsBot
BOT_NAME=بوت الواجبات الجامعي

# Owner Configuration
OWNER_TELEGRAM_ID=123456789
OWNER_NAME=المسؤول

# Database Configuration
DB_PATH=university_bot.db

# Section Configuration
MAX_STUDENTS_PER_SECTION=50

# Assignment Configuration
ASSIGNMENT_EDIT_DURATION_HOURS=24

# Timezone Configuration
TIMEZONE=Asia/Baghdad

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=bot.log
MAX_LOG_FILE_SIZE_MB=10
LOG_BACKUP_COUNT=5

# Notification Configuration
NOTIFICATION_DELAY_SECONDS=0.05
NOTIFICATION_RETRY_ATTEMPTS=3
NOTIFICATION_BATCH_SIZE=30

# Performance Configuration
DB_TIMEOUT_SECONDS=10

# Development Configuration (optional)
DEBUG_MODE=False
SHOW_SQL_QUERIES=False
AUTO_TESTING=False
"""


def create_env_template():
    """إنشاء ملف .env نموذجي إذا لم يكن موجوداً"""
    if not os.path.exists('.env'):
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(ENV_TEMPLATE.strip())
        print("✅ تم إنشاء ملف .env نموذجي")
        print("⚠️  الرجاء تعديل القيم في ملف .env قبل تشغيل البوت")


if __name__ == "__main__":
    print("=" * 60)
    print("⚙️  التحقق من إعدادات البوت")
    print("=" * 60)
    
    # إنشاء المجلدات المطلوبة
    ensure_directories()
    print("✅ تم إنشاء المجلدات المطلوبة")
    
    # إنشاء ملف .env نموذجي
    create_env_template()
    
    # التحقق من صحة الإعدادات
    if validate_config():
        print("\n✅ جميع الإعدادات صحيحة")
        print(f"📁 مسار قاعدة البيانات: {Config.DB_PATH}")
        print(f"🤖 اسم البوت: {Config.BOT_NAME}")
        print(f"👑 معرف المالك: {Config.OWNER_TELEGRAM_ID}")
    else:
        print("\n❌ يوجد أخطاء في الإعدادات")
    
    print("=" * 60)

