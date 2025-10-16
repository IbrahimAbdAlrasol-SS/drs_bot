#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
البوت الرئيسي لنظام إدارة الواجبات الجامعية
يحتوي على جميع handlers والمنطق الأساسي للبوت
"""

import sys
import logging
import time
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

# حل مشكلة encoding في Windows
if sys.platform.startswith('win'):
    import codecs
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

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
            # إنشاء Inline Keyboard للمالك
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("➕ إنشاء شعبة", callback_data="owner_create_section"),
                types.InlineKeyboardButton("📋 عرض الشعب", callback_data="owner_list_sections")
            )
            markup.add(
                types.InlineKeyboardButton("📊 الإحصائيات", callback_data="owner_statistics"),
                types.InlineKeyboardButton("⚙️ الإعدادات", callback_data="owner_settings")
            )
        elif user_type == 'admin':
            welcome_message = Config.Messages.WELCOME_ADMIN
            # إنشاء Inline Keyboard للأدمن
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("➕ نشر واجب", callback_data="admin_create_assignment"),
                types.InlineKeyboardButton("📝 الواجبات", callback_data="admin_list_assignments")
            )
            markup.add(
                types.InlineKeyboardButton("👥 إدارة الطلاب", callback_data="admin_manage_students"),
                types.InlineKeyboardButton("⏳ الطلبات المعلقة", callback_data="admin_pending_requests")
            )
        elif user_type == 'student':
            welcome_message = Config.Messages.WELCOME_STUDENT
            # إنشاء Inline Keyboard للطالب
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("📚 واجباتي", callback_data="student_my_assignments"),
                types.InlineKeyboardButton("ℹ️ معلومات الشعبة", callback_data="student_section_info")
            )
        else:
            welcome_message = Config.Messages.WELCOME_NEW_USER
            markup = None
        
        bot.send_message(
            message.chat.id,
            welcome_message,
            reply_markup=markup
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
/myid - عرض معرف تلغرام الخاص بك
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


@bot.message_handler(commands=['myid'])
def handle_myid(message: types.Message):
    """معالج أمر /myid - عرض معرف تلغرام للمستخدم"""
    try:
        user_info = get_user_info(message)
        telegram_id = user_info['telegram_id']
        username = user_info['username']
        
        logger.info(f"📩 أمر /myid من المستخدم: {telegram_id}")
        
        myid_text = f"""
🆔 معلومات حسابك:

👤 الاسم: {message.from_user.first_name or 'غير متوفر'}
🔢 معرف تلغرام: `{telegram_id}`
📱 Username: @{username if username else 'غير متوفر'}

