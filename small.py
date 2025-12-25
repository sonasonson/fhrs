#!/usr/bin/env python3
"""
سكربت سريع لتحويل جودة الفيديو إلى 240p وتقليل الحجم
"""

import os
import sys
import subprocess
import glob

def check_ffmpeg():
    """التحقق من وجود ffmpeg"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except:
        print("[!] ffmpeg غير مثبت")
        print("[*] جاري التثبيت...")
        try:
            subprocess.run(['sudo', 'apt', 'update'], check=True)
            subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], check=True)
            return True
        except:
            print("[!] فشل تثبيت ffmpeg")
            return False

def fast_compress_240p(input_file, output_file=None, crf=30):
    """
    تحويل سريع إلى 240p مع تقليل الحجم
    """
    if not os.path.exists(input_file):
        print(f"[!] الملف غير موجود: {input_file}")
        return False
    
    if output_file is None:
        name, ext = os.path.splitext(input_file)
        output_file = f"{name}_240p.mp4"
    
    print(f"[*] تحويل: {os.path.basename(input_file)}")
    print(f"[*] الإخراج: {os.path.basename(output_file)}")
    
    # الحجم الأصلي
    original_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
    
    # أبسط وأسرع أمر للتحويل إلى 240p
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-vf', 'scale=-2:240',          # تحويل إلى 240p مع الحفاظ على النسبة
        '-c:v', 'libx264',
        '-crf', str(crf),               # ضغط أعلى
        '-preset', 'fast',              # سرعة تنفيذ
        '-c:a', 'aac',
        '-b:a', '64k',                  # صوت منخفض
        '-y',                           # نعم للكتابة فوق
        output_file
    ]
    
    try:
        print("[*] جاري التحويل...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_file):
            new_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            reduction = ((original_size - new_size) / original_size) * 100
            
            print(f"[✓] تم التحويل بنجاح!")
            print(f"    من: {original_size:.1f} MB")
            print(f"    إلى: {new_size:.1f} MB")
            print(f"    توفير: {reduction:.1f}%")
            return True
        else:
            print(f"[!] فشل التحويل")
            return False
            
    except Exception as e:
        print(f"[!] خطأ: {e}")
        return False

def batch_compress_240p(folder_path, crf=30):
    """تحويل جميع الفيديوهات في مجلد"""
    video_files = []
    
    # البحث عن ملفات الفيديو
    for ext in ['*.mp4', '*.mkv', '*.avi', '*.mov']:
        video_files.extend(glob.glob(os.path.join(folder_path, ext)))
        video_files.extend(glob.glob(os.path.join(folder_path, ext.upper())))
    
    if not video_files:
        print("[!] لم يتم العثور على ملفات فيديو")
        return
    
    print(f"[*] تم العثور على {len(video_files)} ملف فيديو")
    
    # إنشاء مجلد للنتائج
    output_folder = os.path.join(folder_path, "240p")
    os.makedirs(output_folder, exist_ok=True)
    
    successful = 0
    
    for video_file in video_files:
        filename = os.path.basename(video_file)
        name, ext = os.path.splitext(filename)
        output_file = os.path.join(output_folder, f"{name}_240p.mp4")
        
        if fast_compress_240p(video_file, output_file, crf):
            successful += 1
    
    print(f"\n[*] اكتمل التحويل: {successful}/{len(video_files)}")

def simple_menu():
    """واجهة بسيطة"""
    print("="*50)
    print("تحويل سريع إلى 240p")
    print("="*50)
    
    if not check_ffmpeg():
        return
    
    while True:
        print("\n1. تحويل ملف واحد")
        print("2. تحويل مجلد كامل")
        print("3. الخروج")
        
        choice = input("\nاختر [1-3]: ").strip()
        
        if choice == '1':
            file_path = input("أدخل مسار الملف: ").strip()
            if os.path.exists(file_path):
                # اختيار مستوى الضغط
                print("\nمستوى الضغط:")
                print("1. ضغط عالي (حجم صغير)")
                print("2. ضغط متوسط")
                print("3. ضغط منخفض (جودة أفضل)")
                
                quality = input("اختر [1-3]: ").strip()
                crf_map = {'1': '32', '2': '28', '3': '24'}
                crf = int(crf_map.get(quality, '28'))
                
                fast_compress_240p(file_path, crf=crf)
            else:
                print("[!] الملف غير موجود")
                
        elif choice == '2':
            folder_path = input("أدخل مسار المجلد: ").strip()
            if os.path.isdir(folder_path):
                batch_compress_240p(folder_path)
            else:
                print("[!] المجلد غير موجود")
                
        elif choice == '3':
            print("[*] مع السلامة!")
            break
            
        else:
            print("[!] اختيار غير صحيح")

# الاستخدام من سطر الأوامر
if __name__ == "__main__":
    if len(sys.argv) == 1:
        # بدون معاملات، تشغيل الواجهة
        simple_menu()
    elif len(sys.argv) == 2:
        # ملف واحد
        if os.path.isdir(sys.argv[1]):
            batch_compress_240p(sys.argv[1])
        else:
            fast_compress_240p(sys.argv[1])
    elif len(sys.argv) == 3:
        # ملف مع ملف إخراج
        fast_compress_240p(sys.argv[1], sys.argv[2])
