#!/usr/bin/env python3
"""
Video Compressor Script
تقليل حجم ملفات الفيديو مع الحفاظ على الجودة
"""

import os
import sys
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
        return result.stdout
    except:
        return None

def compress_video_advanced(input_file, output_file, preset='balanced'):
    """
    ضغط الفيديو مع إعدادات متقدمة
    
    preset options:
    - 'small': أصغر حجم (240p, ضغط عالي)
    - 'balanced': توازن بين الجودة والحجم (360p)
    - 'good': جودة جيدة (480p)
    - 'extreme': ضغط شديد (أقل حجم ممكن)
    """
    
    presets = {
        'extreme': {
            'video': {
                'scale': '426:240',
                'crf': 32,           # ضغط عالي (18-28 عادي، 32 شديد)
                'preset': 'veryslow', # أفضل ضغط
                'bitrate': '400k',
                'tune': 'film' if 'film' in input_file.lower() else 'zerolatency'
            },
            'audio': {
                'codec': 'aac',
                'bitrate': '64k',
                'channels': '2',
                'samplerate': '44100'
            }
        },
        'small': {
            'video': {
                'scale': '426:240',
                'crf': 28,
                'preset': 'slow',
                'bitrate': '500k',
                'tune': 'film'
            },
            'audio': {
                'codec': 'aac',
                'bitrate': '96k',
                'channels': '2',
                'samplerate': '44100'
            }
        },
        'balanced': {
            'video': {
                'scale': '640:360',
                'crf': 26,
                'preset': 'medium',
                'bitrate': '800k',
                'tune': 'film'
            },
            'audio': {
                'codec': 'aac',
                'bitrate': '128k',
                'channels': '2',
                'samplerate': '44100'
            }
        },
        'good': {
            'video': {
                'scale': '854:480',
                'crf': 24,
                'preset': 'medium',
                'bitrate': '1200k',
                'tune': 'film'
            },
            'audio': {
                'codec': 'aac',
                'bitrate': '128k',
                'channels': '2',
                'samplerate': '44100'
            }
        }
    }
    
    preset_config = presets.get(preset, presets['balanced'])
    
    print(f"[*] إعدادات الضغط: {preset}")
    print(f"[*] الدقة: {preset_config['video']['scale']}")
    print(f"[*] جودة الفيديو (CRF): {preset_config['video']['crf']}")
    
    # بناء أمر ffmpeg
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-vf', f"scale={preset_config['video']['scale']}",
        '-c:v', 'libx264',
        '-preset', preset_config['video']['preset'],
        '-crf', str(preset_config['video']['crf']),
        '-maxrate', preset_config['video']['bitrate'],
        '-bufsize', str(int(preset_config['video']['bitrate'].replace('k', '')) * 2) + 'k',
        '-tune', preset_config['video']['tune'],
        '-c:a', preset_config['audio']['codec'],
        '-b:a', preset_config['audio']['bitrate'],
        '-ac', preset_config['audio']['channels'],
        '-ar', preset_config['audio']['samplerate'],
        '-movflags', '+faststart',
        '-threads', '0',  # استخدام جميع الأنوية
        '-y',
        output_file
    ]
    
    return run_compression(cmd, input_file, output_file)

def compress_video_custom(input_file, output_file, width=426, height=240, crf=28, 
                         audio_bitrate='96k', video_bitrate='500k'):
    """
    ضغط مخصص مع إعدادات يدوية
    """
    print(f"[*] الضغط المخصص: {width}x{height}")
    print(f"[*] CRF: {crf}, البتريت: {video_bitrate}")
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-vf', f"scale={width}:{height}",
        '-c:v', 'libx264',
        '-preset', 'slow',  # للحصول على أفضل ضغط
        '-crf', str(crf),
        '-maxrate', video_bitrate,
        '-bufsize', str(int(video_bitrate.replace('k', '')) * 2) + 'k',
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

def run_compression(cmd, input_file, output_file):
    """تنفيذ عملية الضغط"""
    try:
        print(f"[*] جاري ضغط: {os.path.basename(input_file)}")
        print(f"[*] قد تستغرق العملية بعض الوقت...")
        
        # الحصول على حجم الملف الأصلي
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
                import re
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

def batch_compress(folder_path, preset='small', custom_settings=None):
    """ضغط مجموعة من الفيديوهات"""
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"[!] المجلد غير موجود: {folder_path}")
        return
    
    # إنشاء مجلد للملفات المضغوطة
    compressed_folder = folder / "مضغوط"
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
        output_file = compressed_folder / f"{video_file.stem}_compressed.mp4"
        
        # الضغط
        if custom_settings:
            success = compress_video_custom(
                str(video_file), str(output_file), **custom_settings
            )
        else:
            success = compress_video_advanced(
                str(video_file), str(output_file), preset
            )
        
        if success:
            compressed_size = output_file.stat().st_size / (1024 * 1024)  # MB
            total_compressed_size += compressed_size
            successful += 1
        else:
            failed.append(video_file.name)
        
        # تأخير بسيط بين الملفات
        if i < len(video_files):
            import time
            time.sleep(1)
    
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

