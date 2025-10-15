#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
البوت الرئيسي لنظام إدارة الواجبات الجامعية
يحتوي على جميع handlers والمنطق الأساسي للبوت
"""

import logging
import time
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from telebot import TeleBot, types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage

from config import Config, get_bot_link
from database import (
    UserDatabase, SectionDatabase, StudentDatabase,
    AssignmentDatabase, NotificationDatabase, ActivityDatabase,
    StatisticsDatabase, SettingsDatabase, get_academic_levels, get_subjects
)
from helpers import (
    CodeGenerator, DateTimeHelper, MessageFormatter,
    Validator, PermissionChecker
)

# إعداد نظام السجلات
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# إنشاء البوت
state_storage = StateMemoryStorage()
bot = TeleBot(Config.BOT_TOKEN, state_storage=state_storage)


# ==================== حالات المحادثة ====================

class BotStates(StatesGroup):
    """حالات المحادثة"""
    
    # حالات التسجيل
    waiting_for_name = State()
    
    # حالات إنشاء الشعبة
    create_section_level = State()
    create_section_type = State()
    create_section_division = State()
    create_section_admin = State()
    
    # حالات إنشاء الواجب
    create_assignment_section = State()
    create_assignment_subject = State()
    create_assignment_title = State()
    create_assignment_description = State()
    create_assignment_date = State()
    create_assignment_time = State()


# ==================== دوال مساعدة ====================

def get_user_info(message: types.Message) -> Dict[str, Any]:
    """
    استخراج معلومات المستخدم من رسالة تلغرام
    
    Args:
        message: رسالة تلغرام
    
    Returns:
        قاموس يحتوي على معلومات المستخدم
    """
    return {
        'telegram_id': message.from_user.id,
        'username': f"@{message.from_user.username}" if message.from_user.username else None,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name
    }


def create_main_keyboard(user_type: str) -> types.ReplyKeyboardMarkup:
    """
    إنشاء لوحة المفاتيح الرئيسية حسب نوع المستخدم
    
    Args:
        user_type: نوع المستخدم (owner/admin/student)
    
    Returns:
        لوحة المفاتيح
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if user_type == 'owner':
        for row in Config.Keyboards.OWNER_MAIN:
            keyboard.row(*[types.KeyboardButton(btn) for btn in row])
    
    elif user_type == 'admin':
        for row in Config.Keyboards.ADMIN_MAIN:
            keyboard.row(*[types.KeyboardButton(btn) for btn in row])
    
    elif user_type == 'student':
        for row in Config.Keyboards.STUDENT_MAIN:
            keyboard.row(*[types.KeyboardButton(btn) for btn in row])
    
    return keyboard


def send_long_message(chat_id: int, text: str) -> None:
    """
    إرسال رسالة طويلة مع التقسيم التلقائي
    
    Args:
        chat_id: معرف المحادثة
        text: النص المراد إرساله
    """
    max_length = Config.MAX_MESSAGE_LENGTH
    
    if len(text) <= max_length:
        bot.send_message(chat_id, text)
    else:
        parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        for part in parts:
            bot.send_message(chat_id, part)
            time.sleep(0.1)  # تأخير صغير بين الرسائل


def check_permission(telegram_id: int, required_type: str) -> tuple[bool, Optional[str]]:
    """
    التحقق من صلاحيات المستخدم
    
    Args:
        telegram_id: معرف تلغرام
        required_type: نوع الصلاحية المطلوبة
    
    Returns:
        (لديه صلاحية: bool, سبب الرفض: str أو None)
    """
    return PermissionChecker.check_user_permission(
        Config.DB_PATH, telegram_id, required_type
    )


# ==================== معالجات الأوامر الأساسية ====================

