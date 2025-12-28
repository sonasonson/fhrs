#!/usr/bin/env python3
"""
Telegram Video Downloader & Uploader - Simplified Version
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
from datetime import datetime

# ===== إضافة Pyrogram بعد التثبيت =====
try:
    from pyrogram import Client, enums
    from pyrogram.errors import FloodWait, AuthKeyUnregistered, SessionPasswordNeeded
    PYROGRAM_INSTALLED = True
except ImportError:
    print("[!] pyrogram غير مثبت، جاري التثبيت...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyrogram", "tgcrypto"])
    from pyrogram import Client, enums
    from pyrogram.errors import FloodWait, AuthKeyUnregistered, SessionPasswordNeeded
    PYROGRAM_INSTALLED = True

# ===== CONFIG =====
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
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
    
    print("\n" + "="*50)
    print("🔧 إعداد Telegram API")
    print("="*50)
    
    try:
        print(f"[*] API_ID: {TELEGRAM_API_ID}")
        print(f"[*] Phone: {TELEGRAM_PHONE}")
        
        app = Client(
            "my_account",
            api_id=TELEGRAM_API_ID,
            api_hash=TELEGRAM_API_HASH,
            phone_number=TELEGRAM_PHONE,
            app_version="1.0.0",
            device_model="PC",
            system_version="Windows 10"
        )
        
        print("[*] جاري الاتصال بـ Telegram...")
        await app.start()
        
        me = await app.get_me()
        print(f"[✓] تم الاتصال بنجاح!")
        print(f"    👤 الاسم: {me.first_name}")
        
        # التحقق من القناة
        try:
            chat = await app.get_chat(TELEGRAM_CHANNEL)
            print(f"[✓] القناة: {chat.title}")
        except:
            print(f"[!] تحذير: قد لا أكون مشتركاً في القناة")
        
        return True
        
    except SessionPasswordNeeded:
        print("\n[!] حسابك محمي بكلمة مرور (2FA)")
        password = input("🔑 أدخل كلمة المرور: ").strip()
        try:
            await app.check_password(password)
            print("[✓] تم التحقق من كلمة المرور")
            return True
        except:
            print("[!] كلمة المرور غير صحيحة")
            return False
            
    except Exception as e:
        print(f"[!] خطأ في الاتصال: {e}")
        return False

# ===== VIDEO DOWNLOAD =====

def download_video(url, output_path):
    """تنزيل فيديو باستخدام yt-dlp"""
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'best[height<=720]/best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'user_agent': USER_AGENT,
            'referer': 'https://v.vidsp.net/',
            'http_headers': HEADERS,
        }
        
        print(f"[*] جاري تنزيل الفيديو...")
        start = time.time()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        elapsed = time.time() - start
        
        # التحقق من وجود الملف
        if os.path.exists(output_path):
            size = os.path.getsize(output_path) / (1024*1024)
            print(f"[✓] تم التنزيل خلال {elapsed:.1f}ث ({size:.1f}MB)")
            return True
        else:
            # البحث عن ملف آخر
            base = os.path.splitext(output_path)[0]
            for ext in ['.mp4', '.mkv', '.webm', '.flv', '.avi']:
                if os.path.exists(base + ext):
                    shutil.move(base + ext, output_path)
                    size = os.path.getsize(output_path) / (1024*1024)
                    print(f"[✓] تم التنزيل خلال {elapsed:.1f}ث ({size:.1f}MB)")
                    return True
        
        return False
        
    except Exception as e:
        print(f"[!] خطأ في التنزيل: {e}")
        return False

# ===== COMPRESSION WITH PROGRESS BAR =====

def compress_video_240p(input_file, output_file, crf=30):
    """ضغط الفيديو إلى 240p مع شريط تقدم"""
    if not os.path.exists(input_file):
        print(f"[!] الملف غير موجود: {input_file}")
        return False
    
    original_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
    
    print(f"[*] جاري ضغط الفيديو إلى 240p...")
    print(f"[*] الحجم الأصلي: {original_size:.1f}MB")
    print(f"[*] CRF: {crf} (كلما زاد الرقم زاد الضغط)")
    
    # الحصول على مدة الفيديو
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
            if duration > 0:
                print(f"[*] المدة: {int(duration//60)}:{int(duration%60):02d}")
    except:
        duration = 0
    
    # بناء أمر FFmpeg مع مراقبة التقدم
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-vf', 'scale=-2:240',
        '-c:v', 'libx264',
        '-crf', str(crf),
        '-preset', 'fast',
        '-c:a', 'aac',
        '-b:a', '64k',
        '-progress', 'pipe:1',  # إخراج التقدم
        '-y',
        output_file
    ]
    
    print(f"[*] جاري بدء الضغط...")
    print(f"[ ] 0%", end='', flush=True)
    
    start_time = time.time()
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # متغيرات لتتبع التقدم
    progress_data = {}
    
    # قراءة الإخراج سطراً سطراً
    for line in process.stdout:
        line = line.strip()
        
        # تحليل خطوط التقدم
        if '=' in line:
            key, value = line.split('=', 1)
            progress_data[key.strip()] = value.strip()
        
        # عرض التقدم بناءً على الوقت
        if 'out_time_ms' in progress_data:
            try:
                current_time_ms = int(progress_data['out_time_ms'])
                current_time = current_time_ms / 1000000.0  # تحويل إلى ثواني
                
                if duration > 0:
                    progress_percent = min(100, (current_time / duration) * 100)
                    
                    # عرض شريط تقدم
                    bar_length = 30
                    filled_length = int(bar_length * progress_percent // 100)
                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                    
                    elapsed = time.time() - start_time
                    if progress_percent > 0:
                        remaining = (elapsed / progress_percent) * (100 - progress_percent)
                        print(f"\r[+] {progress_percent:.1f}% |{bar}| الوقت المتبقي: {remaining:.0f}ث", end='', flush=True)
                    else:
                        print(f"\r[+] {progress_percent:.1f}% |{bar}|", end='', flush=True)
            except:
                pass
    
    # الانتظار حتى انتهاء العملية
    process.wait()
    
    print()  # سطر جديد بعد انتهاء الشريط
    
    if process.returncode == 0 and os.path.exists(output_file):
        new_size = os.path.getsize(output_file) / (1024 * 1024)
        total_time = time.time() - start_time
        reduction = ((original_size - new_size) / original_size) * 100
        
        print(f"[✓] تم الضغط بنجاح خلال {total_time:.1f}ث")
        print(f"    📊 الحجم الأصلي: {original_size:.1f}MB")
        print(f"    📊 الحجم الجديد: {new_size:.1f}MB")
        print(f"    💾 توفير: {reduction:.1f}%")
        return True
    else:
        print(f"[!] فشل الضغط")
        return False

# ===== UPLOAD TO TELEGRAM =====

async def upload_video_to_channel(file_path, caption):
    """رفع الفيديو إلى القناة مع صورة مصغرة"""
    try:
        if not app or not os.path.exists(file_path):
            return False
        
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024*1024)
        
        print(f"\n[*] جاري رفع: {filename}")
        print(f"[*] الحجم: {file_size:.1f}MB")
        
        # إضافة تأخير بسيط قبل الرفع
        await asyncio.sleep(1)
        
        start_time = time.time()
        last_update = 0
        
        def progress_callback(current, total):
            nonlocal last_update
            percentage = (current / total) * 100
            
            # تحديث كل 2% أو كل ثانية
            now = time.time()
            if now - last_update > 1 or percentage - last_update >= 2:
                elapsed = now - start_time
                if current > 0 and elapsed > 0:
                    speed = current / elapsed / 1024  # KB/s
                    remaining = ((total - current) / current) * elapsed if current > 0 else 0
                    
                    bar_length = 25
                    filled = int(bar_length * current // total)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    
                    print(f'\r[*] رفع: {percentage:.1f}% |{bar}| {current/1024/1024:.1f}MB/{total/1024/1024:.1f}MB ({speed:.0f}KB/s)', end='')
                    last_update = percentage
        
        # رفع الفيديو
        try:
            await app.send_video(
                chat_id=TELEGRAM_CHANNEL,
                video=file_path,
                caption=caption,
                supports_streaming=True,
                # parse_mode=enums.ParseMode.HTML,  # إزالة هذا السطر إذا كان يسبب مشكلة
                disable_notification=False,
                progress=progress_callback
            )
            
            elapsed = time.time() - start_time
            print(f"\n[✓] تم الرفع بنجاح خلال {elapsed:.1f}ثانية!")
            return True
            
        except FloodWait as e:
            print(f"\n[!] انتظر {e.value} ثانية (طلب من Telegram)...")
            await asyncio.sleep(e.value)
            return await upload_video_to_channel(file_path, caption)
            
        except Exception as e:
            print(f"\n[!] خطأ في الرفع: {e}")
            
            # محاولة بدون progress callback
            try:
                print("[*] جاري محاولة رفع بدون تتبع التقدم...")
                await app.send_video(
                    chat_id=TELEGRAM_CHANNEL,
                    video=file_path,
                    caption=caption,
                    supports_streaming=True,
                    disable_notification=False
                )
                print("[✓] تم الرفع بنجاح!")
                return True
            except Exception as e2:
                print(f"[!] فشل الرفع مرة أخرى: {e2}")
                return False
        
    except Exception as e:
        print(f"[!] خطأ غير متوقع في الرفع: {e}")
        return False

# ===== EXTRACT VIDEO URL =====

def extract_video_url(episode_num, series_name, season_num):
    """استخراج رابط الفيديو"""
    try:
        # بناء الرابط
        if season_num > 1:
            base_url = f"https://x.3seq.com/video/modablaj-{series_name}-episode-s{season_num:02d}e{episode_num:02d}"
        else:
            base_url = f"https://x.3seq.com/video/modablaj-{series_name}-episode-{episode_num:02d}"
        
        print(f"[*] الرابط: {base_url}")
        
        # جلب الصفحة
        response = requests.get(base_url, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            return None, f"فشل جلب الصفحة: {response.status_code}"
        
        # استخراج رابط watch
        watch_match = re.search(r'href=["\']([^"\']+episode[^"\']+\?do=watch)["\']', response.text)
        if watch_match:
            watch_url = watch_match.group(1)
            if watch_url.startswith('//'):
                watch_url = 'https:' + watch_url
            elif watch_url.startswith('/'):
                watch_url = 'https://x.3seq.com' + watch_url
        else:
            watch_url = f"{base_url}-yvra/?do=watch"
        
        # جلب صفحة watch
        response = requests.get(watch_url, headers=HEADERS, timeout=20)
        iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', response.text)
        
        if not iframe_match:
            return None, "لم يتم العثور على رابط الفيديو"
        
        video_url = iframe_match.group(1)
        if video_url.startswith('//'):
            video_url = 'https:' + video_url
        elif video_url.startswith('/'):
            video_url = 'https://v.vidsp.net' + video_url
        
        return video_url, "تم استخراج الرابط"
        
    except requests.exceptions.Timeout:
        return None, "انتهت مهلة الاتصال"
    except Exception as e:
        return None, f"خطأ: {str(e)}"

# ===== PROCESS EPISODE =====

async def process_episode(episode_num, series_name, series_name_arabic, season_num, download_dir):
    """معالجة حلقة واحدة"""
    print(f"\n{'='*60}")
    print(f"🎬 الحلقة {episode_num:02d}")
    print('='*60)
    
    temp_file = os.path.join(download_dir, f"temp_{episode_num:02d}.mp4")
    final_file = os.path.join(download_dir, f"{series_name_arabic}_S{season_num:02d}_E{episode_num:02d}.mp4")
    
    # تنظيف الملفات القديمة
    for f in [temp_file, final_file]:
        if os.path.exists(f):
            os.remove(f)
    
    try:
        # 1. استخراج رابط الفيديو
        print("[*] جاري استخراج رابط الفيديو...")
        video_url, message = extract_video_url(episode_num, series_name, season_num)
        
        if not video_url:
            return False, message
        
        print(f"[✓] {message}")
        
        # 2. تنزيل الفيديو
        print("[*] بدء تنزيل الفيديو...")
        if not download_video(video_url, temp_file):
            return False, "فشل تنزيل الفيديو"
        
        # 3. ضغط الفيديو
        print("\n[*] بدء ضغط الفيديو...")
        if not compress_video_240p(temp_file, final_file, crf=28):
            # إذا فشل الضغط، استخدم الملف الأصلي
            print("[!] فشل الضغط، استخدام الملف الأصلي")
            shutil.copy2(temp_file, final_file)
        
        # 4. رفع الفيديو
        caption = f"📺 {series_name_arabic}\nالموسم {season_num} | الحلقة {episode_num}\n\n🚀 تم الرفع تلقائياً"
        
        if await upload_video_to_channel(final_file, caption):
            return True, "تم الرفع بنجاح"
        else:
            return True, "تم التنزيل فقط (فشل الرفع)"
        
    except Exception as e:
        print(f"[!] خطأ غير متوقع: {e}")
        return False, str(e)
    finally:
        # تنظيف الملف المؤقت
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

# ===== MAIN FUNCTION =====

async def main():
    """الدالة الرئيسية"""
    print("="*70)
    print("📥 Telegram Video Downloader & Uploader")
    print("="*70)
    
    # التحقق من التبعيات
    print("\n[*] التحقق من التبعيات...")
    
    # FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("  ✓ ffmpeg")
    except:
        print("  ✗ ffmpeg غير مثبت")
        print("  [*] جاري التثبيت...")
        try:
            subprocess.run(['apt-get', 'install', '-y', 'ffmpeg'], capture_output=True)
            print("  ✓ تم التثبيت")
        except:
            print("  ✗ فشل التثبيت، يرجى تثبيته يدوياً")
            return
    
    # yt-dlp
    try:
        import yt_dlp
        print("  ✓ yt-dlp")
    except:
        print("  ✗ تثبيت yt-dlp...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp', '-q'], check=True)
        print("  ✓ تم التثبيت")
    
    # إعداد Telegram
    if not await setup_telegram():
        print("[!] فشل إعداد Telegram")
        return
    
    # إدخال المعلومات
    print("\n" + "="*50)
    print("📝 معلومات المسلسل")
    print("="*50)
    
    series_name = input("\nاسم المسلسل بالإنجليزية: ").strip() or "the-protector"
    series_name_arabic = input("اسم المسلسل بالعربية: ").strip() or "المحافظ"
    
    try:
        season_num = int(input("رقم الموسم: ").strip() or "2")
        start_ep = int(input("الحلقة الأولى: ").strip() or "1")
        end_ep = int(input("الحلقة الأخيرة: ").strip() or "8")
    except:
        print("[!] أرقام غير صالحة")
        return
    
    if start_ep > end_ep:
        print("[!] الحلقة الأولى يجب أن تكون أصغر من الأخيرة")
        return
    
    # إنشاء مجلد
    download_dir = f"{series_name_arabic}_الموسم_{season_num}"
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("🚀 بدء العمل")
    print('='*70)
    print(f"📺 المسلسل: {series_name_arabic}")
    print(f"🎬 الموسم: {season_num}")
    print(f"🔢 الحلقات: {start_ep} إلى {end_ep}")
    print(f"📁 المجلد: {download_dir}")
    
    # معالجة الحلقات
    successful = 0
    failed = []
    total = end_ep - start_ep + 1
    
    for episode_num in range(start_ep, end_ep + 1):
        current = episode_num - start_ep + 1
        
        print(f"\n📋 الحلقة {episode_num:02d} ({current}/{total})")
        print("-" * 40)
        
        start_time = time.time()
        success, message = await process_episode(
            episode_num, series_name, series_name_arabic, season_num, download_dir
        )
        
        elapsed = time.time() - start_time
        
        if success:
            successful += 1
            print(f"[✅] {episode_num:02d}: {message} ({elapsed/60:.1f} دقيقة)")
        else:
            failed.append(episode_num)
            print(f"[❌] {episode_num:02d}: {message}")
        
        # انتظار بين الحلقات
        if episode_num < end_ep:
            wait = 3
            print(f"[⏳] انتظار {wait} ثواني...")
            await asyncio.sleep(wait)
    
    # النتائج
    print(f"\n{'='*70}")
    print("📊 النتائج النهائية")
    print('='*70)
    print(f"✅ الناجحة: {successful}/{total}")
    print(f"📁 الملفات في: {download_dir}")
    
    if failed:
        print(f"❌ الفاشلة: {failed}")
    
    print(f"\n{'='*70}")
    print("🎉 انتهى العمل!")
    
    # إغلاق التطبيق
    if app:
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[!] توقف بواسطة المستخدم")
    except Exception as e:
        print(f"\n[!] خطأ: {e}")