def interactive_mode():
    """الوضع التفاعلي"""
    print("="*60)
    print("أداة ضغط الفيديو - Video Compressor")
    print("="*60)
    
    # التحقق من ffmpeg
    if not check_ffmpeg():
        return
    
    while True:
        print("\n[*] الخيارات المتاحة:")
        print("    1. ضغط ملف فيديو واحد")
        print("    2. ضغط جميع الفيديوهات في مجلد")
        print("    3. ضغط بإعدادات مخصصة")
        print("    4. الخروج")
        
        choice = input("\n[?] اختر خياراً (1-4): ").strip()
        
        if choice == '1':
            # ضغط ملف واحد
            file_path = input("[?] أدخل مسار ملف الفيديو: ").strip()
            
            if not os.path.exists(file_path):
                print("[!] الملف غير موجود")
                continue
            
            print("\n[*] إعدادات الضغط:")
            print("    1. حجم صغير جداً (240p, ضغط عالي)")
            print("    2. حجم صغير (240p)")
            print("    3. حجم متوسط (360p)")
            print("    4. جودة جيدة (480p)")
            
            preset_choice = input("[?] اختر الإعداد (1-4): ").strip()
            presets = {'1': 'extreme', '2': 'small', '3': 'balanced', '4': 'good'}
            preset = presets.get(preset_choice, 'small')
            
            output_path = input("[?] أدخل مسار الملف الناتج (اختياري): ").strip()
            if not output_path:
                # اسم افتراضي
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"{os.path.splitext(file_path)[0]}_compressed_{timestamp}.mp4"
            
            compress_video_advanced(file_path, output_path, preset)
            
        elif choice == '2':
            # ضغط مجلد
            folder_path = input("[?] أدخل مسار المجلد: ").strip()
            
            print("\n[*] إعدادات الضغط:")
            print("    1. حجم صغير جداً (240p, ضغط عالي)")
            print("    2. حجم صغير (240p)")
            print("    3. حجم متوسط (360p)")
            print("    4. جودة جيدة (480p)")
            
            preset_choice = input("[?] اختر الإعداد (1-4): ").strip()
            presets = {'1': 'extreme', '2': 'small', '3': 'balanced', '4': 'good'}
            preset = presets.get(preset_choice, 'small')
            
            batch_compress(folder_path, preset)
            
        elif choice == '3':
            # إعدادات مخصصة
            file_path = input("[?] أدخل مسار ملف الفيديو: ").strip()
            
            if not os.path.exists(file_path):
                print("[!] الملف غير موجود")
                continue
            
            print("\n[*] الإعدادات المخصصة:")
            
            try:
                width = int(input("[?] العرض (بالنقاط) [426]: ").strip() or "426")
                height = int(input("[?] الارتفاع (بالنقاط) [240]: ").strip() or "240")
                crf = int(input("[?] جودة الفيديو (CRF: 18-32) [28]: ").strip() or "28")
                video_bitrate = input("[?] بتريت الفيديو [500k]: ").strip() or "500k"
                audio_bitrate = input("[?] بتريت الصوت [96k]: ").strip() or "96k"
            except ValueError:
                print("[!] قيم غير صحيحة")
                continue
            
            output_path = input("[?] أدخل مسار الملف الناتج (اختياري): ").strip()
            if not output_path:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"{os.path.splitext(file_path)[0]}_custom_{timestamp}.mp4"
            
            compress_video_custom(
                file_path, output_path, 
                width=width, height=height, crf=crf,
                video_bitrate=video_bitrate, audio_bitrate=audio_bitrate
            )
            
        elif choice == '4':
            print("[*] مع السلامة!")
            break
            
        else:
            print("[!] خيار غير صحيح")

def quick_compress(input_path, output_path=None, preset='small'):
    """ضغط سريع"""
    if not check_ffmpeg():
        return False
    
    if os.path.isdir(input_path):
        batch_compress(input_path, preset)
    else:
        if not output_path:
            output_path = f"{os.path.splitext(input_path)[0]}_compressed.mp4"
        
        return compress_video_advanced(input_path, output_path, preset)

# استخدام من سطر الأوامر
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='أداة ضغط الفيديو')
    parser.add_argument('-i', '--input', help='مسار الملف أو المجلد')
    parser.add_argument('-o', '--output', help='مسار الملف الناتج (للملف الواحد)')
    parser.add_argument('-p', '--preset', choices=['extreme', 'small', 'balanced', 'good'], 
                       default='small', help='إعدادات الضغط')
    parser.add_argument('-w', '--width', type=int, help='العرض المخصص')
    parser.add_argument('-h', '--height', type=int, help='الارتفاع المخصص')
    parser.add_argument('-c', '--crf', type=int, help='جودة الفيديو (CRF)')
    parser.add_argument('--interactive', action='store_true', help='الوضع التفاعلي')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    elif args.input:
        if args.width and args.height:
            # إعدادات مخصصة
            custom_settings = {
                'width': args.width,
                'height': args.height,
                'crf': args.crf or 28,
                'audio_bitrate': '96k',
                'video_bitrate': '500k'
            }
            
            if os.path.isdir(args.input):
                batch_compress(args.input, custom_settings=custom_settings)
            else:
                if not args.output:
                    args.output = f"{os.path.splitext(args.input)[0]}_custom.mp4"
                compress_video_custom(args.input, args.output, **custom_settings)
        else:
            # استخدام الإعدادات المسبقة
            quick_compress(args.input, args.output, args.preset)
    else:
        # بدون معاملات، تشغيل الوضع التفاعلي
        interactive_mode()