@bot.message_handler(commands=['start'])
def handle_start(message: types.Message):
    """معالج أمر /start"""
    try:
        user_info = get_user_info(message)
        telegram_id = user_info['telegram_id']
        
        logger.info(f"📩 أمر /start من المستخدم: {telegram_id}")
        
        # التحقق من وجود كود الشعبة في الأمر
        if len(message.text.split()) > 1:
            code = message.text.split()[1]
            
            # التحقق من صحة الكود
            if Validator.validate_section_code(code):
                handle_registration_link(message, code)
                return
        
        # الحصول على معلومات المستخدم من قاعدة البيانات
        user = UserDatabase.get_user(telegram_id)
        
        if not user:
            # مستخدم جديد
            bot.send_message(
                message.chat.id,
                Config.Messages.WELCOME_NEW_USER
            )
            return
        
        # التحقق من الحظر
        if user['is_blocked']:
            bot.send_message(
                message.chat.id,
                Config.Messages.ERROR_BLOCKED
            )
            return
        
        # إرسال الرسالة الترحيبية حسب نوع المستخدم
        user_type = user['user_type']
        
        if user_type == 'owner':
            welcome_message = Config.Messages.WELCOME_OWNER
        elif user_type == 'admin':
            welcome_message = Config.Messages.WELCOME_ADMIN
        elif user_type == 'student':
            welcome_message = Config.Messages.WELCOME_STUDENT
        else:
            welcome_message = Config.Messages.WELCOME_NEW_USER
        
        keyboard = create_main_keyboard(user_type)
        bot.send_message(
            message.chat.id,
            welcome_message,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة /start: {e}")
        bot.send_message(
            message.chat.id,
            Config.Messages.ERROR_GENERAL
        )


@bot.message_handler(commands=['help'])
def handle_help(message: types.Message):
    """معالج أمر /help"""
    try:
        user_info = get_user_info(message)
        telegram_id = user_info['telegram_id']
        
        user = UserDatabase.get_user(telegram_id)
        
        help_text = """
🆘 مساعدة البوت

📚 الأوامر المتاحة:
/start - بدء البوت
/help - عرض هذه المساعدة
/cancel - إلغاء العملية الحالية

"""
        
        if user:
            user_type = user['user_type']
            
            if user_type == 'owner':
                help_text += """
👑 أوامر المالك:
• إنشاء شعبة جديدة
• عرض جميع الشعب
• إدارة الأدمنز
• عرض الإحصائيات الشاملة
• إدارة الإعدادات
"""
            
            elif user_type == 'admin':
                help_text += """
👨‍💼 أوامر الأدمن:
• نشر واجب جديد
• تعديل/حذف الواجبات
• إدارة الطلاب
• الموافقة على طلبات التسجيل
• عرض إحصائيات الشعبة
"""
            
            elif user_type == 'student':
                help_text += """
👨‍🎓 ميزات الطالب:
• استلام إشعارات الواجبات
• عرض واجباتي
• عرض معلومات الشعبة
"""
        
        help_text += """
💡 للاستفسارات، تواصل مع الأدمن.
"""
        
        bot.send_message(message.chat.id, help_text)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة /help: {e}")


@bot.message_handler(commands=['cancel'])
def handle_cancel(message: types.Message):
    """معالج أمر /cancel"""
    try:
        bot.delete_state(message.from_user.id, message.chat.id)
        
        user_info = get_user_info(message)
        user = UserDatabase.get_user(user_info['telegram_id'])
        
        if user:
            keyboard = create_main_keyboard(user['user_type'])
            bot.send_message(
                message.chat.id,
                "❌ تم إلغاء العملية",
                reply_markup=keyboard
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ تم إلغاء العملية"
            )
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة /cancel: {e}")


# ==================== معالجات التسجيل ====================

def handle_registration_link(message: types.Message, code: str):
    """
    معالجة رابط التسجيل
    
    Args:
        message: رسالة تلغرام
        code: كود الشعبة
    """
    try:
        user_info = get_user_info(message)
        telegram_id = user_info['telegram_id']
        
        # الحصول على معلومات الشعبة
        section = SectionDatabase.get_section_by_code(code)
        
        if not section:
            bot.send_message(
                message.chat.id,
                "❌ كود الشعبة غير صحيح أو منتهي الصلاحية"
            )
            return
        
        # التحقق من عدم وجود تسجيل سابق
        user = UserDatabase.get_user(telegram_id)
        
        if user and user['user_type'] in ['owner', 'admin']:
            bot.send_message(
                message.chat.id,
                "❌ لا يمكنك التسجيل كطالب. أنت " + user['user_type']
            )
            return
        
        # إرسال معلومات الشعبة
        section_info = f"""
📚 معلومات الشعبة

🏷️ الاسم: {section['section_name']}
📖 المرحلة: {section['level_name']}
📅 نوع الدراسة: {section['study_type']}
🔤 الشعبة: {section['division']}

للتسجيل، أرسل اسمك الكامل:
"""
        
        bot.send_message(message.chat.id, section_info)
        
        # حفظ كود الشعبة في الحالة
        bot.set_state(
            message.from_user.id,
            BotStates.waiting_for_name,
            message.chat.id
        )
        
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['section_code'] = code
            data['section_name'] = section['section_name']
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة رابط التسجيل: {e}")
        bot.send_message(
            message.chat.id,
            Config.Messages.ERROR_GENERAL
        )


@bot.message_handler(state=BotStates.waiting_for_name)
def handle_student_name(message: types.Message):
    """معالج إدخال اسم الطالب"""
    try:
        user_info = get_user_info(message)
        full_name = message.text.strip()
        
        # التحقق من صحة الاسم
        is_valid, error = Validator.validate_full_name(full_name)
        
        if not is_valid:
            bot.send_message(
                message.chat.id,
                f"❌ {error}\n\nالرجاء إدخال اسمك الكامل مرة أخرى:"
            )
            return
        
        # الحصول على كود الشعبة من الحالة
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            section_code = data.get('section_code')
            section_name = data.get('section_name')
        
        if not section_code:
            bot.send_message(
                message.chat.id,
                "❌ حدث خطأ. الرجاء استخدام رابط التسجيل مرة أخرى."
            )
            bot.delete_state(message.from_user.id, message.chat.id)
            return
        
        # تسجيل الطالب
        success, msg = StudentDatabase.register_student(
            telegram_id=user_info['telegram_id'],
            full_name=full_name,
            section_code=section_code,
            username=user_info['username']
        )
        
        if success:
            bot.send_message(
                message.chat.id,
                Config.Messages.SUCCESS_REGISTRATION_SENT
            )
            
            # إرسال إشعار للأدمن
            section = SectionDatabase.get_section_by_code(section_code)
            if section:
                admin = UserDatabase.get_user_by_id(section['admin_id'])
                if admin:
                    # تنسيق رسالة طلب التسجيل
                    request_message = MessageFormatter.format_registration_request_message(
                        full_name=full_name,
                        username=user_info['username'],
                        telegram_id=user_info['telegram_id'],
                        section_name=section_name
                    )
                    
                    # إنشاء أزرار الموافقة/الرفض
                    markup = types.InlineKeyboardMarkup()
                    markup.row(
                        types.InlineKeyboardButton(
                            "✅ موافقة",
                            callback_data=f"approve_{user_info['telegram_id']}_{section['section_id']}"
                        ),
                        types.InlineKeyboardButton(
                            "❌ رفض",
                            callback_data=f"reject_{user_info['telegram_id']}_{section['section_id']}"
                        )
                    )
                    
                    try:
                        bot.send_message(
                            admin['telegram_id'],
                            request_message,
                            reply_markup=markup
                        )
                    except Exception as e:
                        logger.error(f"❌ خطأ في إرسال إشعار للأدمن: {e}")
        else:
            bot.send_message(
                message.chat.id,
                f"❌ {msg}"
            )
        
        bot.delete_state(message.from_user.id, message.chat.id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة اسم الطالب: {e}")
        bot.send_message(
            message.chat.id,
            Config.Messages.ERROR_GENERAL
        )
        bot.delete_state(message.from_user.id, message.chat.id)


# ==================== معالجات أزرار الموافقة/الرفض ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_') or call.data.startswith('reject_'))
def handle_approval_decision(call: types.CallbackQuery):
    """معالج أزرار الموافقة والرفض"""
    try:
        # تحليل البيانات
        parts = call.data.split('_')
        action = parts[0]  # approve أو reject
        student_telegram_id = int(parts[1])
        section_id = int(parts[2])
        
        admin_telegram_id = call.from_user.id
        
        # تنفيذ الإجراء
        if action == 'approve':
            success, msg = StudentDatabase.approve_student(
                admin_telegram_id=admin_telegram_id,
                student_telegram_id=student_telegram_id,
                section_id=section_id
            )
            
            if success:
                # تحديث الرسالة
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=call.message.text + "\n\n✅ تمت الموافقة على الطالب"
                )
                
                # إرسال إشعار للطالب
                try:
                    section = SectionDatabase.get_section_by_id(section_id)
                    bot.send_message(
                        student_telegram_id,
                        f"🎉 مبروك! تمت الموافقة على تسجيلك في {section['section_name']}\n\n"
                        "يمكنك الآن استلام الواجبات والإشعارات."
                    )
                except Exception as e:
                    logger.error(f"❌ خطأ في إرسال إشعار الموافقة للطالب: {e}")
                
                bot.answer_callback_query(call.id, "✅ تمت الموافقة")
            else:
                bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
        
        elif action == 'reject':
            success, msg = StudentDatabase.reject_student(
                admin_telegram_id=admin_telegram_id,
                student_telegram_id=student_telegram_id,
                section_id=section_id
            )
            
            if success:
                # تحديث الرسالة
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=call.message.text + "\n\n❌ تم رفض الطالب"
                )
                
                # إرسال إشعار للطالب
                try:
                    bot.send_message(
                        student_telegram_id,
                        "😔 عذراً، تم رفض طلب تسجيلك.\n\n"
                        "للاستفسار، تواصل مع أدمن الشعبة."
                    )
                except Exception as e:
                    logger.error(f"❌ خطأ في إرسال إشعار الرفض للطالب: {e}")
                
                bot.answer_callback_query(call.id, "✅ تم رفض الطالب")
            else:
                bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة قرار الموافقة/الرفض: {e}")
        bot.answer_callback_query(call.id, Config.Messages.ERROR_GENERAL, show_alert=True)


