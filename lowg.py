#!/usr/bin/env python3
"""
Video Downloader - Fixed Telegram API Issue
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
import tempfile
from pathlib import Path
from urllib.parse import urljoin

# ===== إضافة Pyrogram بعد التثبيت =====
try:
    from pyrogram import Client
    from pyrogram.errors import FloodWait, AuthKeyUnregistered, SessionPasswordNeeded
    PYROGRAM_INSTALLED = True
except ImportError:
    print("[!] pyrogram غير مثبت، جاري التثبيت...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyrogram", "tgcrypto"])
    from pyrogram import Client
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

# Telegram Configuration - استخدم بياناتك هنا مباشرة
TELEGRAM_API_ID = 30637918
TELEGRAM_API_HASH = "4779bdfbeddb85accd6fdbe199625ac5"
TELEGRAM_PHONE = "+201121087915"
TELEGRAM_CHANNEL = "@shoofFilm"

# جلسة Pyrogram
app = None

# ===== TELEGRAM SETUP FIXED =====

async def setup_telegram_fixed():
    """إعداد Telegram مع البيانات المباشرة"""
    global app
    
    print("\n" + "="*50)
    print("🔧 إعداد Telegram API")
    print("="*50)
    
    try:
        # استخدام البيانات التي قدمتها مباشرة
        api_id = TELEGRAM_API_ID
        api_hash = TELEGRAM_API_HASH
        phone_number = TELEGRAM_PHONE
        
        print(f"[*] API_ID: {api_id}")
        print(f"[*] API_HASH: {api_hash[:10]}...")
        print(f"[*] Phone: {phone_number}")
        
        # إنشاء كائن Client
        app = Client(
            "my_account",
            api_id=api_id,
            api_hash=api_hash,
            phone_number=phone_number,
            app_version="1.0.0",
            device_model="Video Downloader",
            system_version="Linux 6.5"
        )
        
        print("[*] جاري الاتصال بـ Telegram...")
        
        await app.start()
        
        # التحقق من الاتصال
        me = await app.get_me()
        print(f"[✓] تم الاتصال بنجاح!")
        print(f"    👤 الاسم: {me.first_name}")
        print(f"    📞 رقم الهاتف: {me.phone_number}")
        print(f"    🆔 User ID: {me.id}")
        
        # التحقق من القناة
        try:
            chat = await app.get_chat(TELEGRAM_CHANNEL)
            print(f"[✓] القناة: {chat.title}")
        except Exception as e:
            print(f"[!] تحذير: {e}")
            print(f"[*] تأكد من انضمام البوت للقناة: {TELEGRAM_CHANNEL}")
        
        return True
        
    except SessionPasswordNeeded:
        print("\n[!] حسابك محمي بكلمة مرور (2FA)")
        password = input("🔑 أدخل كلمة المرور: ").strip()
        try:
            await app.check_password(password)
            print("[✓] تم التحقق من كلمة المرور")
            return True
        except Exception as e:
            print(f"[!] كلمة المرور غير صحيحة: {e}")
            return False
            
    except AuthKeyUnregistered:
        print("[!] الجلسة غير صالحة، جاري إنشاء جلسة جديدة...")
        # حذف الجلسة القديمة
        session_files = ["my_account.session", "my_account.session-journal"]
        for file in session_files:
            if os.path.exists(file):
                os.remove(file)
        
        # إعادة المحاولة
        return await setup_telegram_fixed()
        
    except Exception as e:
        print(f"[!] خطأ في الاتصال بـ Telegram: {e}")
        print("[*] تأكد من:")
        print("    1. صحة API_ID و API_HASH")
        print("    2. اتصال الإنترنت")
        print("    3. أن الرقم مسجل في Telegram")
        return False

# ===== VIDEO PROCESSING FUNCTIONS =====

def download_video_simple(url, output_path):
    """تنزيل فيديو بسيط"""
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'best[height<=480]/best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'user_agent': USER_AGENT,
            'referer': 'https://v.vidsp.net/',
            'http_headers': HEADERS,
            'concurrent_fragment_downloads': 2,
        }
        
        print(f"[*] جاري التنزيل...")
        start = time.time()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        
        elapsed = time.time() - start
        
        if os.path.exists(output_path):
            size = os.path.getsize(output_path) / (1024*1024)
            print(f"[✓] تم التنزيل خلال {elapsed:.1f}ث ({size:.1f}MB)")
            return True
        else:
            # البحث عن ملف مختلف الاسم
            base = os.path.splitext(output_path)[0]
            for ext in ['.mp4', '.mkv', '.webm']:
                if os.path.exists(base + ext):
                    shutil.move(base + ext, output_path)
                    size = os.path.getsize(output_path) / (1024*1024)
                    print(f"[✓] تم التنزيل خلال {elapsed:.1f}ث ({size:.1f}MB)")
                    return True
        
        return False
        
    except Exception as e:
        print(f"[!] خطأ في التنزيل: {e}")
        return False

def compress_for_telegram(input_path, output_path, target_mb=100):
    """ضبط الفيديو لـ Telegram"""
    try:
        print(f"[*] جاري تحضير الفيديو لـ Telegram...")
        
        # الحصول على معلومات الفيديو
        cmd_info = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            input_path
        ]
        
        result = subprocess.run(cmd_info, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("[!] فشل قراءة معلومات الفيديو")
            return False
        
        info = json.loads(result.stdout)
        
        # استخراج معلومات الفيديو
        video_stream = None
        for stream in info.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break
        
        if not video_stream:
            print("[!] لا يوجد فيديو في الملف")
            return False
        
        width = int(video_stream.get('width', 640))
        height = int(video_stream.get('height', 360))
        duration = float(info['format'].get('duration', 1800))
        
        print(f"[*] الأبعاد: {width}x{height}")
        print(f"[*] المدة: {duration//60:.0f}:{duration%60:02.0f}")
        
        # حساب معدل البت المستهدف
        target_bitrate = int((target_mb * 8000) / (duration / 60))
        target_bitrate = max(500, min(target_bitrate, 1500))
        
        # إعدادات FFmpeg لـ Telegram
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', 'scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '24',
            '-maxrate', f'{target_bitrate}k',
            '-bufsize', f'{target_bitrate * 2}k',
            '-profile:v', 'high',
            '-level', '4.0',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ac', '2',
            '-ar', '48000',
            '-threads', '2',
            '-y',
            output_path
        ]
        
        start = time.time()
        
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if process.returncode == 0:
            elapsed = time.time() - start
            size = os.path.getsize(output_path) / (1024*1024)
            print(f"[✓] تم التحضير خلال {elapsed:.1f}ث ({size:.1f}MB)")
            return True
        else:
            print(f"[!] فشل التحضير: {process.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"[!] خطأ في التحضير: {e}")
        return False

async def upload_to_telegram_fixed(file_path, caption):
    """رفع الفيديو إلى Telegram"""
    try:
        if not app or not os.path.exists(file_path):
            return False
        
        print(f"[*] جاري رفع: {os.path.basename(file_path)}")
        
        # إرسال الفيديو
        await app.send_video(
            chat_id=TELEGRAM_CHANNEL,
            video=file_path,
            caption=caption,
            supports_streaming=True,
            parse_mode='HTML',
            disable_notification=False,
            progress=lambda current, total: print(f'\r[*] رفع: {current*100/total:.1f}%', end='')
        )
        
        print(f"\n[✓] تم الرفع بنجاح!")
        return True
        
    except FloodWait as e:
        print(f"\n[!] انتظر {e.value} ثانية...")
        await asyncio.sleep(e.value)
        return await upload_to_telegram_fixed(file_path, caption)
        
    except Exception as e:
        print(f"\n[!] خطأ في الرفع: {e}")
        return False

# ===== MAIN PROCESSING =====

async def process_single_episode(episode_num, series_name, series_name_arabic, season_num, download_dir):
    """معالجة حلقة واحدة"""
    print(f"\n{'='*50}")
    print(f"🎬 الحلقة {episode_num:02d}")
    print('='*50)
    
    try:
        # 1. بناء الرابط
        if season_num > 1:
            base_url = f"https://x.3seq.com/video/modablaj-{series_name}-episode-s{season_num:02d}e{episode_num:02d}"
        else:
            base_url = f"https://x.3seq.com/video/modablaj-{series_name}-episode-{episode_num:02d}"
        
        # 2. جلب الصفحة
        print(f"[*] جلب: {base_url}")
        response = requests.get(base_url, headers=HEADERS, timeout=15)
        
        # 3. استخراج رابط watch
        watch_match = re.search(r'href=["\']([^"\']+episode[^"\']+\?do=watch)["\']', response.text)
        if watch_match:
            watch_url = watch_match.group(1)
            if watch_url.startswith('//'):
                watch_url = 'https:' + watch_url
            elif watch_url.startswith('/'):
                watch_url = 'https://x.3seq.com' + watch_url
        else:
            watch_url = f"{base_url}-yvra/?do=watch"
        
        # 4. استخراج embed
        print(f"[*] استخراج رابط الفيديو...")
        response = requests.get(watch_url, headers=HEADERS, timeout=15)
        iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', response.text)
        
        if not iframe_match:
            return False, "لا يوجد رابط فيديو"
        
        embed_url = iframe_match.group(1)
        if embed_url.startswith('//'):
            embed_url = 'https:' + embed_url
        elif embed_url.startswith('/'):
            embed_url = 'https://v.vidsp.net' + embed_url
        
        print(f"[✓] تم استخراج الرابط")
        
        # 5. تنزيل
        temp_file = os.path.join(download_dir, f"temp_{episode_num:02d}.mp4")
        final_file = os.path.join(download_dir, f"{series_name_arabic}_S{season_num:02d}_E{episode_num:02d}.mp4")
        
        # تنظيف
        for f in [temp_file, final_file]:
            if os.path.exists(f):
                os.remove(f)
        
        if not download_video_simple(embed_url, temp_file):
            return False, "فشل التنزيل"
        
        # 6. تحضير لـ Telegram
        if not compress_for_telegram(temp_file, final_file, 100):
            # إذا فشل، استخدم الملف الأصلي
            shutil.copy2(temp_file, final_file)
        
        # تنظيف الملف المؤقت
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # 7. رفع
        caption = f"<b>{series_name_arabic}</b>\nالموسم {season_num} | الحلقة {episode_num}"
        
        if await upload_to_telegram_fixed(final_file, caption):
            return True, "تم الرفع"
        else:
            return True, "تم التنزيل فقط"
        
    except Exception as e:
        print(f"[!] خطأ: {e}")
        return False, str(e)

async def main():
    """الدالة الرئيسية"""
    print("="*60)
    print("🎥 Video Downloader for Telegram - FIXED")
    print("="*60)
    
    # التحقق من التبعيات
    print("[*] التحقق من التبعيات...")
    
    # FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("  ✓ ffmpeg")
    except:
        print("  ✗ ffmpeg غير مثبت")
        return
    
    # yt-dlp
    try:
        import yt_dlp
        print("  ✓ yt-dlp")
    except:
        print("  ✗ تثبيت yt-dlp...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp', '-q'], check=True)
    
    # إعداد Telegram
    if not await setup_telegram_fixed():
        print("[!] فشل إعداد Telegram")
        return
    
    # إدخال معلومات المسلسل
    print("\n" + "="*50)
    print("📝 إدخال معلومات المسلسل")
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
    
    # إنشاء مجلد
    download_dir = f"{series_name_arabic}_الموسم_{season_num}"
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print("🎬 بدء العمل")
    print(f"   المسلسل: {series_name_arabic}")
    print(f"   الموسم: {season_num}")
    print(f"   الحلقات: {start_ep} إلى {end_ep}")
    print('='*60)
    
    # معالجة الحلقات بالترتيب
    successful = 0
    failed = []
    
    for episode in range(start_ep, end_ep + 1):
        print(f"\n📋 الحلقة {episode:02d} ({successful+1}/{end_ep-start_ep+1})")
        print("-" * 40)
        
        start_time = time.time()
        success, message = await process_single_episode(
            episode, series_name, series_name_arabic, season_num, download_dir
        )
        
        elapsed = time.time() - start_time
        
        if success:
            successful += 1
            print(f"[✅] {episode:02d}: {message} ({elapsed/60:.1f} دقيقة)")
        else:
            failed.append(episode)
            print(f"[❌] {episode:02d}: {message}")
        
        # انتظار بين الحلقات
        if episode < end_ep:
            print(f"[⏳] انتظار 5 ثواني...")
            await asyncio.sleep(5)
    
    # النتائج
    print(f"\n{'='*60}")
    print("📊 النتائج")
    print('='*60)
    print(f"✅ الناجحة: {successful}/{end_ep-start_ep+1}")
    print(f"📁 الملفات في: {download_dir}")
    
    if failed:
        print(f"❌ الفاشلة: {failed}")
    
    print(f"\n{'='*60}")
    print("🎉 انتهى العمل!")
    
    # إغلاق Telegram
    if app:
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[!] توقف بواسطة المستخدم")
    except Exception as e:
        print(f"\n[!] خطأ غير متوقع: {e}")
