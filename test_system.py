#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
برنامج نصي لاختبار وظائف النظام الأساسية
يتحقق من أن جميع المكونات تعمل بشكل صحيح
"""

import os
import sys
from datetime import datetime, timedelta

# إضافة المجلد الحالي للمسار
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import (
    UserDatabase, SectionDatabase, StudentDatabase,
    AssignmentDatabase, get_academic_levels, get_subjects
)
from helpers import (
    CodeGenerator, DateTimeHelper, MessageFormatter,
    Validator, PermissionChecker
)


def print_header(text: str):
    """طباعة رأس منسق"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def test_database_connection():
    """اختبار الاتصال بقاعدة البيانات"""
    print_header("🔌 اختبار الاتصال بقاعدة البيانات")
    
    try:
        if not os.path.exists(Config.DB_PATH):
            print("❌ قاعدة البيانات غير موجودة")
            print("   الرجاء تشغيل: python create_database.py")
            return False
        
        # اختبار جلب المراحل الدراسية
        levels = get_academic_levels()
        
        if levels:
            print(f"✅ تم الاتصال بقاعدة البيانات بنجاح")
            print(f"   عدد المراحل الدراسية: {len(levels)}")
            for level in levels:
                print(f"   - {level['level_name']}")
            return True
        else:
            print("❌ قاعدة البيانات فارغة")
            return False
    
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False


def test_code_generation():
    """اختبار توليد الأكواد الفريدة"""
    print_header("🔑 اختبار توليد الأكواد الفريدة")
    
    try:
        codes = set()
        
        # توليد 10 أكواد
        for i in range(10):
            code = CodeGenerator.generate_section_code()
            codes.add(code)
            print(f"   {i+1}. {code}")
        
        # التحقق من عدم التكرار
        if len(codes) == 10:
            print("\n✅ جميع الأكواد فريدة")
            return True
        else:
            print(f"\n❌ توجد أكواد مكررة ({len(codes)}/10)")
            return False
    
    except Exception as e:
        print(f"❌ خطأ في توليد الأكواد: {e}")
        return False


def test_date_formatting():
    """اختبار تنسيق التواريخ"""
    print_header("📅 اختبار تنسيق التواريخ")
    
    try:
        # التاريخ الحالي
        now = DateTimeHelper.get_current_datetime()
        print(f"   التاريخ الحالي: {DateTimeHelper.format_datetime(now)}")
        
        # موعد نهائي بعد يومين
        deadline = now + timedelta(days=2, hours=5, minutes=30)
        print(f"   موعد نهائي: {DateTimeHelper.format_datetime(deadline)}")
        
        # حساب الوقت المتبقي
        remaining = DateTimeHelper.get_remaining_time(deadline)
        print(f"   الوقت المتبقي: {remaining}")
        
        print("\n✅ تنسيق التواريخ يعمل بشكل صحيح")
        return True
    
    except Exception as e:
        print(f"❌ خطأ في تنسيق التواريخ: {e}")
        return False


def test_validators():
    """اختبار دوال التحقق"""
    print_header("✔️ اختبار دوال التحقق")
    
    try:
        tests = []
        
        # اختبار التحقق من الاسم
        is_valid, _ = Validator.validate_full_name("أحمد محمد علي")
        tests.append(("اسم صحيح", is_valid))
        
        is_valid, _ = Validator.validate_full_name("أ")
        tests.append(("اسم قصير (يجب أن يفشل)", not is_valid))
        
        # اختبار التحقق من كود الشعبة
        code = CodeGenerator.generate_section_code()
        is_valid = Validator.validate_section_code(code)
        tests.append(("كود شعبة صحيح", is_valid))
        
        is_valid = Validator.validate_section_code("INVALID_CODE")
        tests.append(("كود شعبة خاطئ (يجب أن يفشل)", not is_valid))
        
        # اختبار التحقق من العنوان
        is_valid, _ = Validator.validate_assignment_title("واجب المصفوفات")
        tests.append(("عنوان واجب صحيح", is_valid))
        
        # اختبار التحقق من الموعد النهائي
        future_deadline = DateTimeHelper.get_current_datetime() + timedelta(days=7)
        is_valid, _ = Validator.validate_deadline(future_deadline)
        tests.append(("موعد نهائي في المستقبل", is_valid))
        
        past_deadline = DateTimeHelper.get_current_datetime() - timedelta(days=1)
        is_valid, _ = Validator.validate_deadline(past_deadline)
        tests.append(("موعد نهائي في الماضي (يجب أن يفشل)", not is_valid))
        
        # عرض النتائج
        all_passed = True
        for test_name, result in tests:
            status = "✅" if result else "❌"
            print(f"   {status} {test_name}")
            if not result:
                all_passed = False
        
        if all_passed:
            print(f"\n✅ جميع الاختبارات نجحت ({len(tests)}/{len(tests)})")
        else:
            failed = sum(1 for _, result in tests if not result)
            print(f"\n⚠️ بعض الاختبارات فشلت ({len(tests)-failed}/{len(tests)})")
        
        return all_passed
    
    except Exception as e:
        print(f"❌ خطأ في اختبار دوال التحقق: {e}")
        return False