# ==================== معالجات أزرار المالك ====================

@bot.message_handler(func=lambda message: message.text == '➕ إنشاء شعبة')
def handle_create_section_button(message: types.Message):
    """معالج زر إنشاء شعبة"""
    try:
        telegram_id = message.from_user.id
        
        # التحقق من الصلاحية
        has_permission, error = check_permission(telegram_id, 'owner')
        
        if not has_permission:
            bot.send_message(message.chat.id, f"❌ {error}")
            return
        
        # بدء عملية إنشاء الشعبة
        levels = get_academic_levels()
        
        if not levels:
            bot.send_message(message.chat.id, "❌ لا توجد مراحل دراسية")
            return
        
        # إنشاء أزرار المراحل
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for level in levels:
            markup.add(types.KeyboardButton(level['level_name']))
        markup.add(types.KeyboardButton('❌ إلغاء'))
        
        bot.send_message(
            message.chat.id,
            "📚 اختر المرحلة الدراسية:",
            reply_markup=markup
        )
        
        bot.set_state(
            message.from_user.id,
            BotStates.create_section_level,
            message.chat.id
        )
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة زر إنشاء شعبة: {e}")
        bot.send_message(message.chat.id, Config.Messages.ERROR_GENERAL)


@bot.message_handler(func=lambda message: message.text == '📋 عرض الشعب')
def handle_list_sections_button(message: types.Message):
    """معالج زر عرض الشعب"""
    try:
        telegram_id = message.from_user.id
        
        # التحقق من الصلاحية
        user = UserDatabase.get_user(telegram_id)
        
        if not user:
            bot.send_message(message.chat.id, Config.Messages.ERROR_NO_PERMISSION)
            return
        
        sections = []
        
        if user['user_type'] == 'owner':
            sections = SectionDatabase.get_all_sections()
        elif user['user_type'] == 'admin':
            sections = SectionDatabase.get_admin_sections(telegram_id)
        
        if not sections:
            bot.send_message(message.chat.id, "لا توجد شعب")
            return
        
        message_text = "📋 قائمة الشعب:\n\n"
        
        for section in sections:
            message_text += f"🏷️ {section['section_name']}\n"
            
            if 'admin_name' in section and section['admin_name']:
                message_text += f"👨‍💼 الأدمن: {section['admin_name']}\n"
            
            message_text += f"🔗 رابط التسجيل:\n{get_bot_link(section['join_code'])}\n"
            message_text += "─" * 30 + "\n\n"
        
        send_long_message(message.chat.id, message_text)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة زر عرض الشعب: {e}")
        bot.send_message(message.chat.id, Config.Messages.ERROR_GENERAL)


