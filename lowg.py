#!/usr/bin/env python3
"""
Telegram Video Uploader - Clean Version
"""

import os
import sys
import re
import time
import json
import requests
import subprocess
import shutil
import asyncio

# ===== إضافة Pyrogram بعد التثبيت =====
try:
    from pyrogram import Client
    from pyrogram.errors import FloodWait
    PYROGRAM_INSTALLED = True
except ImportError:
    print("[*] تثبيت pyrogram...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyrogram", "tgcrypto"])
    from pyrogram import Client
    from pyrogram.errors import FloodWait
    PYROGRAM_INSTALLED = True

# ===== CONFIG =====
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
HEADERS = {
    'User-Agent': USER_AGENT,
    'Referer': 'https://3seq.com/'
}

# Telegram Configuration
TELEGRAM_API_ID = 30637918
TELEGRAM_API_HASH = "4779bdfbeddb85accd6fdbe199625ac5"
TELEGRAM_PHONE = "+201121087915"
TELEGRAM_CHANNEL = "@shoofFilm"

# جلسة Pyrogram
app = None

# ===== TELEGRAM SETUP =====

async def setup_telegram():
    """إعداد Telegram"""
    global app
    
    print("[*] جاري الاتصال بـ Telegram...")
    
    try:
        app = Client(
            "my_account",
            api_id=TELEGRAM_API_ID,
            api_hash=TELEGRAM_API_HASH,
            phone_number=TELEGRAM_PHONE
        )
        
        await app.start()
        
        me = await app.get_me()
        print(f"[✓] متصل بـ: {me.first_name}")
        
        return True
        
    except Exception as e:
        print(f"[!] خطأ في الاتصال: {e}")
        return False

# ===== VIDEO DOWNLOAD =====

def download_video(url, output_path):
    """تنزيل فيديو"""
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'best[height<=480]/best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'user_agent': USER_AGENT,
        }
        
        print(f"[*] جاري التنزيل...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(output_path):
            size = os.path.getsize(output_path) / (1024*1024)
            print(f"[✓] تم التنزيل ({size:.1f}MB)")
            return True
        
        return False
        
    except Exception as e:
        print(f"[!] خطأ في التنزيل: {e}")
        return False

# ===== VIDEO COMPRESSION =====

def compress_video_with_progress(input_file, output_file, crf=28):
    """ضغط الفيديو مع شريط تقدم"""
    if not os.path.exists(input_file):
        return False
    
    original_size = os.path.getsize(input_file) / (1024 * 1024)
    
    print(f"[*] جاري الضغط...")
    
    # الحصول على مدة الفيديو
    duration = 0
    try:
        cmd_info = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            input_file
        ]
        
        result = subprocess.run(cmd_info, capture_output=True, text=True)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            duration = float(info['format'].get('duration', 0))
    except:
        pass
    
    # إعدادات الضغط المطلوبة
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-vf', 'scale=-2:480',  # 480p لجودة متوسطة
        '-c:v', 'libx264',
        '-crf', str(crf),
        '-preset', 'fast',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-progress', 'pipe:1',
        '-y',
        output_file
    ]
    
    print("[ ] 0%", end='', flush=True)
    
    start_time = time.time()
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    progress_data = {}
    
    for line in process.stdout:
        line = line.strip()
        
        if '=' in line:
            key, value = line.split('=', 1)
            progress_data[key.strip()] = value.strip()
        
        if 'out_time_ms' in progress_data:
            try:
                current_time_ms = int(progress_data['out_time_ms'])
                current_time = current_time_ms / 1000000.0
                
                if duration > 0:
                    progress_percent = min(100, (current_time / duration) * 100)
                    
                    bar_length = 25
                    filled = int(bar_length * progress_percent // 100)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    
                    elapsed = time.time() - start_time
                    if progress_percent > 0:
                        remaining = (elapsed / progress_percent) * (100 - progress_percent)
                        print(f"\r[+] {progress_percent:.1f}% |{bar}| {remaining:.0f}ث", end='', flush=True)
            except:
                pass
    
    process.wait()
    print()
    
    if process.returncode == 0 and os.path.exists(output_file):
        new_size = os.path.getsize(output_file) / (1024 * 1024)
        total_time = time.time() - start_time
        
        print(f"[✓] تم الضغط خلال {total_time:.1f}ث")
        print(f"[+] من {original_size:.1f}MB إلى {new_size:.1f}MB")
        return True
    
    return False

# ===== UPLOAD VIDEO =====

async def upload_video(file_path, series_name, season_num, episode_num):
    """رفع الفيديو إلى القناة"""
    try:
        if not app or not os.path.exists(file_path):
            return False
        
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024*1024)
        
        print(f"[*] رفع: {filename} ({file_size:.1f}MB)")
        
        # إنشاء التعليق البسيط المطلوب
        caption = f"{series_name} الموسم {season_num} الحلقة {episode_num}"
        
        start_time = time.time()
        
        # رفع الفيديو بدون عرض التقدم لتجنب المشاكل
        try:
            await app.send_video(
                chat_id=TELEGRAM_CHANNEL,
                video=file_path,
                caption=caption,
                supports_streaming=True
            )
            
            elapsed = time.time() - start_time
            print(f"[✓] تم الرفع ({elapsed:.1f}ث)")
            return True
            
        except FloodWait as e:
            print(f"[*] انتظر {e.value} ثانية...")
            await asyncio.sleep(e.value)
            return await upload_video(file_path, series_name, season_num, episode_num)
            
        except Exception as e:
            # محاولة أخرى بدون caption إذا كان هناك مشكلة
            try:
                print("[*] محاولة رفع بدون caption...")
                await app.send_video(
                    chat_id=TELEGRAM_CHANNEL,
                    video=file_path,
                    supports_streaming=True
                )
                print("[✓] تم الرفع")
                return True
            except Exception as e2:
                print(f"[!] فشل الرفع: {e2}")
                return False
        
    except Exception as e:
        print(f"[!] خطأ: {e}")
        return False

