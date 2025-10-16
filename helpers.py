#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ملف الدوال المساعدة لبوت التلغرام الجامعي
يحتوي على دوال توليد الأكواد، تنسيق الرسائل، والتعامل مع التواريخ
"""

import secrets
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Tuple
import pytz
import re


class CodeGenerator:
    """كلاس لتوليد الأكواد الفريدة"""
    
    @staticmethod
    def generate_section_code(length: int = 12) -> str:
        """
        توليد كود فريد للشعبة
        
        Args:
            length: طول الكود العشوائي (افتراضي: 12)
        
        Returns:
            كود بصيغة: SEC_XXXXXXXXXXXX
        
        مثال:
            >>> generate_section_code()
            'SEC_A7bX9kL2pQ3m'
        """
        random_part = secrets.token_urlsafe(length)[:length]
        # استبدال الأحرف الخاصة لضمان التوافق
        random_part = random_part.replace('-', 'x').replace('_', 'y')
        return f"SEC_{random_part}"
    
    @staticmethod
    def verify_code_uniqueness(db_path: str, code: str) -> bool:
        """
        التحقق من أن الكود غير مكرر
        
        Args:
            db_path: مسار قاعدة البيانات
            code: الكود المراد التحقق منه
        
        Returns:
            True إذا كان الكود فريد، False إذا كان مكرر
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM sections WHERE join_code = ?
            """, (code,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count == 0
            
        except Exception:
            return False
    
    @staticmethod
    def generate_unique_section_code(db_path: str, max_attempts: int = 10) -> Optional[str]:
        """
        توليد كود فريد مع التحقق من عدم التكرار
        
        Args:
            db_path: مسار قاعدة البيانات
            max_attempts: عدد المحاولات القصوى (افتراضي: 10)
        
        Returns:
            كود فريد أو None إذا فشلت كل المحاولات
        
        مثال:
            >>> code = generate_unique_section_code('university_bot.db')
            >>> print(code)
            'SEC_kP9mN2qL4zX7'
        """
        for _ in range(max_attempts):
            code = CodeGenerator.generate_section_code()
            if CodeGenerator.verify_code_uniqueness(db_path, code):
                return code
        
        return None


class DateTimeHelper:
    """كلاس للتعامل مع التواريخ والأوقات"""
    
    # المنطقة الزمنية الافتراضية
    TIMEZONE = pytz.timezone('Asia/Baghdad')
    
    @staticmethod
    def get_current_datetime() -> datetime:
        """
        الحصول على التاريخ والوقت الحالي بالمنطقة الزمنية المحلية
        
        Returns:
            كائن datetime بالمنطقة الزمنية المحددة
        """
        return datetime.now(DateTimeHelper.TIMEZONE)
    
    @staticmethod
    def format_datetime(dt: datetime, include_time: bool = True) -> str:
        """
        تنسيق التاريخ والوقت للعرض بالعربية
        
        Args:
            dt: كائن datetime
            include_time: هل نضمّن الوقت في التنسيق
        
        Returns:
            نص منسق بالعربية
        
        مثال:
            >>> dt = datetime(2025, 10, 20, 23, 59)
            >>> format_datetime(dt)
            '2025-10-20 الساعة 23:59'
        """
        if include_time:
            # تجنب مشاكل encoding باستخدام format بدلاً من strftime
            date_part = dt.strftime('%Y-%m-%d')
            time_part = dt.strftime('%H:%M')
            return f'{date_part} الساعة {time_part}'
        else:
            return dt.strftime('%Y-%m-%d')
    
    @staticmethod
    def parse_datetime(date_str: str, time_str: Optional[str] = None) -> Optional[datetime]:
        """
        تحويل نص إلى كائن datetime
        
        Args:
            date_str: التاريخ بصيغة YYYY-MM-DD
            time_str: الوقت بصيغة HH:MM (اختياري)
        
        Returns:
            كائن datetime أو None إذا فشل التحويل
        
        مثال:
            >>> parse_datetime('2025-10-20', '23:59')
            datetime(2025, 10, 20, 23, 59)
        """
        try:
            if time_str:
                datetime_str = f"{date_str} {time_str}"
                dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            else:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            
            # إضافة المنطقة الزمنية
            dt = DateTimeHelper.TIMEZONE.localize(dt)
            return dt
            
        except Exception:
            return None
    
    @staticmethod
    def is_deadline_passed(deadline: datetime) -> bool:
        """
        التحقق من انتهاء الموعد النهائي
        
        Args:
            deadline: الموعد النهائي
        
        Returns:
            True إذا انتهى الموعد
        """
        current = DateTimeHelper.get_current_datetime()
        return current > deadline
    
    @staticmethod
    def get_remaining_time(deadline: datetime) -> str:
        """
        حساب الوقت المتبقي حتى الموعد النهائي
        
        Args:
            deadline: الموعد النهائي
        
        Returns:
            نص منسق بالعربية يوضح الوقت المتبقي
        
        مثال:
            >>> deadline = datetime.now() + timedelta(days=2, hours=5)
            >>> get_remaining_time(deadline)
            'يومان و 5 ساعات'
        """
        current = DateTimeHelper.get_current_datetime()
        
        if current > deadline:
            return "انتهى الموعد"
        
        diff = deadline - current
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        parts = []
        
        if days > 0:
            if days == 1:
                parts.append("يوم واحد")
            elif days == 2:
                parts.append("يومان")
            elif days <= 10:
                parts.append(f"{days} أيام")
            else:
                parts.append(f"{days} يوماً")
        
        if hours > 0:
            if hours == 1:
                parts.append("ساعة واحدة")
            elif hours == 2:
                parts.append("ساعتان")
            elif hours <= 10:
                parts.append(f"{hours} ساعات")
            else:
                parts.append(f"{hours} ساعة")
        
        if days == 0 and minutes > 0:
            if minutes == 1:
                parts.append("دقيقة واحدة")
            elif minutes == 2:
                parts.append("دقيقتان")
            elif minutes <= 10:
                parts.append(f"{minutes} دقائق")
            else:
                parts.append(f"{minutes} دقيقة")
        
        if not parts:
            return "أقل من دقيقة"
        
        return " و ".join(parts)


class MessageFormatter:
    """كلاس لتنسيق الرسائل"""
    
    @staticmethod
    def format_section_name(level_name: str, study_type: str, division: str) -> str:
        """
        تنسيق اسم الشعبة
        
        Args:
            level_name: اسم المرحلة
            study_type: نوع الدراسة (صباحي/مسائي)
            division: الشعبة (A/B)
        
        Returns:
            اسم منسق للشعبة
        
        مثال:
            >>> format_section_name('المرحلة الأولى', 'صباحي', 'A')
            'المرحلة الأولى - صباحي - شعبة A'
        """
        return f"{level_name} - {study_type} - شعبة {division}"
    
    @staticmethod
    def format_assignment_message(
        subject_name: str,
        title: str,
        description: str,
        deadline: datetime
    ) -> str:
        """
        تنسيق رسالة الواجب
        
        Args:
            subject_name: اسم المادة
            title: عنوان الواجب
            description: وصف الواجب
            deadline: الموعد النهائي
        
        Returns:
            رسالة منسقة
        """
        formatted_deadline = DateTimeHelper.format_datetime(deadline)
        remaining = DateTimeHelper.get_remaining_time(deadline)
        
        message = f"""