@bot.message_handler(func=lambda message: message.text == '📊 الإحصائيات')
def handle_statistics_button(message: types.Message):
    """معالج زر الإحصائيات"""
    try:
        telegram_id = message.from_user.id
        user = UserDatabase.get_user(telegram_id)
        
        if not user:
            bot.send_message(message.chat.id, Config.Messages.ERROR_NO_PERMISSION)
            return
        
        if user['user_type'] == 'owner':
            stats = StatisticsDatabase.get_owner_statistics()
        elif user['user_type'] == 'admin':
            stats = StatisticsDatabase.get_admin_statistics(telegram_id)
        else:
            bot.send_message(message.chat.id, Config.Messages.ERROR_NO_PERMISSION)
            return
        
        if not stats:
            bot.send_message(message.chat.id, "لا توجد إحصائيات")
            return
        
        stats_message = MessageFormatter.format_statistics(stats)
        bot.send_message(message.chat.id, stats_message)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة زر الإحصائيات: {e}")
        bot.send_message(message.chat.id, Config.Messages.ERROR_GENERAL)


# ==================== معالجات أزرار الأدمن ====================

@bot.message_handler(func=lambda message: message.text == '⏳ الطلبات المعلقة')
def handle_pending_requests_button(message: types.Message):
    """معالج زر الطلبات المعلقة"""
    try:
        telegram_id = message.from_user.id
        
        # التحقق من الصلاحية
        has_permission, error = check_permission(telegram_id, 'admin')
        
        if not has_permission:
            bot.send_message(message.chat.id, f"❌ {error}")
            return
        
        # الحصول على شعب الأدمن
        sections = SectionDatabase.get_admin_sections(telegram_id)
        
        if not sections:
            bot.send_message(message.chat.id, "❌ ليس لديك شعب")
            return
        
        # الحصول على الطلبات المعلقة
        total_pending = 0
        message_text = "⏳ الطلبات المعلقة:\n\n"
        
        for section in sections:
            pending_students = StudentDatabase.get_pending_students(section['section_id'])
            
            if pending_students:
                message_text += f"📚 {section['section_name']}\n"
                total_pending += len(pending_students)
                
                for student in pending_students:
                    username_part = student['username'] if student['username'] else "بدون username"
                    message_text += f"  • {student['full_name']} ({username_part})\n"
                    
                    # إضافة أزرار الموافقة/الرفض
                    markup = types.InlineKeyboardMarkup()
                    markup.row(
                        types.InlineKeyboardButton(
                            "✅ موافقة",
                            callback_data=f"approve_{student['telegram_id']}_{section['section_id']}"
                        ),
                        types.InlineKeyboardButton(
                            "❌ رفض",
                            callback_data=f"reject_{student['telegram_id']}_{section['section_id']}"
                        )
                    )
                    
                    bot.send_message(
                        message.chat.id,
                        f"👤 {student['full_name']}\n"
                        f"🆔 {username_part}\n"
                        f"📚 {section['section_name']}",
                        reply_markup=markup
                    )
                
                message_text += "\n"
        
        if total_pending == 0:
            bot.send_message(message.chat.id, "✅ لا توجد طلبات معلقة")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة زر الطلبات المعلقة: {e}")
        bot.send_message(message.chat.id, Config.Messages.ERROR_GENERAL)