def test_message_formatting():
    """اختبار تنسيق الرسائل"""
    print_header("💬 اختبار تنسيق الرسائل")
    
    try:
        # تنسيق اسم الشعبة
        section_name = MessageFormatter.format_section_name(
            "المرحلة الأولى", "صباحي", "A"
        )
        print(f"   اسم الشعبة: {section_name}")
        
        # تنسيق رسالة الواجب
        deadline = DateTimeHelper.get_current_datetime() + timedelta(days=2)
        assignment_msg = MessageFormatter.format_assignment_message(
            subject_name="برمجة 1",
            title="واجب المصفوفات",
            description="حل التمارين من 1 إلى 5",
            deadline=deadline
        )
        print("\n   رسالة الواجب:")
        print("   " + "-" * 50)
        for line in assignment_msg.split('\n'):
            print(f"   {line}")
        print("   " + "-" * 50)
        
        print("\n✅ تنسيق الرسائل يعمل بشكل صحيح")
        return True
    
    except Exception as e:
        print(f"❌ خطأ في تنسيق الرسائل: {e}")
        return False


def test_subjects_and_levels():
    """اختبار المواد والمراحل"""
    print_header("📚 اختبار المواد والمراحل الدراسية")
    
    try:
        # المراحل الدراسية
        levels = get_academic_levels()
        print(f"   المراحل الدراسية ({len(levels)}):")
        for level in levels:
            print(f"   - {level['level_name']}")
        
        # المواد
        subjects = get_subjects()
        print(f"\n   المواد ({len(subjects)}):")
        for subject in subjects:
            print(f"   - {subject['subject_name']}")
        
        if levels and subjects:
            print("\n✅ المراحل والمواد موجودة في قاعدة البيانات")
            return True
        else:
            print("\n❌ لا توجد مراحل أو مواد")
            return False
    
    except Exception as e:
        print(f"❌ خطأ في جلب المراحل والمواد: {e}")
        return False


def run_all_tests():
    """تشغيل جميع الاختبارات"""
    print("\n" + "=" * 60)
    print("  🧪 اختبار نظام بوت الواجبات الجامعي")
    print("=" * 60)
    
    tests = [
        ("الاتصال بقاعدة البيانات", test_database_connection),
        ("توليد الأكواد الفريدة", test_code_generation),
        ("تنسيق التواريخ", test_date_formatting),
        ("دوال التحقق", test_validators),
        ("تنسيق الرسائل", test_message_formatting),
        ("المواد والمراحل", test_subjects_and_levels)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ خطأ في اختبار {test_name}: {e}")
            results.append((test_name, False))
    
    # عرض النتائج النهائية
    print_header("📊 ملخص النتائج")
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ نجح" if result else "❌ فشل"
        print(f"   {status}: {test_name}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    total = len(results)
    percentage = (passed / total) * 100 if total > 0 else 0
    
    print("\n" + "-" * 60)
    print(f"   الإجمالي: {passed}/{total} ({percentage:.1f}%)")
    print("-" * 60)
    
    if failed == 0:
        print("\n🎉 جميع الاختبارات نجحت! النظام جاهز للاستخدام.")
        return True
    else:
        print(f"\n⚠️ {failed} اختبار(ات) فشل. الرجاء مراجعة الأخطاء.")
        return False


def main():
    """الدالة الرئيسية"""
    try:
        success = run_all_tests()
        
        print("\n" + "=" * 60)
        
        if success:
            print("✅ النظام جاهز للاستخدام!")
            print("\nالخطوات التالية:")
            print("1. إعداد ملف .env (انسخ من env_template.txt)")
            print("2. تشغيل: python setup_owner.py")
            print("3. تشغيل البوت: python bot.py")
        else:
            print("❌ يوجد مشاكل في النظام")
            print("الرجاء مراجعة الأخطاء أعلاه")
        
        print("=" * 60)
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n\n❌ تم الإيقاف بواسطة المستخدم")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