📚 واجب جديد - {subject_name}

📌 العنوان: {title}

📝 التفاصيل:
{description}

⏰ الموعد النهائي: {formatted_deadline}
⏳ الوقت المتبقي: {remaining}

🔔 لا تنسَ التسليم!
"""
        return message.strip()
    
    @staticmethod
    def format_registration_request_message(
        full_name: str,
        username: Optional[str],
        telegram_id: int,
        section_name: str
    ) -> str:
        """
        تنسيق رسالة طلب التسجيل للأدمن
        
        Args:
            full_name: الاسم الكامل للطالب
            username: اسم المستخدم في تلغرام
            telegram_id: معرف تلغرام
            section_name: اسم الشعبة
        
        Returns:
            رسالة منسقة
        """
        username_part = f"@{username}" if username else "بدون username"
        
        message = f"""
🆕 طلب تسجيل جديد

👤 الاسم: {full_name}
🆔 المعرف: {username_part}
🔢 ID: {telegram_id}
📚 الشعبة: {section_name}

⏰ وقت الطلب: {DateTimeHelper.format_datetime(DateTimeHelper.get_current_datetime())}
"""
        return message.strip()
    
    @staticmethod
    def format_student_list(students: list) -> str:
        """
        تنسيق قائمة الطلاب
        
        Args:
            students: قائمة من tuples تحتوي على (full_name, username, telegram_id, status)
        
        Returns:
            نص منسق لقائمة الطلاب
        """
        if not students:
            return "لا يوجد طلاب مسجلين"
        
        message = "📋 قائمة الطلاب:\n\n"
        
        for idx, (full_name, username, telegram_id, status) in enumerate(students, 1):
            username_part = f"@{username}" if username else "بدون username"
            status_emoji = {
                'approved': '✅',
                'pending': '⏳',
                'rejected': '❌'
            }.get(status, '❓')
            
            message += f"{idx}. {full_name} ({username_part}) {status_emoji}\n"
            message += f"   ID: {telegram_id}\n\n"
        
        return message.strip()
    
    @staticmethod
    def format_statistics(stats: dict) -> str:
        """
        تنسيق رسالة الإحصائيات
        
        Args:
            stats: قاموس يحتوي على الإحصائيات
        
        Returns:
            رسالة منسقة
        """
        message = "📊 الإحصائيات\n\n"
        
        if 'sections_count' in stats:
            message += f"📚 عدد الشعب: {stats['sections_count']}\n"
        
        if 'students_count' in stats:
            message += f"👥 عدد الطلاب: {stats['students_count']}\n"
        
        if 'pending_count' in stats:
            message += f"⏳ طلبات معلقة: {stats['pending_count']}\n"
        
        if 'assignments_count' in stats:
            message += f"📝 عدد الواجبات: {stats['assignments_count']}\n"
        
        if 'active_assignments' in stats:
            message += f"✅ واجبات نشطة: {stats['active_assignments']}\n"
        
        return message.strip()


class Validator:
    """كلاس للتحقق من صحة البيانات"""
    
    @staticmethod
    def validate_telegram_id(telegram_id: int) -> bool:
        """
        التحقق من صحة معرف تلغرام
        
        Args:
            telegram_id: معرف تلغرام
        
        Returns:
            True إذا كان صحيح
        """
        return isinstance(telegram_id, int) and telegram_id > 0
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """
        التحقق من صحة اسم المستخدم
        
        Args:
            username: اسم المستخدم
        
        Returns:
            True إذا كان صحيح
        """
        if not username:
            return True  # اسم المستخدم اختياري
        
        # اسم المستخدم يجب أن يبدأ بـ @ ويحتوي على 5-32 حرف
        pattern = r'^@[a-zA-Z0-9_]{5,32}$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_full_name(full_name: str) -> Tuple[bool, str]:
        """
        التحقق من صحة الاسم الكامل
        
        Args:
            full_name: الاسم الكامل
        
        Returns:
            (صحيح: bool, رسالة خطأ: str)
        """
        if not full_name or not full_name.strip():
            return False, "الاسم فارغ"
        
        if len(full_name) < 3:
            return False, "الاسم قصير جداً (أقل من 3 أحرف)"
        
        if len(full_name) > 100:
            return False, "الاسم طويل جداً (أكثر من 100 حرف)"
        
        return True, ""
    
    @staticmethod
    def validate_section_code(code: str) -> bool:
        """
        التحقق من صحة كود الشعبة
        
        Args:
            code: كود الشعبة
        
        Returns:
            True إذا كان صحيح
        """
        # الكود يجب أن يبدأ بـ SEC_ ويحتوي على 12 حرف بعدها
        pattern = r'^SEC_[a-zA-Z0-9]{12}$'
        return bool(re.match(pattern, code))
    
    @staticmethod
    def validate_assignment_title(title: str) -> Tuple[bool, str]:
        """
        التحقق من صحة عنوان الواجب
        
        Args:
            title: عنوان الواجب
        
        Returns:
            (صحيح: bool, رسالة خطأ: str)
        """
        if not title or not title.strip():
            return False, "العنوان فارغ"
        
        if len(title) < 3:
            return False, "العنوان قصير جداً"
        
        if len(title) > 200:
            return False, "العنوان طويل جداً"
        
        return True, ""
    
    @staticmethod
    def validate_deadline(deadline: datetime) -> Tuple[bool, str]:
        """
        التحقق من صحة الموعد النهائي
        
        Args:
            deadline: الموعد النهائي
        
        Returns:
            (صحيح: bool, رسالة خطأ: str)
        """
        current = DateTimeHelper.get_current_datetime()
        
        if deadline <= current:
            return False, "الموعد النهائي يجب أن يكون في المستقبل"
        
        # التحقق من أن الموعد ليس بعيداً جداً (مثلاً أكثر من سنة)
        max_deadline = current + timedelta(days=365)
        if deadline > max_deadline:
            return False, "الموعد النهائي بعيد جداً (أكثر من سنة)"
        
        return True, ""


class PermissionChecker:
    """كلاس للتحقق من الصلاحيات"""
    
    @staticmethod
    def check_user_permission(
        db_path: str,
        telegram_id: int,
        required_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        التحقق من صلاحيات المستخدم
        
        Args:
            db_path: مسار قاعدة البيانات
            telegram_id: معرف تلغرام للمستخدم
            required_type: نوع الصلاحية المطلوبة (owner/admin/student)
        
        Returns:
            (لديه صلاحية: bool, سبب الرفض: str أو None)
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_type, is_active, is_blocked
                FROM users
                WHERE telegram_id = ?
            """, (telegram_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False, "المستخدم غير موجود"
            
            user_type, is_active, is_blocked = result
            
            if not is_active:
                return False, "الحساب غير نشط"
            
            if is_blocked:
                return False, "أنت محظور من استخدام البوت"
            
            # المالك لديه كل الصلاحيات
            if user_type == 'owner':
                return True, None
            
            if user_type == required_type:
                return True, None
            
            return False, f"تحتاج إلى صلاحية {required_type}"
            
        except Exception as e:
            return False, f"خطأ في التحقق من الصلاحيات: {e}"
    
    @staticmethod
    def check_admin_section_permission(
        db_path: str,
        telegram_id: int,
        section_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        التحقق من صلاحية الأدمن على شعبة معينة
        
        Args:
            db_path: مسار قاعدة البيانات
            telegram_id: معرف تلغرام للأدمن
            section_id: معرف الشعبة
        
        Returns:
            (لديه صلاحية: bool, سبب الرفض: str أو None)
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # التحقق من نوع المستخدم أولاً
            cursor.execute("""
                SELECT user_id, user_type FROM users WHERE telegram_id = ?
            """, (telegram_id,))
            
            user_result = cursor.fetchone()
            
            if not user_result:
                conn.close()
                return False, "المستخدم غير موجود"
            
            user_id, user_type = user_result
            
            # المالك لديه صلاحية على كل الشعب
            if user_type == 'owner':
                conn.close()
                return True, None
            
            # التحقق من أن الأدمن مسؤول عن هذه الشعبة
            cursor.execute("""
                SELECT admin_id FROM sections WHERE section_id = ?
            """, (section_id,))
            
            section_result = cursor.fetchone()
            conn.close()
            
            if not section_result:
                return False, "الشعبة غير موجودة"
            
            admin_id = section_result[0]
            
            if admin_id == user_id:
                return True, None
            
            return False, "ليس لديك صلاحية على هذه الشعبة"
            
        except Exception as e:
            return False, f"خطأ في التحقق من الصلاحيات: {e}"


# ==================== أمثلة الاستخدام ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🧰 أمثلة على استخدام الدوال المساعدة")
    print("=" * 60)
    
    # مثال 1: توليد كود فريد
    print("\n1️⃣ توليد كود للشعبة:")
    code = CodeGenerator.generate_section_code()
    print(f"   الكود: {code}")
    
    # مثال 2: تنسيق التاريخ
    print("\n2️⃣ تنسيق التاريخ:")
    dt = DateTimeHelper.get_current_datetime()
    formatted = DateTimeHelper.format_datetime(dt)
    print(f"   التاريخ: {formatted}")
    
    # مثال 3: حساب الوقت المتبقي
    print("\n3️⃣ حساب الوقت المتبقي:")
    deadline = dt + timedelta(days=2, hours=5, minutes=30)
    remaining = DateTimeHelper.get_remaining_time(deadline)
    print(f"   الوقت المتبقي: {remaining}")
    
    # مثال 4: تنسيق رسالة واجب
    print("\n4️⃣ تنسيق رسالة واجب:")
    message = MessageFormatter.format_assignment_message(
        subject_name="برمجة 1",
        title="واجب المصفوفات",
        description="حل التمارين من 1 إلى 5",
        deadline=deadline
    )
    print(message)
    
    # مثال 5: التحقق من صحة البيانات
    print("\n5️⃣ التحقق من صحة البيانات:")
    is_valid, error = Validator.validate_full_name("أحمد محمد علي")
    print(f"   الاسم صحيح: {is_valid}")
    
    is_valid, error = Validator.validate_section_code(code)
    print(f"   الكود صحيح: {is_valid}")
    
    print("\n" + "=" * 60)

