#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ملف دوال قاعدة البيانات لبوت التلغرام الجامعي
يحتوي على جميع العمليات المتعلقة بقاعدة البيانات
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from contextlib import contextmanager

from config import Config
from helpers import (
    CodeGenerator, DateTimeHelper, MessageFormatter,
    Validator, PermissionChecker
)

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection(db_path: str = None):
    """
    Context manager للحصول على اتصال بقاعدة البيانات
    
    Args:
        db_path: مسار قاعدة البيانات (اختياري)
    
    Yields:
        اتصال قاعدة البيانات
    """
    if db_path is None:
        db_path = Config.DB_PATH
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=Config.DB_TIMEOUT_SECONDS)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row  # للحصول على النتائج كـ dictionary
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
        raise
    finally:
        if conn:
            conn.close()


# ==================== دوال المستخدمين ====================

class UserDatabase:
    """كلاس لإدارة عمليات المستخدمين"""
    
    @staticmethod
    def create_user(
        telegram_id: int,
        full_name: str,
        user_type: str,
        username: Optional[str] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        إنشاء مستخدم جديد
        
        Args:
            telegram_id: معرف تلغرام
            full_name: الاسم الكامل
            user_type: نوع المستخدم (owner/admin/student)
            username: اسم المستخدم في تلغرام (اختياري)
        
        Returns:
            (نجاح: bool, رسالة: str, معرف المستخدم: int أو None)
        """
        try:
            # التحقق من صحة البيانات
            if not Validator.validate_telegram_id(telegram_id):
                return False, "معرف تلغرام غير صحيح", None
            
            is_valid, error = Validator.validate_full_name(full_name)
            if not is_valid:
                return False, error, None
            
            if user_type not in ['owner', 'admin', 'student']:
                return False, "نوع المستخدم غير صحيح", None
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # التحقق من عدم وجود المستخدم مسبقاً
                cursor.execute("""
                    SELECT user_id FROM users WHERE telegram_id = ?
                """, (telegram_id,))
                
                existing = cursor.fetchone()
                if existing:
                    return False, "المستخدم موجود مسبقاً", existing['user_id']
                
                # إضافة المستخدم
                cursor.execute("""
                    INSERT INTO users (telegram_id, username, full_name, user_type)
                    VALUES (?, ?, ?, ?)
                """, (telegram_id, username, full_name, user_type))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"✅ تم إنشاء مستخدم جديد: {full_name} ({user_type})")
                return True, "تم إنشاء المستخدم بنجاح", user_id
                
        except sqlite3.IntegrityError as e:
            logger.error(f"❌ خطأ في تكرار البيانات: {e}")
            return False, "المستخدم موجود مسبقاً", None
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء المستخدم: {e}")
            return False, f"خطأ غير متوقع: {e}", None
    
    @staticmethod
    def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        الحصول على معلومات مستخدم
        
        Args:
            telegram_id: معرف تلغرام
        
        Returns:
            قاموس يحتوي على معلومات المستخدم أو None
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM users WHERE telegram_id = ?
                """, (telegram_id,))
                
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب المستخدم: {e}")
            return None
    
    @staticmethod
    def update_user(
        telegram_id: int,
        full_name: Optional[str] = None,
        username: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        تحديث معلومات مستخدم
        
        Args:
            telegram_id: معرف تلغرام
            full_name: الاسم الكامل الجديد (اختياري)
            username: اسم المستخدم الجديد (اختياري)
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            updates = []
            params = []
            
            if full_name:
                is_valid, error = Validator.validate_full_name(full_name)
                if not is_valid:
                    return False, error
                updates.append("full_name = ?")
                params.append(full_name)
            
            if username:
                updates.append("username = ?")
                params.append(username)
            
            if not updates:
                return False, "لا توجد تحديثات"
            
            params.append(telegram_id)
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = f"""
                    UPDATE users
                    SET {', '.join(updates)}, last_active = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                """
                
                cursor.execute(query, params)
                conn.commit()
                
                if cursor.rowcount > 0:
                    return True, "تم تحديث المستخدم بنجاح"
                else:
                    return False, "المستخدم غير موجود"
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث المستخدم: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def block_user(telegram_id: int, admin_id: int) -> Tuple[bool, str]:
        """
        حظر مستخدم
        
        Args:
            telegram_id: معرف تلغرام للمستخدم المراد حظره
            admin_id: معرف الأدمن الذي يقوم بالحظر
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # تحديث حالة الحظر
                cursor.execute("""
                    UPDATE users
                    SET is_blocked = 1
                    WHERE telegram_id = ?
                """, (telegram_id,))
                
                if cursor.rowcount == 0:
                    return False, "المستخدم غير موجود"
                
                # تسجيل الحدث
                ActivityDatabase.log_activity(
                    user_id=admin_id,
                    action_type=Config.ActivityTypes.USER_BLOCKED,
                    action_details=f"حظر المستخدم {telegram_id}",
                    target_type='user',
                    target_id=telegram_id
                )
                
                conn.commit()
                
                logger.info(f"✅ تم حظر المستخدم: {telegram_id}")
                return True, "تم حظر المستخدم بنجاح"
                
        except Exception as e:
            logger.error(f"❌ خطأ في حظر المستخدم: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def unblock_user(telegram_id: int, admin_id: int) -> Tuple[bool, str]:
        """
        إلغاء حظر مستخدم
        
        Args:
            telegram_id: معرف تلغرام للمستخدم
            admin_id: معرف الأدمن
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE users
                    SET is_blocked = 0
                    WHERE telegram_id = ?
                """, (telegram_id,))
                
                if cursor.rowcount == 0:
                    return False, "المستخدم غير موجود"
                
                # تسجيل الحدث
                ActivityDatabase.log_activity(
                    user_id=admin_id,
                    action_type=Config.ActivityTypes.USER_UNBLOCKED,
                    action_details=f"إلغاء حظر المستخدم {telegram_id}",
                    target_type='user',
                    target_id=telegram_id
                )
                
                conn.commit()
                
                logger.info(f"✅ تم إلغاء حظر المستخدم: {telegram_id}")
                return True, "تم إلغاء الحظر بنجاح"
                
        except Exception as e:
            logger.error(f"❌ خطأ في إلغاء حظر المستخدم: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """
        الحصول على معلومات مستخدم بواسطة user_id
        
        Args:
            user_id: معرف المستخدم في قاعدة البيانات
        
        Returns:
            قاموس يحتوي على معلومات المستخدم أو None
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM users WHERE user_id = ?
                """, (user_id,))
                
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب المستخدم: {e}")
            return None


# ==================== دوال الشعب ====================

class SectionDatabase:
    """كلاس لإدارة عمليات الشعب"""
    
    @staticmethod
    def create_section(
        level_id: int,
        study_type: str,
        division: str,
        admin_telegram_id: int,
        owner_id: int
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        إنشاء شعبة جديدة
        
        Args:
            level_id: معرف المرحلة الدراسية
            study_type: نوع الدراسة (صباحي/مسائي)
            division: الشعبة (A/B)
            admin_telegram_id: معرف تلغرام للأدمن
            owner_id: معرف المالك الذي ينشئ الشعبة
        
        Returns:
            (نجاح: bool, رسالة: str, معلومات الشعبة: dict أو None)
        """
        try:
            # التحقق من صحة البيانات
            if study_type not in Config.STUDY_TYPES:
                return False, "نوع الدراسة غير صحيح", None
            
            if division not in Config.DIVISIONS:
                return False, "الشعبة غير صحيحة", None
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على اسم المرحلة
                cursor.execute("""
                    SELECT level_name FROM academic_levels WHERE level_id = ?
                """, (level_id,))
                
                level_row = cursor.fetchone()
                if not level_row:
                    return False, "المرحلة الدراسية غير موجودة", None
                
                level_name = level_row['level_name']
                
                # الحصول على معلومات الأدمن
                cursor.execute("""
                    SELECT user_id FROM users WHERE telegram_id = ?
                """, (admin_telegram_id,))
                
                admin_row = cursor.fetchone()
                if not admin_row:
                    return False, "الأدمن غير موجود", None
                
                admin_id = admin_row['user_id']
                
                # توليد كود فريد
                join_code = CodeGenerator.generate_unique_section_code(Config.DB_PATH)
                if not join_code:
                    return False, "فشل توليد الكود الفريد", None
                
                # تنسيق اسم الشعبة
                section_name = MessageFormatter.format_section_name(
                    level_name, study_type, division
                )
                
                # إضافة الشعبة
                cursor.execute("""
                    INSERT INTO sections 
                    (section_name, level_id, study_type, division, admin_id, join_code)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (section_name, level_id, study_type, division, admin_id, join_code))
                
                section_id = cursor.lastrowid
                
                # تسجيل الحدث
                ActivityDatabase.log_activity(
                    user_id=owner_id,
                    action_type=Config.ActivityTypes.SECTION_CREATED,
                    action_details=f"إنشاء شعبة: {section_name}",
                    target_type='section',
                    target_id=section_id
                )
                
                conn.commit()
                
                section_info = {
                    'section_id': section_id,
                    'section_name': section_name,
                    'join_code': join_code,
                    'admin_id': admin_id,
                    'join_link': f"https://t.me/{Config.BOT_USERNAME}?start={join_code}"
                }
                
                logger.info(f"✅ تم إنشاء شعبة جديدة: {section_name}")
                return True, "تم إنشاء الشعبة بنجاح", section_info
                
        except sqlite3.IntegrityError:
            return False, "الشعبة موجودة مسبقاً", None
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء الشعبة: {e}")
            return False, f"خطأ غير متوقع: {e}", None
    
    @staticmethod
    def get_section_by_code(join_code: str) -> Optional[Dict[str, Any]]:
        """
        الحصول على معلومات شعبة بواسطة كود التسجيل
        
        Args:
            join_code: كود التسجيل
        
        Returns:
            قاموس يحتوي على معلومات الشعبة أو None
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT s.*, al.level_name
                    FROM sections s
                    JOIN academic_levels al ON s.level_id = al.level_id
                    WHERE s.join_code = ? AND s.is_active = 1
                """, (join_code,))
                
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الشعبة: {e}")
            return None
    
    @staticmethod
    def get_section_by_id(section_id: int) -> Optional[Dict[str, Any]]:
        """
        الحصول على معلومات شعبة بواسطة المعرف
        
        Args:
            section_id: معرف الشعبة
        
        Returns:
            قاموس يحتوي على معلومات الشعبة أو None
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT s.*, al.level_name, u.full_name as admin_name
                    FROM sections s
                    JOIN academic_levels al ON s.level_id = al.level_id
                    LEFT JOIN users u ON s.admin_id = u.user_id
                    WHERE s.section_id = ?
                """, (section_id,))
                
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الشعبة: {e}")
            return None
    
    @staticmethod
    def get_admin_sections(admin_telegram_id: int) -> List[Dict[str, Any]]:
        """
        الحصول على قائمة الشعب التي يديرها الأدمن
        
        Args:
            admin_telegram_id: معرف تلغرام للأدمن
        
        Returns:
            قائمة من القواميس تحتوي على معلومات الشعب
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT s.*, al.level_name
                    FROM sections s
                    JOIN academic_levels al ON s.level_id = al.level_id
                    JOIN users u ON s.admin_id = u.user_id
                    WHERE u.telegram_id = ? AND s.is_active = 1
                """, (admin_telegram_id,))
                
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب شعب الأدمن: {e}")
            return []
    
    @staticmethod
    def get_all_sections() -> List[Dict[str, Any]]:
        """
        الحصول على جميع الشعب (للمالك)
        
        Returns:
            قائمة من القواميس تحتوي على معلومات الشعب
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT s.*, al.level_name, u.full_name as admin_name
                    FROM sections s
                    JOIN academic_levels al ON s.level_id = al.level_id
                    LEFT JOIN users u ON s.admin_id = u.user_id
                    WHERE s.is_active = 1
                    ORDER BY al.level_number, s.study_type, s.division
                """)
                
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب جميع الشعب: {e}")
            return []


# ==================== دوال الطلاب ====================

class StudentDatabase:
    """كلاس لإدارة عمليات الطلاب"""
    
    @staticmethod
    def register_student(
        telegram_id: int,
        full_name: str,
        section_code: str,
        username: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        تسجيل طالب جديد في شعبة
        
        Args:
            telegram_id: معرف تلغرام
            full_name: الاسم الكامل
            section_code: كود الشعبة
            username: اسم المستخدم (اختياري)
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            # التحقق من صحة البيانات
            is_valid, error = Validator.validate_full_name(full_name)
            if not is_valid:
                return False, error
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على معلومات الشعبة
                cursor.execute("""
                    SELECT section_id, max_students FROM sections
                    WHERE join_code = ? AND is_active = 1
                """, (section_code,))
                
                section_row = cursor.fetchone()
                if not section_row:
                    return False, "كود الشعبة غير صحيح"
                
                section_id = section_row['section_id']
                max_students = section_row['max_students']
                
                # التحقق من عدد الطلاب
                cursor.execute("""
                    SELECT COUNT(*) as count FROM student_sections
                    WHERE section_id = ? AND registration_status = 'approved'
                """, (section_id,))
                
                current_count = cursor.fetchone()['count']
                if current_count >= max_students:
                    return False, "الشعبة ممتلئة"
                
                # إنشاء المستخدم أو تحديثه
                success, message, user_id = UserDatabase.create_user(
                    telegram_id, full_name, 'student', username
                )
                
                if not success and "موجود مسبقاً" not in message:
                    return False, message
                
                # إذا كان المستخدم موجود، نحصل على user_id
                if not user_id:
                    user = UserDatabase.get_user(telegram_id)
                    if user:
                        user_id = user['user_id']
                    else:
                        return False, "خطأ في الحصول على معلومات المستخدم"
                
                # التحقق من عدم وجود تسجيل سابق
                cursor.execute("""
                    SELECT registration_status FROM student_sections
                    WHERE student_id = ? AND section_id = ?
                """, (user_id, section_id))
                
                existing = cursor.fetchone()
                if existing:
                    status = existing['registration_status']
                    if status == 'pending':
                        return False, "لديك طلب تسجيل معلق"
                    elif status == 'approved':
                        return False, "أنت مسجل بالفعل في هذه الشعبة"
                    elif status == 'rejected':
                        return False, "تم رفض طلبك سابقاً. تواصل مع الأدمن"
                
                # إضافة طلب التسجيل
                cursor.execute("""
                    INSERT INTO student_sections (student_id, section_id, registration_status)
                    VALUES (?, ?, 'pending')
                """, (user_id, section_id))
                
                # تسجيل الحدث
                ActivityDatabase.log_activity(
                    user_id=user_id,
                    action_type=Config.ActivityTypes.REGISTRATION_REQUESTED,
                    action_details=f"طلب التسجيل في الشعبة {section_id}",
                    target_type='section',
                    target_id=section_id
                )
                
                conn.commit()
                
                logger.info(f"✅ طلب تسجيل جديد: {full_name} في الشعبة {section_id}")
                return True, "تم إرسال طلب التسجيل بنجاح"
                
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الطالب: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def approve_student(
        admin_telegram_id: int,
        student_telegram_id: int,
        section_id: int
    ) -> Tuple[bool, str]:
        """
        الموافقة على تسجيل طالب
        
        Args:
            admin_telegram_id: معرف تلغرام للأدمن
            student_telegram_id: معرف تلغرام للطالب
            section_id: معرف الشعبة
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            # التحقق من صلاحية الأدمن
            has_permission, error = PermissionChecker.check_admin_section_permission(
                Config.DB_PATH, admin_telegram_id, section_id
            )
            
            if not has_permission:
                return False, error
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على معرفات المستخدمين
                cursor.execute("""
                    SELECT user_id FROM users WHERE telegram_id = ?
                """, (admin_telegram_id,))
                admin_row = cursor.fetchone()
                if not admin_row:
                    return False, "الأدمن غير موجود"
                admin_id = admin_row['user_id']
                
                cursor.execute("""
                    SELECT user_id FROM users WHERE telegram_id = ?
                """, (student_telegram_id,))
                student_row = cursor.fetchone()
                if not student_row:
                    return False, "الطالب غير موجود"
                student_id = student_row['user_id']
                
                # تحديث حالة التسجيل
                cursor.execute("""
                    UPDATE student_sections
                    SET registration_status = 'approved',
                        approved_at = CURRENT_TIMESTAMP,
                        approved_by = ?
                    WHERE student_id = ? AND section_id = ? AND registration_status = 'pending'
                """, (admin_id, student_id, section_id))
                
                if cursor.rowcount == 0:
                    return False, "الطلب غير موجود أو تمت معالجته مسبقاً"
                
                # تسجيل الحدث
                ActivityDatabase.log_activity(
                    user_id=admin_id,
                    action_type=Config.ActivityTypes.REGISTRATION_APPROVED,
                    action_details=f"الموافقة على تسجيل الطالب {student_id}",
                    target_type='student',
                    target_id=student_id
                )
                
                conn.commit()
                
                logger.info(f"✅ تمت الموافقة على الطالب: {student_id} في الشعبة {section_id}")
                return True, "تمت الموافقة على الطالب بنجاح"
                
        except Exception as e:
            logger.error(f"❌ خطأ في الموافقة على الطالب: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def reject_student(
        admin_telegram_id: int,
        student_telegram_id: int,
        section_id: int
    ) -> Tuple[bool, str]:
        """
        رفض تسجيل طالب
        
        Args:
            admin_telegram_id: معرف تلغرام للأدمن
            student_telegram_id: معرف تلغرام للطالب
            section_id: معرف الشعبة
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            # التحقق من صلاحية الأدمن
            has_permission, error = PermissionChecker.check_admin_section_permission(
                Config.DB_PATH, admin_telegram_id, section_id
            )
            
            if not has_permission:
                return False, error
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على معرفات المستخدمين
                cursor.execute("""
                    SELECT user_id FROM users WHERE telegram_id = ?
                """, (admin_telegram_id,))
                admin_row = cursor.fetchone()
                if not admin_row:
                    return False, "الأدمن غير موجود"
                admin_id = admin_row['user_id']
                
                cursor.execute("""
                    SELECT user_id FROM users WHERE telegram_id = ?
                """, (student_telegram_id,))
                student_row = cursor.fetchone()
                if not student_row:
                    return False, "الطالب غير موجود"
                student_id = student_row['user_id']
                
                # تحديث حالة التسجيل
                cursor.execute("""
                    UPDATE student_sections
                    SET registration_status = 'rejected'
                    WHERE student_id = ? AND section_id = ? AND registration_status = 'pending'
                """, (student_id, section_id))
                
                if cursor.rowcount == 0:
                    return False, "الطلب غير موجود أو تمت معالجته مسبقاً"
                
                # تسجيل الحدث
                ActivityDatabase.log_activity(
                    user_id=admin_id,
                    action_type=Config.ActivityTypes.REGISTRATION_REJECTED,
                    action_details=f"رفض تسجيل الطالب {student_id}",
                    target_type='student',
                    target_id=student_id
                )
                
                conn.commit()
                
                logger.info(f"✅ تم رفض الطالب: {student_id} في الشعبة {section_id}")
                return True, "تم رفض الطالب"
                
        except Exception as e:
            logger.error(f"❌ خطأ في رفض الطالب: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def get_pending_students(section_id: int) -> List[Dict[str, Any]]:
        """
        الحصول على قائمة الطلاب المعلقين في شعبة
        
        Args:
            section_id: معرف الشعبة
        
        Returns:
            قائمة من القواميس تحتوي على معلومات الطلاب
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT u.*, ss.registered_at
                    FROM student_sections ss
                    JOIN users u ON ss.student_id = u.user_id
                    WHERE ss.section_id = ? AND ss.registration_status = 'pending'
                    ORDER BY ss.registered_at DESC
                """, (section_id,))
                
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الطلاب المعلقين: {e}")
            return []
    
    @staticmethod
    def get_approved_students(section_id: int) -> List[Dict[str, Any]]:
        """
        الحصول على قائمة الطلاب الموافق عليهم في شعبة
        
        Args:
            section_id: معرف الشعبة
        
        Returns:
            قائمة من القواميس تحتوي على معلومات الطلاب
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT u.*, ss.approved_at
                    FROM student_sections ss
                    JOIN users u ON ss.student_id = u.user_id
                    WHERE ss.section_id = ? 
                      AND ss.registration_status = 'approved'
                      AND ss.is_active = 1
                      AND u.is_blocked = 0
                    ORDER BY u.full_name
                """, (section_id,))
                
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الطلاب الموافق عليهم: {e}")
            return []
    
    @staticmethod
    def get_student_section(telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        الحصول على شعبة الطالب
        
        Args:
            telegram_id: معرف تلغرام للطالب
        
        Returns:
            قاموس يحتوي على معلومات الشعبة أو None
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT s.*, al.level_name
                    FROM student_sections ss
                    JOIN sections s ON ss.section_id = s.section_id
                    JOIN academic_levels al ON s.level_id = al.level_id
                    JOIN users u ON ss.student_id = u.user_id
                    WHERE u.telegram_id = ? 
                      AND ss.registration_status = 'approved'
                      AND ss.is_active = 1
                """, (telegram_id,))
                
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب شعبة الطالب: {e}")
            return None


# ==================== دوال الواجبات ====================

class AssignmentDatabase:
    """كلاس لإدارة عمليات الواجبات"""
    
    @staticmethod
    def create_assignment(
        section_id: int,
        subject_name: str,
        title: str,
        description: str,
        deadline: datetime,
        admin_telegram_id: int
    ) -> Tuple[bool, str, Optional[int]]:
        """
        إنشاء واجب جديد
        
        Args:
            section_id: معرف الشعبة
            subject_name: اسم المادة
            title: عنوان الواجب
            description: وصف الواجب
            deadline: الموعد النهائي
            admin_telegram_id: معرف تلغرام للأدمن
        
        Returns:
            (نجاح: bool, رسالة: str, معرف الواجب: int أو None)
        """
        try:
            # التحقق من صحة البيانات
            is_valid, error = Validator.validate_assignment_title(title)
            if not is_valid:
                return False, error, None
            
            is_valid, error = Validator.validate_deadline(deadline)
            if not is_valid:
                return False, error, None
            
            # التحقق من صلاحية الأدمن
            has_permission, error = PermissionChecker.check_admin_section_permission(
                Config.DB_PATH, admin_telegram_id, section_id
            )
            
            if not has_permission:
                return False, error, None
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على معرف الأدمن
                cursor.execute("""
                    SELECT user_id FROM users WHERE telegram_id = ?
                """, (admin_telegram_id,))
                admin_row = cursor.fetchone()
                if not admin_row:
                    return False, "الأدمن غير موجود", None
                admin_id = admin_row['user_id']
                
                # الحصول على معرف المادة أو إضافتها
                cursor.execute("""
                    SELECT subject_id FROM subjects WHERE subject_name = ?
                """, (subject_name,))
                subject_row = cursor.fetchone()
                
                if subject_row:
                    subject_id = subject_row['subject_id']
                else:
                    cursor.execute("""
                        INSERT INTO subjects (subject_name) VALUES (?)
                    """, (subject_name,))
                    subject_id = cursor.lastrowid
                
                # إضافة الواجب
                cursor.execute("""
                    INSERT INTO assignments 
                    (section_id, subject_id, title, description, deadline, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (section_id, subject_id, title, description, 
                      deadline.isoformat(), admin_id))
                
                assignment_id = cursor.lastrowid
                
                # تسجيل الحدث
                ActivityDatabase.log_activity(
                    user_id=admin_id,
                    action_type=Config.ActivityTypes.ASSIGNMENT_CREATED,
                    action_details=f"إنشاء واجب: {title}",
                    target_type='assignment',
                    target_id=assignment_id
                )
                
                conn.commit()
                
                logger.info(f"✅ تم إنشاء واجب جديد: {title} في الشعبة {section_id}")
                return True, "تم إنشاء الواجب بنجاح", assignment_id
                
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء الواجب: {e}")
            return False, f"خطأ غير متوقع: {e}", None
    
    @staticmethod
    def get_section_assignments(
        section_id: int,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        الحصول على قائمة الواجبات في شعبة
        
        Args:
            section_id: معرف الشعبة
            include_inactive: هل نضمّن الواجبات غير النشطة
        
        Returns:
            قائمة من القواميس تحتوي على معلومات الواجبات
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT a.*, sub.subject_name, u.full_name as creator_name
                    FROM assignments a
                    JOIN subjects sub ON a.subject_id = sub.subject_id
                    JOIN users u ON a.created_by = u.user_id
                    WHERE a.section_id = ?
                """
                
                if not include_inactive:
                    query += " AND a.is_active = 1"
                
                query += " ORDER BY a.deadline DESC"
                
                cursor.execute(query, (section_id,))
                
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الواجبات: {e}")
            return []
    
    @staticmethod
    def edit_assignment(
        assignment_id: int,
        admin_telegram_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        deadline: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        تعديل واجب
        
        Args:
            assignment_id: معرف الواجب
            admin_telegram_id: معرف تلغرام للأدمن
            title: العنوان الجديد (اختياري)
            description: الوصف الجديد (اختياري)
            deadline: الموعد النهائي الجديد (اختياري)
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على الواجب الحالي
                cursor.execute("""
                    SELECT * FROM assignments WHERE assignment_id = ?
                """, (assignment_id,))
                assignment_row = cursor.fetchone()
                
                if not assignment_row:
                    return False, "الواجب غير موجود"
                
                assignment = dict(assignment_row)
                section_id = assignment['section_id']
                
                # التحقق من صلاحية الأدمن
                has_permission, error = PermissionChecker.check_admin_section_permission(
                    Config.DB_PATH, admin_telegram_id, section_id
                )
                
                if not has_permission:
                    return False, error
                
                # الحصول على معرف الأدمن
                cursor.execute("""
                    SELECT user_id FROM users WHERE telegram_id = ?
                """, (admin_telegram_id,))
                admin_row = cursor.fetchone()
                if not admin_row:
                    return False, "الأدمن غير موجود"
                admin_id = admin_row['user_id']
                
                # حفظ القيم القديمة في جدول التعديلات
                cursor.execute("""
                    INSERT INTO assignment_edits 
                    (assignment_id, old_title, old_description, old_deadline, edited_by)
                    VALUES (?, ?, ?, ?, ?)
                """, (assignment_id, assignment['title'], assignment['description'],
                      assignment['deadline'], admin_id))
                
                # تحديث الواجب
                updates = []
                params = []
                
                if title:
                    is_valid, error = Validator.validate_assignment_title(title)
                    if not is_valid:
                        return False, error
                    updates.append("title = ?")
                    params.append(title)
                
                if description:
                    updates.append("description = ?")
                    params.append(description)
                
                if deadline:
                    is_valid, error = Validator.validate_deadline(deadline)
                    if not is_valid:
                        return False, error
                    updates.append("deadline = ?")
                    params.append(deadline.isoformat())
                
                if not updates:
                    return False, "لا توجد تحديثات"
                
                updates.append("is_edited = 1")
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(assignment_id)
                
                query = f"""
                    UPDATE assignments
                    SET {', '.join(updates)}
                    WHERE assignment_id = ?
                """
                
                cursor.execute(query, params)
                
                # تسجيل الحدث
                ActivityDatabase.log_activity(
                    user_id=admin_id,
                    action_type=Config.ActivityTypes.ASSIGNMENT_EDITED,
                    action_details=f"تعديل واجب: {assignment['title']}",
                    target_type='assignment',
                    target_id=assignment_id
                )
                
                conn.commit()
                
                logger.info(f"✅ تم تعديل الواجب: {assignment_id}")
                return True, "تم تعديل الواجب بنجاح"
                
        except Exception as e:
            logger.error(f"❌ خطأ في تعديل الواجب: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def delete_assignment(
        assignment_id: int,
        admin_telegram_id: int
    ) -> Tuple[bool, str]:
        """
        حذف واجب (soft delete)
        
        Args:
            assignment_id: معرف الواجب
            admin_telegram_id: معرف تلغرام للأدمن
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على الواجب
                cursor.execute("""
                    SELECT section_id, title FROM assignments WHERE assignment_id = ?
                """, (assignment_id,))
                assignment_row = cursor.fetchone()
                
                if not assignment_row:
                    return False, "الواجب غير موجود"
                
                section_id = assignment_row['section_id']
                title = assignment_row['title']
                
                # التحقق من صلاحية الأدمن
                has_permission, error = PermissionChecker.check_admin_section_permission(
                    Config.DB_PATH, admin_telegram_id, section_id
                )
                
                if not has_permission:
                    return False, error
                
                # الحصول على معرف الأدمن
                cursor.execute("""
                    SELECT user_id FROM users WHERE telegram_id = ?
                """, (admin_telegram_id,))
                admin_row = cursor.fetchone()
                if not admin_row:
                    return False, "الأدمن غير موجود"
                admin_id = admin_row['user_id']
                
                # حذف soft
                cursor.execute("""
                    UPDATE assignments
                    SET is_active = 0
                    WHERE assignment_id = ?
                """, (assignment_id,))
                
                # تسجيل الحدث
                ActivityDatabase.log_activity(
                    user_id=admin_id,
                    action_type=Config.ActivityTypes.ASSIGNMENT_DELETED,
                    action_details=f"حذف واجب: {title}",
                    target_type='assignment',
                    target_id=assignment_id
                )
                
                conn.commit()
                
                logger.info(f"✅ تم حذف الواجب: {assignment_id}")
                return True, "تم حذف الواجب بنجاح"
                
        except Exception as e:
            logger.error(f"❌ خطأ في حذف الواجب: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def get_assignment_by_id(assignment_id: int) -> Optional[Dict[str, Any]]:
        """
        الحصول على معلومات واجب
        
        Args:
            assignment_id: معرف الواجب
        
        Returns:
            قاموس يحتوي على معلومات الواجب أو None
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT a.*, sub.subject_name, u.full_name as creator_name
                    FROM assignments a
                    JOIN subjects sub ON a.subject_id = sub.subject_id
                    JOIN users u ON a.created_by = u.user_id
                    WHERE a.assignment_id = ?
                """, (assignment_id,))
                
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الواجب: {e}")
            return None


# ==================== دوال الإشعارات ====================

class NotificationDatabase:
    """كلاس لإدارة عمليات الإشعارات"""
    
    @staticmethod
    def log_notification(
        assignment_id: int,
        student_telegram_id: int,
        notification_type: str,
        delivery_status: str = 'sent'
    ) -> Tuple[bool, str]:
        """
        تسجيل إشعار تم إرساله
        
        Args:
            assignment_id: معرف الواجب
            student_telegram_id: معرف تلغرام للطالب
            notification_type: نوع الإشعار (new/edit/delete/reminder)
            delivery_status: حالة التوصيل (sent/failed/blocked)
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على معرف الطالب
                cursor.execute("""
                    SELECT user_id FROM users WHERE telegram_id = ?
                """, (student_telegram_id,))
                student_row = cursor.fetchone()
                
                if not student_row:
                    return False, "الطالب غير موجود"
                
                student_id = student_row['user_id']
                
                # تسجيل الإشعار
                cursor.execute("""
                    INSERT INTO assignment_notifications
                    (assignment_id, student_id, notification_type, delivery_status)
                    VALUES (?, ?, ?, ?)
                """, (assignment_id, student_id, notification_type, delivery_status))
                
                conn.commit()
                
                return True, "تم تسجيل الإشعار"
                
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الإشعار: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def get_notification_stats(assignment_id: int) -> Dict[str, int]:
        """
        الحصول على إحصائيات إرسال الإشعارات لواجب معين
        
        Args:
            assignment_id: معرف الواجب
        
        Returns:
            قاموس يحتوي على الإحصائيات
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN delivery_status = 'sent' THEN 1 ELSE 0 END) as sent,
                        SUM(CASE WHEN delivery_status = 'failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN delivery_status = 'blocked' THEN 1 ELSE 0 END) as blocked
                    FROM assignment_notifications
                    WHERE assignment_id = ?
                """, (assignment_id,))
                
                row = cursor.fetchone()
                
                return {
                    'total': row['total'] or 0,
                    'sent': row['sent'] or 0,
                    'failed': row['failed'] or 0,
                    'blocked': row['blocked'] or 0
                }
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات الإشعارات: {e}")
            return {'total': 0, 'sent': 0, 'failed': 0, 'blocked': 0}


# ==================== دوال السجلات ====================

class ActivityDatabase:
    """كلاس لإدارة عمليات السجلات"""
    
    @staticmethod
    def log_activity(
        user_id: int,
        action_type: str,
        action_details: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        تسجيل حدث في السجل
        
        Args:
            user_id: معرف المستخدم
            action_type: نوع الحدث
            action_details: تفاصيل الحدث (اختياري)
            target_type: نوع الهدف (اختياري)
            target_id: معرف الهدف (اختياري)
            ip_address: عنوان IP (اختياري)
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO activity_logs
                    (user_id, action_type, action_details, target_type, target_id, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, action_type, action_details, target_type, target_id, ip_address))
                
                conn.commit()
                
                return True, "تم تسجيل الحدث"
                
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الحدث: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def get_recent_activities(limit: int = 50) -> List[Dict[str, Any]]:
        """
        الحصول على آخر الأحداث
        
        Args:
            limit: عدد الأحداث المطلوبة
        
        Returns:
            قائمة من القواميس تحتوي على الأحداث
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT al.*, u.full_name, u.user_type
                    FROM activity_logs al
                    LEFT JOIN users u ON al.user_id = u.user_id
                    ORDER BY al.created_at DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الأحداث: {e}")
            return []


# ==================== دوال الإحصائيات ====================

class StatisticsDatabase:
    """كلاس لإدارة الإحصائيات"""
    
    @staticmethod
    def get_owner_statistics() -> Dict[str, Any]:
        """
        الحصول على إحصائيات شاملة للمالك
        
        Returns:
            قاموس يحتوي على الإحصائيات
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # عدد الشعب
                cursor.execute("""
                    SELECT COUNT(*) as count FROM sections WHERE is_active = 1
                """)
                stats['sections_count'] = cursor.fetchone()['count']
                
                # عدد الطلاب الكلي
                cursor.execute("""
                    SELECT COUNT(DISTINCT student_id) as count
                    FROM student_sections
                    WHERE registration_status = 'approved' AND is_active = 1
                """)
                stats['students_count'] = cursor.fetchone()['count']
                
                # عدد الطلاب المعلقين
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM student_sections
                    WHERE registration_status = 'pending'
                """)
                stats['pending_count'] = cursor.fetchone()['count']
                
                # عدد الواجبات
                cursor.execute("""
                    SELECT COUNT(*) as count FROM assignments WHERE is_active = 1
                """)
                stats['assignments_count'] = cursor.fetchone()['count']
                
                # عدد الأدمنز
                cursor.execute("""
                    SELECT COUNT(*) as count FROM users 
                    WHERE user_type = 'admin' AND is_active = 1
                """)
                stats['admins_count'] = cursor.fetchone()['count']
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات المالك: {e}")
            return {}
    
    @staticmethod
    def get_admin_statistics(admin_telegram_id: int) -> Dict[str, Any]:
        """
        الحصول على إحصائيات الأدمن
        
        Args:
            admin_telegram_id: معرف تلغرام للأدمن
        
        Returns:
            قاموس يحتوي على الإحصائيات
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على شعب الأدمن
                cursor.execute("""
                    SELECT s.section_id
                    FROM sections s
                    JOIN users u ON s.admin_id = u.user_id
                    WHERE u.telegram_id = ? AND s.is_active = 1
                """, (admin_telegram_id,))
                
                sections = cursor.fetchall()
                section_ids = [s['section_id'] for s in sections]
                
                if not section_ids:
                    return {}
                
                stats = {}
                stats['sections_count'] = len(section_ids)
                
                # استخدام placeholders
                placeholders = ','.join('?' * len(section_ids))
                
                # عدد الطلاب
                cursor.execute(f"""
                    SELECT COUNT(*) as count
                    FROM student_sections
                    WHERE section_id IN ({placeholders})
                      AND registration_status = 'approved'
                      AND is_active = 1
                """, section_ids)
                stats['students_count'] = cursor.fetchone()['count']
                
                # عدد الطلاب المعلقين
                cursor.execute(f"""
                    SELECT COUNT(*) as count
                    FROM student_sections
                    WHERE section_id IN ({placeholders})
                      AND registration_status = 'pending'
                """, section_ids)
                stats['pending_count'] = cursor.fetchone()['count']
                
                # عدد الواجبات
                cursor.execute(f"""
                    SELECT COUNT(*) as count
                    FROM assignments
                    WHERE section_id IN ({placeholders})
                      AND is_active = 1
                """, section_ids)
                stats['assignments_count'] = cursor.fetchone()['count']
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات الأدمن: {e}")
            return {}


# ==================== دوال الإعدادات ====================

class SettingsDatabase:
    """كلاس لإدارة الإعدادات"""
    
    @staticmethod
    def get_setting(setting_key: str) -> Optional[str]:
        """
        الحصول على قيمة إعداد
        
        Args:
            setting_key: مفتاح الإعداد
        
        Returns:
            قيمة الإعداد أو None
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT setting_value FROM bot_settings WHERE setting_key = ?
                """, (setting_key,))
                
                row = cursor.fetchone()
                
                if row:
                    return row['setting_value']
                
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الإعداد: {e}")
            return None
    
    @staticmethod
    def set_setting(
        setting_key: str,
        setting_value: str,
        user_id: int
    ) -> Tuple[bool, str]:
        """
        تعيين قيمة إعداد
        
        Args:
            setting_key: مفتاح الإعداد
            setting_value: قيمة الإعداد
            user_id: معرف المستخدم الذي يقوم بالتعديل
        
        Returns:
            (نجاح: bool, رسالة: str)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE bot_settings
                    SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE setting_key = ?
                """, (setting_value, setting_key))
                
                if cursor.rowcount == 0:
                    return False, "الإعداد غير موجود"
                
                # تسجيل الحدث
                ActivityDatabase.log_activity(
                    user_id=user_id,
                    action_type=Config.ActivityTypes.SETTING_CHANGED,
                    action_details=f"تغيير إعداد {setting_key} إلى {setting_value}"
                )
                
                conn.commit()
                
                return True, "تم تحديث الإعداد بنجاح"
                
        except Exception as e:
            logger.error(f"❌ خطأ في تعيين الإعداد: {e}")
            return False, f"خطأ غير متوقع: {e}"
    
    @staticmethod
    def toggle_feature(feature_key: str, user_id: int) -> Tuple[bool, str, bool]:
        """
        تشغيل/إيقاف ميزة
        
        Args:
            feature_key: مفتاح الميزة
            user_id: معرف المستخدم
        
        Returns:
            (نجاح: bool, رسالة: str, الحالة الجديدة: bool)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # الحصول على الحالة الحالية
                cursor.execute("""
                    SELECT is_enabled FROM bot_features WHERE feature_key = ?
                """, (feature_key,))
                
                row = cursor.fetchone()
                
                if not row:
                    return False, "الميزة غير موجودة", False
                
                current_status = row['is_enabled']
                new_status = 0 if current_status else 1
                
                # تحديث الحالة
                cursor.execute("""
                    UPDATE bot_features
                    SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE feature_key = ?
                """, (new_status, feature_key))
                
                # تسجيل الحدث
                status_text = "تشغيل" if new_status else "إيقاف"
                ActivityDatabase.log_activity(
                    user_id=user_id,
                    action_type=Config.ActivityTypes.FEATURE_TOGGLED,
                    action_details=f"{status_text} ميزة {feature_key}"
                )
                
                conn.commit()
                
                return True, f"تم {status_text} الميزة", bool(new_status)
                
        except Exception as e:
            logger.error(f"❌ خطأ في تبديل الميزة: {e}")
            return False, f"خطأ غير متوقع: {e}", False
    
    @staticmethod
    def is_feature_enabled(feature_key: str) -> bool:
        """
        التحقق من تفعيل ميزة
        
        Args:
            feature_key: مفتاح الميزة
        
        Returns:
            True إذا كانت مفعلة
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT is_enabled FROM bot_features WHERE feature_key = ?
                """, (feature_key,))
                
                row = cursor.fetchone()
                
                if row:
                    return bool(row['is_enabled'])
                
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من الميزة: {e}")
            return False


# ==================== دوال مساعدة عامة ====================

def get_academic_levels() -> List[Dict[str, Any]]:
    """
    الحصول على قائمة المراحل الدراسية
    
    Returns:
        قائمة من القواميس تحتوي على المراحل الدراسية
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM academic_levels
                WHERE is_active = 1
                ORDER BY level_number
            """)
            
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"❌ خطأ في جلب المراحل الدراسية: {e}")
        return []


def get_subjects() -> List[Dict[str, Any]]:
    """
    الحصول على قائمة المواد
    
    Returns:
        قائمة من القواميس تحتوي على المواد
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM subjects
                WHERE is_active = 1
                ORDER BY subject_name
            """)
            
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"❌ خطأ في جلب المواد: {e}")
        return []


def get_subjects_for_stage(stage_id: int) -> List[Dict[str, Any]]:
    """
    الحصول على قائمة المواد لمرحلة معينة
    
    Args:
        stage_id: معرف المرحلة
    
    Returns:
        قائمة من القواميس تحتوي على المواد
    
    مثال:
        >>> subjects = get_subjects_for_stage(1)
        >>> for subject in subjects:
        ...     print(subject['subject_name'])
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*
                FROM subjects s
                JOIN subjects_stages ss ON s.subject_id = ss.subject_id
                WHERE ss.stage_id = ? AND s.is_active = 1 AND ss.is_active = 1
                ORDER BY s.subject_name
            """, (stage_id,))
            
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"❌ خطأ في جلب مواد المرحلة: {e}")
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("💾 دوال قاعدة البيانات - اختبار")
    print("=" * 60)
    
    # مثال: الحصول على المراحل الدراسية
    print("\n📚 المراحل الدراسية:")
    levels = get_academic_levels()
    for level in levels:
        print(f"  - {level['level_name']}")
    
    # مثال: الحصول على المواد
    print("\n📖 المواد:")
    subjects = get_subjects()
    for subject in subjects:
        print(f"  - {subject['subject_name']}")
    
    print("\n" + "=" * 60)