💡 يمكنك نسخ المعرف بالضغط عليه
"""
        
        bot.send_message(
            message.chat.id,
            myid_text,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة /myid: {e}")
        bot.send_message(
            message.chat.id,
            Config.Messages.ERROR_GENERAL
        )


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
        
        # إنشاء أزرار المراحل Inline
        markup = types.InlineKeyboardMarkup(row_width=1)
        for level in levels:
            markup.add(types.InlineKeyboardButton(
                level['level_name'],
                callback_data=f"create_sec_level_{level['level_id']}"
            ))
        markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="create_sec_cancel"))
        
        bot.send_message(
            message.chat.id,
            "📚 **إنشاء شعبة جديدة**\n\n"
            "الخطوة 1️⃣: اختر المرحلة الدراسية:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        # حفظ بداية العملية
        bot.set_state(
            message.from_user.id,
            BotStates.create_section_level,
            message.chat.id
        )
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة زر إنشاء شعبة: {e}")
        bot.send_message(message.chat.id, Config.Messages.ERROR_GENERAL)


# ==================== معالجات خطوات إنشاء الشعبة (Callback Handlers) ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith('create_sec_level_'))
def handle_section_level_selection(call: types.CallbackQuery):
    """معالج اختيار المرحلة الدراسية - الخطوة 1"""
    try:
        telegram_id = call.from_user.id
        chat_id = call.message.chat.id
        
        # استخراج level_id
        level_id = int(call.data.split('_')[-1])
        
        # الحصول على معلومات المرحلة
        levels = get_academic_levels()
        selected_level = None
        for level in levels:
            if level['level_id'] == level_id:
                selected_level = level
                break
        
        if not selected_level:
            bot.answer_callback_query(call.id, "❌ خطأ في اختيار المرحلة", show_alert=True)
            return
        
        logger.info(f"📝 المستخدم {telegram_id} اختار المرحلة: {selected_level['level_name']}")
        
        # حفظ البيانات
        with bot.retrieve_data(telegram_id, chat_id) as data:
            data['level_id'] = level_id
            data['level_name'] = selected_level['level_name']
        
        # إنشاء أزرار نوع الدراسة Inline
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.row(
            types.InlineKeyboardButton("🌅 صباحي", callback_data="create_sec_type_صباحي"),
            types.InlineKeyboardButton("🌙 مسائي", callback_data="create_sec_type_مسائي")
        )
        markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="create_sec_cancel"))
        
        # تعديل الرسالة
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"📚 **إنشاء شعبة جديدة**\n\n"
                 f"✅ المرحلة: {selected_level['level_name']}\n\n"
                 f"الخطوة 2️⃣: اختر نوع الدراسة:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id, f"✅ تم اختيار {selected_level['level_name']}")
        bot.set_state(telegram_id, BotStates.create_section_type, chat_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة اختيار المرحلة: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('create_sec_type_'))
def handle_section_type_selection(call: types.CallbackQuery):
    """معالج اختيار نوع الدراسة - الخطوة 2"""
    try:
        telegram_id = call.from_user.id
        chat_id = call.message.chat.id
        
        # استخراج نوع الدراسة
        study_type = call.data.split('_')[-1]
        
        if study_type not in Config.STUDY_TYPES:
            bot.answer_callback_query(call.id, "❌ خطأ في اختيار نوع الدراسة", show_alert=True)
            return
        
        logger.info(f"📝 المستخدم {telegram_id} اختار نوع الدراسة: {study_type}")
        
        # حفظ البيانات
        with bot.retrieve_data(telegram_id, chat_id) as data:
            data['study_type'] = study_type
            level_name = data.get('level_name')
        
        # إنشاء أزرار الشعبة Inline
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.row(
            types.InlineKeyboardButton("🅰️ شعبة A", callback_data="create_sec_div_A"),
            types.InlineKeyboardButton("🅱️ شعبة B", callback_data="create_sec_div_B")
        )
        markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="create_sec_cancel"))
        
        # تعديل الرسالة
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"📚 **إنشاء شعبة جديدة**\n\n"
                 f"✅ المرحلة: {level_name}\n"
                 f"✅ نوع الدراسة: {study_type}\n\n"
                 f"الخطوة 3️⃣: اختر الشعبة:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id, f"✅ تم اختيار {study_type}")
        bot.set_state(telegram_id, BotStates.create_section_division, chat_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة اختيار نوع الدراسة: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('create_sec_div_'))
def handle_section_division_selection(call: types.CallbackQuery):
    """معالج اختيار الشعبة (A/B) - الخطوة 3"""
    try:
        telegram_id = call.from_user.id
        chat_id = call.message.chat.id
        
        # استخراج الشعبة
        division = call.data.split('_')[-1]
        
        if division not in Config.DIVISIONS:
            bot.answer_callback_query(call.id, "❌ خطأ في اختيار الشعبة", show_alert=True)
            return
        
        logger.info(f"📝 المستخدم {telegram_id} اختار الشعبة: {division}")
        
        # حفظ البيانات
        with bot.retrieve_data(telegram_id, chat_id) as data:
            data['division'] = division
            level_name = data.get('level_name')
            study_type = data.get('study_type')
        
        # تعديل الرسالة لطلب معرف الأدمن
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"📚 **إنشاء شعبة جديدة**\n\n"
                 f"✅ المرحلة: {level_name}\n"
                 f"✅ نوع الدراسة: {study_type}\n"
                 f"✅ الشعبة: {division}\n\n"
                 f"الخطوة 4️⃣: أدخل معرف تلغرام للأدمن\n\n"
                 f"💡 للحصول على المعرف:\n"
                 f"• أرسل /myid في هذا البوت\n"
                 f"• أو أرسل /start لـ @userinfobot\n\n"
                 f"📝 أرسل المعرف الآن:",
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id, f"✅ تم اختيار شعبة {division}")
        bot.set_state(telegram_id, BotStates.create_section_admin, chat_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة اختيار الشعبة: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ", show_alert=True)


@bot.message_handler(state=BotStates.create_section_admin)
def handle_section_admin_input(message: types.Message):
    """معالج إدخال معرف الأدمن - الخطوة 4"""
    try:
        telegram_id = message.from_user.id
        chat_id = message.chat.id
        admin_input = message.text.strip()
        
        logger.info(f"📝 المستخدم {telegram_id} أدخل معرف الأدمن: {admin_input}")
        
        # معالجة الإلغاء
        if admin_input == '❌ إلغاء':
            bot.delete_state(message.from_user.id, chat_id)
            user = UserDatabase.get_user(telegram_id)
            keyboard = create_main_keyboard(user['user_type'])
            bot.send_message(
                chat_id,
                "❌ تم إلغاء عملية إنشاء الشعبة",
                reply_markup=keyboard
            )
            logger.info(f"🚫 المستخدم {telegram_id} ألغى عملية إنشاء الشعبة")
            return
        
        # التحقق من أن المدخل رقم صحيح
        if not admin_input.isdigit():
            bot.send_message(
                chat_id,
                "❌ معرف تلغرام يجب أن يكون رقماً صحيحاً\n\n"
                "الرجاء إدخال معرف تلغرام صحيح:"
            )
            return
        
        admin_telegram_id = int(admin_input)
        
        # التحقق من أن المعرف صحيح
        is_valid, error = Validator.validate_telegram_id(admin_telegram_id)
        if not is_valid:
            bot.send_message(
                chat_id,
                f"❌ {error}\n\nالرجاء إدخال معرف تلغرام صحيح:"
            )
            return
        
        # التحقق من أن المعرف ليس معرف المالك نفسه
        if admin_telegram_id == telegram_id:
            bot.send_message(
                chat_id,
                "❌ لا يمكنك تعيين نفسك كأدمن\n\n"
                "الرجاء إدخال معرف أدمن آخر:"
            )
            return
        
        # التحقق من وجود الأدمن في قاعدة البيانات
        admin_user = UserDatabase.get_user(admin_telegram_id)
        
        admin_name = "أدمن جديد"
        if admin_user:
            admin_name = admin_user['full_name']
            logger.info(f"✅ الأدمن موجود في قاعدة البيانات: {admin_name}")
        else:
            # إنشاء حساب للأدمن تلقائياً
            success, msg = UserDatabase.create_user(
                telegram_id=admin_telegram_id,
                full_name=f"Admin_{admin_telegram_id}",
                user_type='admin'
            )
            
            if success:
                admin_name = f"Admin_{admin_telegram_id}"
                logger.info(f"✅ تم إنشاء حساب أدمن جديد: {admin_name}")
            else:
                bot.send_message(
                    chat_id,
                    f"❌ خطأ في إنشاء حساب الأدمن: {msg}\n\n"
                    "الرجاء إدخال معرف آخر أو المحاولة لاحقاً:"
                )
                return
        
        # حفظ معرف الأدمن
        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            data['admin_telegram_id'] = admin_telegram_id
            data['admin_name'] = admin_name
        
        logger.info(f"✅ تم حفظ معرف الأدمن: {admin_telegram_id}")
        
        # جلب جميع البيانات لعرض الملخص
        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            level_name = data.get('level_name')
            study_type = data.get('study_type')
            division = data.get('division')
        
        # عرض ملخص الشعبة
        summary = f"""