# ==================== معالجات أزرار الطالب ====================

@bot.message_handler(func=lambda message: message.text == '📚 واجباتي')
def handle_my_assignments_button(message: types.Message):
    """معالج زر واجباتي"""
    try:
        telegram_id = message.from_user.id
        
        # الحصول على شعبة الطالب
        section = StudentDatabase.get_student_section(telegram_id)
        
        if not section:
            bot.send_message(
                message.chat.id,
                Config.Messages.ERROR_NOT_REGISTERED
            )
            return
        
        # الحصول على الواجبات
        assignments = AssignmentDatabase.get_section_assignments(section['section_id'])
        
        if not assignments:
            bot.send_message(message.chat.id, "✅ لا توجد واجبات حالياً")
            return
        
        message_text = "📚 واجباتك:\n\n"
        
        for assignment in assignments:
            deadline = datetime.fromisoformat(assignment['deadline'])
            
            message_text += f"📖 {assignment['subject_name']}\n"
            message_text += f"📌 {assignment['title']}\n"
            message_text += f"⏰ {DateTimeHelper.format_datetime(deadline)}\n"
            message_text += f"⏳ {DateTimeHelper.get_remaining_time(deadline)}\n"
            message_text += "─" * 30 + "\n\n"
        
        send_long_message(message.chat.id, message_text)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة زر واجباتي: {e}")
        bot.send_message(message.chat.id, Config.Messages.ERROR_GENERAL)


