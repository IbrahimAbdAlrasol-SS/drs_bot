#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
برنامج نصي لإعداد حساب المالك بسهولة
يطلب من المستخدم إدخال البيانات ويضيف المالك إلى قاعدة البيانات
"""

import os
import sys

# حل مشكلة encoding في Windows
if sys.platform.startswith('win'):
    import codecs
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from database import UserDatabase
from config import Config


def setup_owner():
    """إعداد حساب المالك"""
    
    print("=" * 60)
    print("👑 إعداد حساب المالك")
    print("=" * 60)
    
    # التحقق من وجود قاعدة البيانات
    if not os.path.exists(Config.DB_PATH):
        print("\n❌ قاعدة البيانات غير موجودة!")
        print("الرجاء تشغيل: python create_database.py أولاً")
        return False
    
    # طلب البيانات من المستخدم
    print("\nللحصول على معرف تلغرام الخاص بك:")
    print("أرسل رسالة لـ @userinfobot في تلغرام\n")
    
    try:
        # معرف تلغرام
        telegram_id_input = input("أدخل معرف تلغرام الخاص بك: ").strip()
        
        if not telegram_id_input.isdigit():
            print("❌ معرف تلغرام يجب أن يكون رقم")
            return False
        
        telegram_id = int(telegram_id_input)
        
        # الاسم الكامل
        full_name = input("أدخل اسمك الكامل: ").strip()
        
        if not full_name or len(full_name) < 3:
            print("❌ الاسم يجب أن يكون 3 أحرف على الأقل")
            return False
        
        # اسم المستخدم (اختياري)
        username_input = input("أدخل username في تلغرام (اختياري، اضغط Enter للتخطي): ").strip()
        username = None
        
        if username_input:
            if not username_input.startswith('@'):
                username = f"@{username_input}"
            else:
                username = username_input
        
        # التأكيد
        print("\n" + "-" * 60)
        print("📋 البيانات المُدخلة:")
        print(f"   معرف تلغرام: {telegram_id}")
        print(f"   الاسم الكامل: {full_name}")
        print(f"   Username: {username if username else 'بدون'}")
        print("-" * 60)
        
        confirm = input("\nهل البيانات صحيحة؟ (نعم/لا): ").strip().lower()
        
        if confirm not in ['نعم', 'yes', 'y', 'ن']:
            print("❌ تم الإلغاء")
            return False
        
        # إنشاء المالك
        print("\n⏳ جارِ إنشاء حساب المالك...")
        
        success, message, user_id = UserDatabase.create_user(
            telegram_id=telegram_id,
            full_name=full_name,
            user_type='owner',
            username=username
        )
        
        if success:
            print("\n" + "=" * 60)
            print("✅ تم إنشاء حساب المالك بنجاح!")
            print(f"📝 معرف المستخدم: {user_id}")
            print("=" * 60)
            print("\nالخطوات التالية:")
            print("1. شغّل البوت: python bot.py")
            print("2. أرسل /start للبوت في تلغرام")
            print("3. استمتع بإدارة البوت! 🎉")
            print("=" * 60)
            return True
        else:
            print(f"\n❌ خطأ: {message}")
            
            if "موجود مسبقاً" in message:
                print("\nℹ️ المالك موجود بالفعل في قاعدة البيانات")
                print("يمكنك البدء في استخدام البوت مباشرة")
            
            return False
        
    except KeyboardInterrupt:
        print("\n\n❌ تم الإلغاء بواسطة المستخدم")
        return False
    
    except Exception as e:
        print(f"\n❌ حدث خطأ غير متوقع: {e}")
        return False


def main():
    """الدالة الرئيسية"""
    
    success = setup_owner()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