📋 ملخص الشعبة الجديدة:

📚 المرحلة: {level_name}
📅 نوع الدراسة: {study_type}
🔤 الشعبة: {division}
👨‍💼 الأدمن: {admin_name}
🆔 معرف الأدمن: {admin_telegram_id}

⚠️ تأكد من صحة البيانات قبل الإنشاء
"""
        
        # إنشاء أزرار التأكيد
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton(
                "✅ تأكيد الإنشاء",
                callback_data="confirm_create_section"
            ),
            types.InlineKeyboardButton(
                "❌ إلغاء",
                callback_data="cancel_create_section"
            )
        )
        
        # إزالة أزرار الرد
        remove_keyboard = types.ReplyKeyboardRemove()
        
        bot.send_message(
            chat_id,
            summary,
            reply_markup=remove_keyboard
        )
        
        bot.send_message(
            chat_id,
            "اضغط على أحد الأزرار:",
            reply_markup=markup
        )
        
        logger.info(f"📋 تم عرض ملخص الشعبة للمستخدم {telegram_id}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة إدخال معرف الأدمن: {e}")
        bot.send_message(message.chat.id, Config.Messages.ERROR_GENERAL)
        bot.delete_state(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data == 'confirm_create_section')
def handle_confirm_create_section(call: types.CallbackQuery):
    """معالج تأكيد إنشاء الشعبة - الخطوة 5"""
    try:
        telegram_id = call.from_user.id
        chat_id = call.message.chat.id
        
        logger.info(f"✅ المستخدم {telegram_id} أكد إنشاء الشعبة")
        
        # جلب البيانات المحفوظة
        with bot.retrieve_data(telegram_id, chat_id) as data:
            level_id = data.get('level_id')
            study_type = data.get('study_type')
            division = data.get('division')
            admin_telegram_id = data.get('admin_telegram_id')
            level_name = data.get('level_name')
        
        # التحقق من وجود جميع البيانات
        if not all([level_id, study_type, division, admin_telegram_id]):
            bot.answer_callback_query(
                call.id,
                "❌ بيانات ناقصة! الرجاء البدء من جديد",
                show_alert=True
            )
            bot.delete_state(telegram_id, chat_id)
            return
        
        # رسالة انتظار
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="⏳ جارِ إنشاء الشعبة..."
        )
        
        # إنشاء الشعبة
        success, message_text, section_info = SectionDatabase.create_section(
            level_id=level_id,
            study_type=study_type,
            division=division,
            admin_telegram_id=admin_telegram_id,
            owner_id=telegram_id
        )
        
        if success:
            logger.info(f"✅ تم إنشاء الشعبة بنجاح: {section_info.get('section_name')}")
            
            # رسالة النجاح
            success_message = f"""