# ===== EXTRACT VIDEO URL =====

def get_video_url(episode_num, series_name, season_num):
    """الحصول على رابط الفيديو"""
    try:
        if season_num > 1:
            url = f"https://x.3seq.com/video/modablaj-{series_name}-episode-s{season_num:02d}e{episode_num:02d}"
        else:
            url = f"https://x.3seq.com/video/modablaj-{series_name}-episode-{episode_num:02d}"
        
        print(f"[*] الصفحة: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        # البحث عن رابط watch
        watch_match = re.search(r'href=["\']([^"\']+episode[^"\']+\?do=watch)["\']', response.text)
        if watch_match:
            watch_url = watch_match.group(1)
            if watch_url.startswith('//'):
                watch_url = 'https:' + watch_url
            elif watch_url.startswith('/'):
                watch_url = 'https://x.3seq.com' + watch_url
        else:
            watch_url = f"{url}-yvra/?do=watch"
        
        # الحصول على رابط الفيديو
        response = requests.get(watch_url, headers=HEADERS, timeout=15)
        iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', response.text)
        
        if not iframe_match:
            return None
        
        video_url = iframe_match.group(1)
        if video_url.startswith('//'):
            video_url = 'https:' + video_url
        elif video_url.startswith('/'):
            video_url = 'https://v.vidsp.net' + video_url
        
        return video_url
        
    except Exception as e:
        print(f"[!] خطأ: {e}")
        return None

# ===== PROCESS EPISODE =====

async def process_episode(episode_num, series_name, series_name_arabic, season_num, download_dir):
    """معالجة حلقة واحدة"""
    print(f"\n[=] الحلقة {episode_num:02d}")
    
    temp_file = os.path.join(download_dir, f"temp_{episode_num:02d}.mp4")
    final_file = os.path.join(download_dir, f"{series_name_arabic}_S{season_num:02d}_E{episode_num:02d}.mp4")
    
    # تنظيف
    for f in [temp_file, final_file]:
        if os.path.exists(f):
            os.remove(f)
    
    try:
        # 1. الحصول على الرابط
        video_url = get_video_url(episode_num, series_name, season_num)
        if not video_url:
            return False, "لم يتم العثور على الرابط"
        
        # 2. التنزيل
        if not download_video(video_url, temp_file):
            return False, "فشل التنزيل"
        
        # 3. الضغط
        if not compress_video_with_progress(temp_file, final_file):
            # استخدام الملف الأصلي إذا فشل الضغط
            shutil.copy2(temp_file, final_file)
        
        # 4. الرفع
        if await upload_video(final_file, series_name_arabic, season_num, episode_num):
            return True, "تم الرفع"
        else:
            return True, "تم التنزيل فقط"
        
    except Exception as e:
        return False, str(e)
    finally:
        # تنظيف الملف المؤقت
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

# ===== MAIN =====

async def main():
    """الدالة الرئيسية"""
    print("="*50)
    print("رفع المسلسلات إلى Telegram")
    print("="*50)
    
    # التحقق من التبعيات
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except:
        print("[!] ffmpeg غير مثبت")
        return
    
    try:
        import yt_dlp
    except:
        print("[*] تثبيت yt-dlp...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp', '-q'], check=True)
    
    # الاتصال بـ Telegram
    if not await setup_telegram():
        return
    
    # إدخال المعلومات
    print("\nإدخال معلومات المسلسل:")
    series_name = input("اسم المسلسل بالإنجليزية: ").strip() or "the-protector"
    series_name_arabic = input("اسم المسلسل بالعربية: ").strip() or "المحافظ"
    
    try:
        season_num = int(input("رقم الموسم: ").strip() or "1")
        start_ep = int(input("الحلقة الأولى: ").strip() or "1")
        end_ep = int(input("الحلقة الأخيرة: ").strip() or "1")
    except:
        print("[!] أرقام غير صالحة")
        return
    
    # إنشاء مجلد
    download_dir = f"{series_name_arabic}_S{season_num}"
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"\nبدء العمل:")
    print(f"المسلسل: {series_name_arabic}")
    print(f"الموسم: {season_num}")
    print(f"الحلقات: {start_ep} إلى {end_ep}")
    
    # معالجة الحلقات
    successful = 0
    failed = []
    
    for episode in range(start_ep, end_ep + 1):
        current = episode - start_ep + 1
        total = end_ep - start_ep + 1
        
        print(f"\n[{current}/{total}] الحلقة {episode:02d}")
        
        success, message = await process_episode(
            episode, series_name, series_name_arabic, season_num, download_dir
        )
        
        if success:
            successful += 1
            print(f"[✓] {message}")
        else:
            failed.append(episode)
            print(f"[!] {message}")
        
        # انتظار بين الحلقات
        if episode < end_ep:
            await asyncio.sleep(2)
    
    # النتائج
    print(f"\n[=] انتهى العمل")
    print(f"[+] الناجحة: {successful}/{end_ep-start_ep+1}")
    
    if failed:
        print(f"[!] الفاشلة: {failed}")
    
    # إغلاق التطبيق
    if app:
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] توقف")
    except Exception as e:
        print(f"\n[!] خطأ: {e}")