@bot.message_handler(func=lambda message: message.text == 'ℹ️ معلومات الشعبة')
def handle_section_info_button(message: types.Message):
    """معالج زر معلومات الشعبة"""
    try:
        telegram_id = message.from_user.id
        
        # الحصول على شعبة الطالب
        section = StudentDatabase.get_student_section(telegram_id)
        
        if not section:
            bot.send_message(
                message.chat.id,
                Config.Messages.ERROR_NOT_REGISTERED
            )
            return
        
        info_text = f"""
ℹ️ معلومات الشعبة

🏷️ الاسم: {section['section_name']}
📖 المرحلة: {section['level_name']}
📅 نوع الدراسة: {section['study_type']}
🔤 الشعبة: {section['division']}
"""
        
        bot.send_message(message.chat.id, info_text)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة زر معلومات الشعبة: {e}")
        bot.send_message(message.chat.id, Config.Messages.ERROR_GENERAL)


# ==================== دالة إرسال الإشعارات ====================

def send_assignment_notifications(
    assignment_id: int,
    section_id: int,
    notification_type: str = 'new'
) -> Dict[str, int]:
    """
    إرسال إشعارات الواجب لجميع الطلاب
    
    Args:
        assignment_id: معرف الواجب
        section_id: معرف الشعبة
        notification_type: نوع الإشعار
    
    Returns:
        قاموس يحتوي على إحصائيات الإرسال
    """
    try:
        # الحصول على معلومات الواجب
        assignment = AssignmentDatabase.get_assignment_by_id(assignment_id)
        
        if not assignment:
            logger.error(f"❌ الواجب {assignment_id} غير موجود")
            return {'sent': 0, 'failed': 0, 'blocked': 0}
        
        # الحصول على الطلاب الموافق عليهم
        students = StudentDatabase.get_approved_students(section_id)
        
        if not students:
            logger.info(f"ℹ️ لا يوجد طلاب في الشعبة {section_id}")
            return {'sent': 0, 'failed': 0, 'blocked': 0}
        
        # تنسيق رسالة الواجب
        deadline = datetime.fromisoformat(assignment['deadline'])
        
        if notification_type == 'new':
            message_text = MessageFormatter.format_assignment_message(
                subject_name=assignment['subject_name'],
                title=assignment['title'],
                description=assignment['description'],
                deadline=deadline
            )
        elif notification_type == 'edit':
            message_text = f"⚠️ تم تعديل واجب\n\n{MessageFormatter.format_assignment_message(assignment['subject_name'], assignment['title'], assignment['description'], deadline)}"
        elif notification_type == 'delete':
            message_text = f"🗑️ تم إلغاء واجب {assignment['title']} في مادة {assignment['subject_name']}"
        else:
            message_text = MessageFormatter.format_assignment_message(
                assignment['subject_name'],
                assignment['title'],
                assignment['description'],
                deadline
            )
        
        # إرسال الإشعارات
        stats = {'sent': 0, 'failed': 0, 'blocked': 0}
        
        for student in students:
            try:
                bot.send_message(student['telegram_id'], message_text)
                
                # تسجيل الإشعار
                NotificationDatabase.log_notification(
                    assignment_id=assignment_id,
                    student_telegram_id=student['telegram_id'],
                    notification_type=notification_type,
                    delivery_status='sent'
                )
                
                stats['sent'] += 1
                
                # تأخير صغير لتجنب الحظر
                time.sleep(Config.NOTIFICATION_DELAY_SECONDS)
                
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال إشعار للطالب {student['telegram_id']}: {e}")
                
                if "blocked" in str(e).lower():
                    delivery_status = 'blocked'
                    stats['blocked'] += 1
                else:
                    delivery_status = 'failed'
                    stats['failed'] += 1
                
                # تسجيل الفشل
                NotificationDatabase.log_notification(
                    assignment_id=assignment_id,
                    student_telegram_id=student['telegram_id'],
                    notification_type=notification_type,
                    delivery_status=delivery_status
                )
        
        logger.info(f"✅ تم إرسال الإشعارات: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال الإشعارات: {e}")
        return {'sent': 0, 'failed': 0, 'blocked': 0}


# ==================== دالة بدء البوت ====================

def start_bot():
    """بدء تشغيل البوت"""
    try:
        logger.info("=" * 60)
        logger.info("🤖 بدء تشغيل بوت الواجبات الجامعي")
        logger.info(f"📝 اسم البوت: {Config.BOT_NAME}")
        logger.info(f"🆔 Username: @{Config.BOT_USERNAME}")
        logger.info("=" * 60)
        
        # بدء استقبال الرسائل
        logger.info("✅ البوت يعمل الآن...")
        bot.infinity_polling()
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
        raise


if __name__ == "__main__":
    start_bot()