✅ تم إنشاء الشعبة بنجاح!

🏷️ الاسم: {section_info['section_name']}
🔗 رابط التسجيل:
{section_info['join_link']}

📋 شارك هذا الرابط مع الطلاب للتسجيل في الشعبة!

💡 يمكنك عرض جميع الشعب من زر "📋 عرض الشعب"
"""
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=success_message
            )
            
            # إرسال إشعار للأدمن
            try:
                admin_notification = f"""
🎉 مبروك! تم تعيينك كأدمن لشعبة جديدة

🏷️ الشعبة: {section_info['section_name']}
👑 تم التعيين بواسطة: المالك

📋 يمكنك الآن:
• إنشاء واجبات جديدة
• الموافقة على طلبات التسجيل
• إدارة الطلاب

🚀 ابدأ بإرسال /start للبوت
"""
                bot.send_message(admin_telegram_id, admin_notification)
                logger.info(f"✅ تم إرسال إشعار للأدمن: {admin_telegram_id}")
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال إشعار للأدمن: {e}")
            
            # إعادة لوحة المفاتيح الرئيسية
            user = UserDatabase.get_user(telegram_id)
            keyboard = create_main_keyboard(user['user_type'])
            bot.send_message(
                chat_id,
                "يمكنك الآن إدارة الشعب:",
                reply_markup=keyboard
            )
            
            bot.answer_callback_query(call.id, "✅ تم إنشاء الشعبة بنجاح!")
            
        else:
            logger.error(f"❌ فشل إنشاء الشعبة: {message_text}")
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ فشل إنشاء الشعبة:\n\n{message_text}"
            )
            
            # إعادة لوحة المفاتيح الرئيسية
            user = UserDatabase.get_user(telegram_id)
            keyboard = create_main_keyboard(user['user_type'])
            bot.send_message(
                chat_id,
                "يمكنك المحاولة مرة أخرى:",
                reply_markup=keyboard
            )
            
            bot.answer_callback_query(
                call.id,
                f"❌ فشل الإنشاء: {message_text}",
                show_alert=True
            )
        
        # حذف الـ state
        bot.delete_state(telegram_id, chat_id)
        logger.info(f"🔄 تم حذف الـ state للمستخدم {telegram_id}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في تأكيد إنشاء الشعبة: {e}")
        bot.answer_callback_query(
            call.id,
            Config.Messages.ERROR_GENERAL,
            show_alert=True
        )
        bot.delete_state(call.from_user.id, call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data == 'create_sec_cancel')
def handle_cancel_create_section(call: types.CallbackQuery):
    """معالج إلغاء إنشاء الشعبة من الـ callback"""
    try:
        telegram_id = call.from_user.id
        chat_id = call.message.chat.id
        
        logger.info(f"🚫 المستخدم {telegram_id} ألغى إنشاء الشعبة")
        
        # حذف الـ state
        bot.delete_state(telegram_id, chat_id)
        
        # تحديث الرسالة
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="❌ **تم إلغاء عملية إنشاء الشعبة**",
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id, "✅ تم الإلغاء")
        
    except Exception as e:
        logger.error(f"❌ خطأ في إلغاء إنشاء الشعبة: {e}")
        bot.answer_callback_query(
            call.id,
            Config.Messages.ERROR_GENERAL,
            show_alert=True
        )


# ==================== معالجات أزرار القائمة الرئيسية ====================

@bot.callback_query_handler(func=lambda call: call.data == 'owner_create_section')
def handle_owner_create_section_inline(call: types.CallbackQuery):
    """معالج زر إنشاء شعبة من Inline"""
    try:
        telegram_id = call.from_user.id
        
        # التحقق من الصلاحية
        has_permission, error = check_permission(telegram_id, 'owner')
        
        if not has_permission:
            bot.answer_callback_query(call.id, f"❌ {error}", show_alert=True)
            return
        
        # بدء عملية إنشاء الشعبة
        levels = get_academic_levels()
        
        if not levels:
            bot.answer_callback_query(call.id, "❌ لا توجد مراحل دراسية", show_alert=True)
            return
        
        # إنشاء أزرار المراحل Inline
        markup = types.InlineKeyboardMarkup(row_width=1)
        for level in levels:
            markup.add(types.InlineKeyboardButton(
                level['level_name'],
                callback_data=f"create_sec_level_{level['level_id']}"
            ))
        markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="create_sec_cancel"))
        
        bot.send_message(
            call.message.chat.id,
            "📚 **إنشاء شعبة جديدة**\n\n"
            "الخطوة 1️⃣: اختر المرحلة الدراسية:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        # حفظ بداية العملية
        bot.set_state(
            telegram_id,
            BotStates.create_section_level,
            call.message.chat.id
        )
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة زر إنشاء شعبة: {e}")
        bot.answer_callback_query(call.id, Config.Messages.ERROR_GENERAL, show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == 'owner_list_sections')
def handle_owner_list_sections_inline(call: types.CallbackQuery):
    """معالج زر عرض الشعب من Inline"""
    try:
        telegram_id = call.from_user.id
        
        # التحقق من الصلاحية
        user = UserDatabase.get_user(telegram_id)
        
        if not user:
            bot.answer_callback_query(call.id, Config.Messages.ERROR_NO_PERMISSION, show_alert=True)
            return
        
        sections = []
        
        if user['user_type'] == 'owner':
            sections = SectionDatabase.get_all_sections()
        elif user['user_type'] == 'admin':
            sections = SectionDatabase.get_admin_sections(telegram_id)
        
        if not sections:
            bot.answer_callback_query(call.id, "لا توجد شعب", show_alert=True)
            return
        
        message_text = "📋 قائمة الشعب:\n\n"
        
        for section in sections:
            message_text += f"🏷️ {section['section_name']}\n"
            
            if 'admin_name' in section and section['admin_name']:
                message_text += f"👨‍💼 الأدمن: {section['admin_name']}\n"
            
            message_text += f"🔗 رابط التسجيل:\n{get_bot_link(section['join_code'])}\n"
            message_text += "─" * 30 + "\n\n"
        
        send_long_message(call.message.chat.id, message_text)
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة زر عرض الشعب: {e}")
        bot.answer_callback_query(call.id, Config.Messages.ERROR_GENERAL, show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == 'owner_statistics')
def handle_owner_statistics_inline(call: types.CallbackQuery):
    """معالج زر الإحصائيات من Inline"""
    bot.answer_callback_query(call.id, "⚠️ هذه الميزة قيد التطوير", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == 'owner_settings')
def handle_owner_settings_inline(call: types.CallbackQuery):
    """معالج زر الإعدادات من Inline"""
    bot.answer_callback_query(call.id, "⚠️ هذه الميزة قيد التطوير", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == 'admin_create_assignment')
def handle_admin_create_assignment_inline(call: types.CallbackQuery):
    """معالج زر نشر واجب من Inline"""
    bot.answer_callback_query(call.id, "⚠️ هذه الميزة قيد التطوير", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == 'admin_list_assignments')
def handle_admin_list_assignments_inline(call: types.CallbackQuery):
    """معالج زر الواجبات من Inline"""
    bot.answer_callback_query(call.id, "⚠️ هذه الميزة قيد التطوير", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == 'admin_manage_students')
def handle_admin_manage_students_inline(call: types.CallbackQuery):
    """معالج زر إدارة الطلاب من Inline"""
    bot.answer_callback_query(call.id, "⚠️ هذه الميزة قيد التطوير", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == 'admin_pending_requests')
def handle_admin_pending_requests_inline(call: types.CallbackQuery):
    """معالج زر الطلبات المعلقة من Inline"""
    bot.answer_callback_query(call.id, "⚠️ هذه الميزة قيد التطوير", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == 'student_my_assignments')
def handle_student_my_assignments_inline(call: types.CallbackQuery):
    """معالج زر واجباتي من Inline"""
    bot.answer_callback_query(call.id, "⚠️ هذه الميزة قيد التطوير", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == 'student_section_info')
def handle_student_section_info_inline(call: types.CallbackQuery):
    """معالج زر معلومات الشعبة من Inline"""
    bot.answer_callback_query(call.id, "⚠️ هذه الميزة قيد التطوير", show_alert=True)


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

