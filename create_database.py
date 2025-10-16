#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ملف إنشاء قاعدة بيانات بوت التلغرام الجامعي
يقوم بإنشاء جميع الجداول والبيانات الأولية المطلوبة
"""

import sys
import sqlite3
import logging
from datetime import datetime
from typing import Optional

# حل مشكلة encoding في Windows
if sys.platform.startswith('win'):
    import codecs
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_creation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseCreator:
    """
    كلاس لإنشاء وإعداد قاعدة البيانات
    """
    
    def __init__(self, db_path: str = "university_bot.db"):
        """
        تهيئة منشئ قاعدة البيانات
        
        Args:
            db_path: مسار ملف قاعدة البيانات
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    def connect(self) -> None:
        """إنشاء اتصال بقاعدة البيانات"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")  # تفعيل المفاتيح الأجنبية
            logger.info(f"✅ تم الاتصال بقاعدة البيانات: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
            raise
    
    def close(self) -> None:
        """إغلاق الاتصال بقاعدة البيانات"""
        if self.conn:
            self.conn.close()
            logger.info("✅ تم إغلاق الاتصال بقاعدة البيانات")
    
    def create_tables(self) -> None:
        """إنشاء جميع الجداول المطلوبة"""
        
        cursor = self.conn.cursor()
        
        try:
            # ==================== جدول المستخدمين ====================
            logger.info("📝 إنشاء جدول المستخدمين...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    user_type TEXT NOT NULL CHECK(user_type IN ('owner', 'admin', 'student')),
                    is_active INTEGER DEFAULT 1,
                    is_blocked INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telegram_id ON users(telegram_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_type ON users(user_type)")
            
            # ==================== جدول المراحل الدراسية ====================
            logger.info("📝 إنشاء جدول المراحل الدراسية...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS academic_levels (
                    level_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level_name TEXT UNIQUE NOT NULL,
                    level_number INTEGER UNIQUE NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ==================== جدول الشعب ====================
            logger.info("📝 إنشاء جدول الشعب...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sections (
                    section_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_name TEXT NOT NULL,
                    level_id INTEGER NOT NULL,
                    study_type TEXT NOT NULL CHECK(study_type IN ('صباحي', 'مسائي')),
                    division TEXT NOT NULL CHECK(division IN ('A', 'B')),
                    admin_id INTEGER,
                    join_code TEXT UNIQUE NOT NULL,
                    max_students INTEGER DEFAULT 50,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (level_id) REFERENCES academic_levels(level_id),
                    FOREIGN KEY (admin_id) REFERENCES users(user_id),
                    UNIQUE(level_id, study_type, division)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_join_code ON sections(join_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_id ON sections(admin_id)")
            
            # ==================== جدول الطلاب في الشعب ====================
            logger.info("📝 إنشاء جدول الطلاب في الشعب...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS student_sections (
                    student_section_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    section_id INTEGER NOT NULL,
                    registration_status TEXT NOT NULL DEFAULT 'pending' 
                        CHECK(registration_status IN ('pending', 'approved', 'rejected')),
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    approved_by INTEGER,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (student_id) REFERENCES users(user_id),
                    FOREIGN KEY (section_id) REFERENCES sections(section_id),
                    FOREIGN KEY (approved_by) REFERENCES users(user_id),
                    UNIQUE(student_id, section_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_section ON student_sections(student_id, section_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_registration_status ON student_sections(registration_status)")
            
            # ==================== جدول المواد ====================
            logger.info("📝 إنشاء جدول المواد...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ==================== جدول ربط المواد بالمراحل ====================
            logger.info("📝 إنشاء جدول ربط المواد بالمراحل...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects_stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER NOT NULL,
                    stage_id INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
                    FOREIGN KEY (stage_id) REFERENCES academic_levels(level_id) ON DELETE CASCADE,
                    UNIQUE(subject_id, stage_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subject_stage ON subjects_stages(subject_id, stage_id)")
            
            # ==================== جدول الواجبات ====================
            logger.info("📝 إنشاء جدول الواجبات...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignments (
                    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    deadline TIMESTAMP NOT NULL,
                    created_by INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    is_edited INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (section_id) REFERENCES sections(section_id),
                    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
                    FOREIGN KEY (created_by) REFERENCES users(user_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_section_assignment ON assignments(section_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_deadline ON assignments(deadline)")
            
            # ==================== جدول تعديلات الواجبات ====================
            logger.info("📝 إنشاء جدول تعديلات الواجبات...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignment_edits (
                    edit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assignment_id INTEGER NOT NULL,
                    old_title TEXT,
                    old_description TEXT,
                    old_deadline TIMESTAMP,
                    edited_by INTEGER NOT NULL,
                    edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id),
                    FOREIGN KEY (edited_by) REFERENCES users(user_id)
                )
            """)
            
            # ==================== جدول إشعارات الواجبات ====================
            logger.info("📝 إنشاء جدول إشعارات الواجبات...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignment_notifications (
                    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assignment_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    notification_type TEXT NOT NULL CHECK(notification_type IN ('new', 'edit', 'delete', 'reminder')),
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivery_status TEXT DEFAULT 'sent' CHECK(delivery_status IN ('sent', 'failed', 'blocked')),
                    FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id),
                    FOREIGN KEY (student_id) REFERENCES users(user_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignment_notification ON assignment_notifications(assignment_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_notification ON assignment_notifications(student_id)")
            
            # ==================== جدول السجلات ====================
            logger.info("📝 إنشاء جدول السجلات...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action_type TEXT NOT NULL,
                    action_details TEXT,
                    target_type TEXT,
                    target_id INTEGER,
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_action_type ON activity_logs(action_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON activity_logs(created_at)")
            
            # ==================== جدول إعدادات البوت ====================
            logger.info("📝 إنشاء جدول إعدادات البوت...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT NOT NULL,
                    setting_type TEXT NOT NULL CHECK(setting_type IN ('string', 'integer', 'boolean', 'json')),
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ==================== جدول الميزات ====================
            logger.info("📝 إنشاء جدول الميزات...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_features (
                    feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feature_key TEXT UNIQUE NOT NULL,
                    feature_name TEXT NOT NULL,
                    is_enabled INTEGER DEFAULT 0,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.conn.commit()
            logger.info("✅ تم إنشاء جميع الجداول بنجاح")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ خطأ في إنشاء الجداول: {e}")
            raise
    
    def insert_initial_data(self) -> None:
        """إضافة البيانات الأولية"""
        
        cursor = self.conn.cursor()
        
        try:
            # ==================== إضافة المراحل الدراسية ====================
            logger.info("📝 إضافة المراحل الدراسية...")
            academic_levels = [
                ('المرحلة الأولى', 1),
                ('المرحلة الثانية', 2),
                ('المرحلة الثالثة', 3),
                ('المرحلة الرابعة', 4)
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO academic_levels (level_name, level_number)
                VALUES (?, ?)
            """, academic_levels)
            
            # ==================== إضافة مواد افتراضية ====================
            logger.info("📝 إضافة المواد الافتراضية...")
            subjects = [
                ('برمجة 1', 'أساسيات البرمجة'),
                ('قواعد البيانات', 'تصميم وإدارة قواعد البيانات'),
                ('الرياضيات', 'الرياضيات للحوسبة'),
                ('الخوارزميات', 'تصميم وتحليل الخوارزميات'),
                ('هندسة البرمجيات', 'مبادئ هندسة البرمجيات')
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO subjects (subject_name, description)
                VALUES (?, ?)
            """, subjects)
            
            # ==================== ربط المواد بالمراحل ====================
            logger.info("📝 ربط المواد بالمراحل الدراسية...")
            subjects_stages_data = [
                (1, 1),  # برمجة 1 - المرحلة الأولى
                (2, 2),  # قواعد البيانات - المرحلة الثانية
                (3, 1),  # الرياضيات - المرحلة الأولى
                (4, 3),  # الخوارزميات - المرحلة الثالثة
                (5, 4),  # هندسة البرمجيات - المرحلة الرابعة
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO subjects_stages (subject_id, stage_id)
                VALUES (?, ?)
            """, subjects_stages_data)
            
            # ==================== إضافة إعدادات البوت ====================
            logger.info("📝 إضافة إعدادات البوت...")
            bot_settings = [
                ('bot_name', 'بوت الواجبات الجامعي', 'string', 'اسم البوت'),
                ('default_language', 'ar', 'string', 'اللغة الافتراضية'),
                ('timezone', 'Asia/Baghdad', 'string', 'المنطقة الزمنية'),
                ('max_students_per_section', '50', 'integer', 'الحد الأقصى للطلاب في الشعبة'),
                ('assignment_edit_duration', '24', 'integer', 'مدة صلاحية تعديل الواجب (بالساعات)')
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, setting_type, description)
                VALUES (?, ?, ?, ?)
            """, bot_settings)
            
            # ==================== إضافة الميزات ====================
            logger.info("📝 إضافة الميزات...")
            bot_features = [
                ('warnings_system', 'نظام التحذيرات', 0, 'نظام إصدار تحذيرات للطلاب'),
                ('leaderboards', 'القوائم التصنيفية', 0, 'عرض ترتيب الطلاب'),
                ('assignment_submission', 'تسليم الواجبات', 0, 'إمكانية تسليم الواجبات عبر البوت'),
                ('auto_reminders', 'التذكيرات التلقائية', 0, 'إرسال تذكيرات تلقائية قبل الموعد النهائي'),
                ('student_blocking', 'نظام الحظر', 1, 'إمكانية حظر الطلاب')
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO bot_features (feature_key, feature_name, is_enabled, description)
                VALUES (?, ?, ?, ?)
            """, bot_features)
            
            self.conn.commit()
            logger.info("✅ تم إضافة البيانات الأولية بنجاح")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ خطأ في إضافة البيانات الأولية: {e}")
            raise
    
    def create_database(self) -> bool:
        """
        تنفيذ عملية إنشاء قاعدة البيانات الكاملة
        
        Returns:
            True إذا نجحت العملية، False إذا فشلت
        """
        try:
            logger.info("🚀 بدء عملية إنشاء قاعدة البيانات...")
            
            self.connect()
            self.create_tables()
            self.insert_initial_data()
            self.close()
            
            logger.info("✅✅✅ تم إنشاء قاعدة البيانات بنجاح!")
            return True
            
        except Exception as e:
            logger.error(f"❌❌❌ فشل إنشاء قاعدة البيانات: {e}")
            return False


def main():
    """الدالة الرئيسية"""
    print("=" * 60)
    print("🎓 بوت التلغرام الجامعي - إنشاء قاعدة البيانات")
    print("=" * 60)
    
    creator = DatabaseCreator()
    success = creator.create_database()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ تم إنشاء قاعدة البيانات بنجاح!")
        print("📁 الملف: university_bot.db")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ فشل إنشاء قاعدة البيانات")
        print("راجع ملف السجلات: database_creation.log")
        print("=" * 60)


if __name__ == "__main__":
    main()

