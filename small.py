#!/usr/bin/env python3
"""
Video Compressor - ضغط الفيديو دون تغيير الأبعاد
"""

import os
import sys
import re
import subprocess
import shutil
from pathlib import Path

def check_ffmpeg():
    """التحقق من تثبيت ffmpeg"""
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

def get_video_info(input_file):
    """الحصول على معلومات الفيديو"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,bit_rate,codec_name',
            '-of', 'json',
            input_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = eval(result.stdout)['streams'][0]
        
        # حساب حجم الملف
        file_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
        
        print(f"[*] معلومات الفيديو:")
        print(f"    الدقة: {info.get('width', '?')}x{info.get('height', '?')}")
        print(f"    المدة: {float(info.get('duration', 0)):.1f} ثانية")
        print(f"    الكودك: {info.get('codec_name', 'غير معروف')}")
        print(f"    الحجم الحالي: {file_size:.1f} MB")
        
        if 'bit_rate' in info:
            bitrate = int(info['bit_rate']) / 1000  # kbps
            print(f"    البتريت: {bitrate:.0f} kbps")
        
        return info
    except:
        print("[*] لا يمكن قراءة معلومات الفيديو")
        return None

def compress_without_scaling(input_file, output_file, crf=28, preset='slow', 
                            audio_bitrate='128k', tune='film'):
    """
    ضغط الفيديو بدون تغيير الأبعاد
    """
    if not os.path.exists(input_file):
        print(f"[!] الملف غير موجود: {input_file}")
        return False
    
    print(f"[*] ضغط الفيديو دون تغيير الأبعاد...")
    print(f"[*] الإدخال: {input_file}")
    print(f"[*] الإخراج: {output_file}")
    print(f"[*] CRF: {crf} (كلما زاد الرقم زاد الضغط)")
    print(f"[*] Preset: {preset}")
    
    original_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
    
    # بناء أمر ffmpeg بدون scale
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c:v', 'libx264',
        '-preset', preset,
        '-crf', str(crf),
        '-tune', tune,
        '-c:a', 'aac',
        '-b:a', audio_bitrate,
        '-ac', '2',
        '-ar', '44100',
        '-movflags', '+faststart',
        '-threads', '0',
        '-y',
        output_file
    ]
    
    return run_compression(cmd, input_file, output_file)

def compress_with_crf_only(input_file, output_file, crf=30):
    """
    أبسط طريقة للضغط - تغيير CRF فقط
    """
    print(f"[*] الضغط بتغيير CRF فقط: {crf}")
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c:v', 'libx264',
        '-crf', str(crf),
        '-c:a', 'copy',  # نسخ الصوت بدون تغيير
        '-y',
        output_file
    ]
    
    return run_compression(cmd, input_file, output_file)

def compress_reduce_bitrate(input_file, output_file, video_bitrate='800k', audio_bitrate='96k'):
    """
    تقليل البتريت للفيديو والصوت
    """
    print(f"[*] تقليل البتريت - فيديو: {video_bitrate}, صوت: {audio_bitrate}")
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c:v', 'libx264',
        '-b:v', video_bitrate,
        '-maxrate', video_bitrate,
        '-bufsize', str(int(video_bitrate.replace('k', '')) * 2) + 'k',
        '-c:a', 'aac',
        '-b:a', audio_bitrate,
        '-y',
        output_file
    ]
    
    return run_compression(cmd, input_file, output_file)

def compress_two_pass(input_file, output_file, video_bitrate='800k'):
    """
    ضغط ثنائي المرحلة (أفضل ضغط)
    """
    print(f"[*] ضغط ثنائي المرحلة - البتريت: {video_bitrate}")
    
    # المرحلة الأولى
    pass1_cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c:v', 'libx264',
        '-b:v', video_bitrate,
        '-pass', '1',
        '-an',  # بدون صوت في المرحلة الأولى
        '-f', 'null',
        '-y',
        '/dev/null'
    ]
    
    # المرحلة الثانية
    pass2_cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c:v', 'libx264',
        '-b:v', video_bitrate,
        '-pass', '2',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',
        output_file
    ]
    
    try:
        print("[*] المرحلة الأولى...")
        subprocess.run(pass1_cmd, capture_output=True, check=True)
        
        print("[*] المرحلة الثانية...")
        return run_compression(pass2_cmd, input_file, output_file)
    except Exception as e:
        print(f"[!] فشل الضغط ثنائي المرحلة: {e}")
        return False

def run_compression(cmd, input_file, output_file):
    """تنفيذ عملية الضغط"""
    try:
        original_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
        
        # تنفيذ الأمر مع عرض التقدم
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # تتبع التقدم
        duration = 0
        for line in process.stderr:
            if 'Duration:' in line:
                # استخراج المدة
                match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', line)
                if match:
                    hours, minutes, seconds = match.groups()
                    duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            
            if 'time=' in line and duration > 0:
                match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                if match:
                    hours, minutes, seconds = match.groups()
                    current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    progress = (current_time / duration) * 100
                    print(f"    التقدم: {progress:.1f}%", end='\r')
        
        process.wait()
        
        if process.returncode == 0:
            if os.path.exists(output_file):
                new_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
                reduction = ((original_size - new_size) / original_size) * 100
                
                print(f"\n[✓] الضغط اكتمل بنجاح!")
                print(f"    الحجم الأصلي: {original_size:.1f} MB")
                print(f"    الحجم الجديد: {new_size:.1f} MB")
                print(f"    نسبة التخفيض: {reduction:.1f}%")
                return True
            else:
                print(f"\n[!] فشل إنشاء الملف الناتج")
                return False
        else:
            print(f"\n[!] فشل عملية الضغط")
            return False
            
    except Exception as e:
        print(f"\n[!] خطأ: {e}")
        return False

def batch_compress_no_scale(folder_path, crf=28, method='crf'):
    """ضغط جميع الفيديوهات في مجلد بدون تغيير الأبعاد"""
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"[!] المجلد غير موجود: {folder_path}")
        return
    
    # إنشاء مجلد للملفات المضغوطة
    compressed_folder = folder / "مضغوط_دون_تغيير_الأبعاد"
    compressed_folder.mkdir(exist_ok=True)
    
    # العثور على ملفات الفيديو
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm']
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(list(folder.glob(f'*{ext}')))
        video_files.extend(list(folder.glob(f'*{ext.upper()}')))
    
    if not video_files:
        print("[!] لم يتم العثور على ملفات فيديو")
        return
    
    print(f"[*] تم العثور على {len(video_files)} ملف فيديو")
    
    successful = 0
    failed = []
    total_original_size = 0
    total_compressed_size = 0
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n{'='*60}")
        print(f"[*] معالجة الملف {i}/{len(video_files)}")
        print(f"[*] الملف: {video_file.name}")
        
        # معلومات الملف الأصلي
        original_size = video_file.stat().st_size / (1024 * 1024)  # MB
        total_original_size += original_size
        
        # اسم الملف الناتج
        output_file = compressed_folder / f"{video_file.stem}_مضغوط.mp4"
        
        # الضغط بالطريقة المختارة
        success = False
        
        if method == 'crf':
            success = compress_with_crf_only(str(video_file), str(output_file), crf)
        elif method == 'bitrate':
            success = compress_reduce_bitrate(str(video_file), str(output_file))
        elif method == '2pass':
            success = compress_two_pass(str(video_file), str(output_file))
        else:
            success = compress_without_scaling(str(video_file), str(output_file), crf)
        
        if success:
            compressed_size = output_file.stat().st_size / (1024 * 1024)  # MB
            total_compressed_size += compressed_size
            successful += 1
        else:
            failed.append(video_file.name)
    
    # عرض النتائج النهائية
    print(f"\n{'='*60}")
    print("[*] انتهت عملية الضغط الجماعي")
    print('='*60)
    print(f"[*] الملفات الناجحة: {successful}/{len(video_files)}")
    
    if failed:
        print(f"[*] الملفات الفاشلة: {len(failed)}")
        for f in failed:
            print(f"    - {f}")
    
    if successful > 0:
        total_reduction = ((total_original_size - total_compressed_size) / total_original_size) * 100
        print(f"\n[*] الإحصائيات:")
        print(f"    الحجم الإجمالي الأصلي: {total_original_size:.1f} MB")
        print(f"    الحجم الإجمالي المضغوط: {total_compressed_size:.1f} MB")
        print(f"    إجمالي التخفيض: {total_reduction:.1f}%")
        print(f"    التوفير: {total_original_size - total_compressed_size:.1f} MB")
    
    print(f"\n[*] الملفات المضغوطة موجودة في: {compressed_folder}")

def interactive_menu():
    """قائمة تفاعلية"""
    print("="*60)
    print("أداة ضغط الفيديو - بدون تغيير الأبعاد")
    print("="*60)
    
    # التحقق من ffmpeg
    if not check_ffmpeg():
        return
    
    while True:
        print("\n[*] الخيارات المتاحة:")
        print("    1. ضغط ملف فيديو واحد")
        print("    2. ضغط جميع الفيديوهات في مجلد")
        print("    3. عرض معلومات الفيديو")
        print("    4. الخروج")
        
        choice = input("\n[?] اختر خياراً (1-4): ").strip()
        
        if choice == '1':
            # ضغط ملف واحد
            file_path = input("[?] أدخل مسار ملف الفيديو: ").strip()
            
            if not os.path.exists(file_path):
                print("[!] الملف غير موجود")
                continue
            
            # عرض معلومات الفيديو
            get_video_info(file_path)
            
            print("\n[*] اختر طريقة الضغط:")
            print("    1. تغيير CRF فقط (بسيط)")
            print("    2. تقليل البتريت")
            print("    3. ضغط متقدم (CRF + إعدادات)")
            print("    4. ضغط ثنائي المرحلة (أفضل ضغط)")
            
            method_choice = input("[?] اختر الطريقة (1-4): ").strip()
            
            # اختيار CRF
            if method_choice in ['1', '3']:
                crf = input("[?] أدخل قيمة CRF (18-32, 28 افتراضي): ").strip()
                crf = int(crf) if crf.isdigit() and 18 <= int(crf) <= 32 else 28
            else:
                crf = 28
            
            output_path = input("[?] أدخل مسار الملف الناتج (اختياري): ").strip()
            if not output_path:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"{os.path.splitext(file_path)[0]}_مضغوط_{timestamp}.mp4"
            
            # التنفيذ حسب الطريقة
            if method_choice == '1':
                compress_with_crf_only(file_path, output_path, crf)
            elif method_choice == '2':
                compress_reduce_bitrate(file_path, output_path)
            elif method_choice == '3':
                compress_without_scaling(file_path, output_path, crf)
            elif method_choice == '4':
                compress_two_pass(file_path, output_path)
            else:
                compress_without_scaling(file_path, output_path, crf)
            
        elif choice == '2':
            # ضغط مجلد
            folder_path = input("[?] أدخل مسار المجلد: ").strip()
            
            print("\n[*] اختر طريقة الضغط:")
            print("    1. تغيير CRF فقط")
            print("    2. تقليل البتريت")
            print("    3. ضغط متقدم")
            
            method_choice = input("[?] اختر الطريقة (1-3): ").strip()
            
            methods = {'1': 'crf', '2': 'bitrate', '3': 'advanced'}
            method = methods.get(method_choice, 'crf')
            
            crf = 28
            if method == 'crf':
                crf_input = input("[?] أدخل قيمة CRF (18-32, 28 افتراضي): ").strip()
                if crf_input.isdigit():
                    crf = int(crf_input)
            
            batch_compress_no_scale(folder_path, crf=crf, method=method)
            
        elif choice == '3':
            # عرض معلومات الفيديو
            file_path = input("[?] أدخل مسار ملف الفيديو: ").strip()
            if os.path.exists(file_path):
                get_video_info(file_path)
            else:
                print("[!] الملف غير موجود")
                
        elif choice == '4':
            print("[*] مع السلامة!")
            break
            
        else:
            print("[!] خيار غير صحيح")

def main():
    """الدالة الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ضغط الفيديو بدون تغيير الأبعاد',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة:
  %(prog)s -i video.mp4 -c 30
  %(prog)s -i folder/ -m bitrate
  %(prog)s --interactive
        """
    )
    
    parser.add_argument('-i', '--input', help='مسار الملف أو المجلد')
    parser.add_argument('-o', '--output', help='مسار الملف الناتج (للملف الواحد)')
    parser.add_argument('-c', '--crf', type=int, default=28, 
                       help='جودة الفيديو CRF (18-32, 28 افتراضي)')
    parser.add_argument('-m', '--method', choices=['crf', 'bitrate', '2pass', 'advanced'],
                       default='crf', help='طريقة الضغط')
    parser.add_argument('--interactive', action='store_true', help='الوضع التفاعلي')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_menu()
    elif args.input:
        if os.path.isdir(args.input):
            batch_compress_no_scale(args.input, crf=args.crf, method=args.method)
        else:
            if not args.output:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                args.output = f"{os.path.splitext(args.input)[0]}_مضغوط_{timestamp}.mp4"
            
            if args.method == 'crf':
                compress_with_crf_only(args.input, args.output, args.crf)
            elif args.method == 'bitrate':
                compress_reduce_bitrate(args.input, args.output)
            elif args.method == '2pass':
                compress_two_pass(args.input, args.output)
            else:
                compress_without_scaling(args.input, args.output, args.crf)
    else:
        # بدون معاملات، تشغيل الوضع التفاعلي
        interactive_menu()

if __name__ == "__main__":
    main()
