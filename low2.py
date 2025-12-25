#!/usr/bin/env python3
"""
Ultra Fast Video Downloader for 3seq.com - Lightning Speed
"""

import os
import sys
import re
import time
import json
import requests
import subprocess
import shutil
import threading
import concurrent.futures
from queue import Queue
from urllib.parse import urljoin, parse_qs, urlparse, unquote
from bs4 import BeautifulSoup

# ===== CONFIGURATION =====
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
MAX_WORKERS = 5  # زيادة عدد التنزيلات المتوازية
DOWNLOAD_TIMEOUT = 300
COMPRESS_TIMEOUT = 180

# متغيرات الأداء
USE_FAST_COMPRESS = True
PARALLEL_DOWNLOADS = True
USE_SSD_OPTIMIZATIONS = True

def clean_directory(directory):
    """تنظيف الملفات غير المرغوب فيها بسرعة"""
    if not os.path.exists(directory):
        return
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        try:
            # حذف الملفات المؤقتة فقط (لا تعطل العملية)
            if any(filename.endswith(ext) for ext in ['.part', '.temp', '.tmp', '.frag', '.m3u8']):
                os.remove(file_path)
        except:
            pass

def install_requirements():
    """تثبيت سريع للحزم المطلوبة"""
    print("[*] فحص سريع للمتطلبات...")
    
    try:
        import requests
        print("  ✓ requests")
    except:
        print("  ✗ تثبيت requests...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests', '--quiet'], check=True)
    
    try:
        import bs4
        print("  ✓ beautifulsoup4")
    except:
        print("  ✗ تثبيت beautifulsoup4...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'beautifulsoup4', '--quiet'], check=True)
    
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("  ✓ yt-dlp")
    except:
        print("  ✗ تثبيت yt-dlp...")
        subprocess.run(['pip', 'install', 'yt-dlp', '--quiet'], check=True)
    
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("  ✓ ffmpeg")
    except:
        print("  ✗ تثبيت ffmpeg...")
        subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg', '--quiet'], check=True)

def get_final_episode_url_fast(base_url, series_pattern, episode_num):
    """الحصول السريع على رابط الحلقة"""
    episode_str = f"{episode_num:02d}"
    initial_url = f"{base_url}/{series_pattern}{episode_str}"
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        response = session.get(initial_url, timeout=5, allow_redirects=True)
        return response.url
    except:
        return initial_url

def extract_m3u8_fast(episode_url):
    """استخراج سريع لرابط m3u8"""
    try:
        if '?do=watch' not in episode_url:
            if not episode_url.endswith('/'):
                episode_url += '/'
            watch_url = episode_url + '?do=watch'
        else:
            watch_url = episode_url
        
        response = requests.get(watch_url, headers=HEADERS, timeout=8)
        
        # البحث السريع عن iframe
        iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', response.text)
        if iframe_match:
            iframe_url = iframe_match.group(1)
            if iframe_url.startswith('//'):
                iframe_url = 'https:' + iframe_url
            
            # استخراج m3u8 من iframe
            iframe_response = requests.get(iframe_url, headers=HEADERS, timeout=8)
            m3u8_match = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', iframe_response.text)
            if m3u8_match:
                return m3u8_match.group(0)
        
        # البحث المباشر عن m3u8
        m3u8_match = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', response.text)
        if m3u8_match:
            return m3u8_match.group(0)
        
        return None
    except:
        return None

def download_hls_ultrafast(m3u8_url, output_file):
    """تنزيل HLS بأقصى سرعة"""
    try:
        print(f"[*] تنزيل سريع باستخدام ffmpeg...")
        
        # استخدام إعدادات ffmpeg للسرعة القصوى
        cmd = [
            'ffmpeg',
            '-i', m3u8_url,
            '-c', 'copy',  # نسخ بدون إعادة ترميز (أسرع خيار)
            '-bsf:a', 'aac_adtstoasc',
            '-y',  # الكتابة فوق الملف
            '-threads', '0',  # استخدام كل الأنوية
            '-loglevel', 'error',  # تقليل السجلات
            output_file
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        
        if result.returncode == 0 and os.path.exists(output_file):
            elapsed = time.time() - start_time
            file_size = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] {elapsed:.1f} ثانية - {file_size:.1f} MB")
            
            # ضغط سريع إذا لزم الأمر
            if file_size > 30:  # إذا كان أكبر من 30MB
                return fast_compress_to_240p(output_file)
            return True
        return False
        
    except Exception as e:
        print(f"[!] خطأ في التنزيل السريع: {e}")
        return False

def fast_compress_to_240p(input_file):
    """ضغط سريع جداً إلى 240p"""
    try:
        temp_file = input_file.replace('.mp4', '_fast.mp4')
        
        # إعدادات ffmpeg للسرعة القصوى
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-vf', 'scale=-2:240',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',  # أسرع إعداد
            '-tune', 'fastdecode',   # تحسين للسرعة
            '-crf', '32',            # ضغط عالي للسرعة
            '-c:a', 'aac',
            '-b:a', '48k',           # صوت منخفض الجودة
            '-ac', '1',              # صوت أحادي
            '-y',
            '-threads', '0',
            '-loglevel', 'error',
            temp_file
        ]
        
        print("[*] ضغط سريع...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=COMPRESS_TIMEOUT)
        
        if result.returncode == 0 and os.path.exists(temp_file):
            os.remove(input_file)
            shutil.move(temp_file, input_file)
            
            final_size = os.path.getsize(input_file) / (1024*1024)
            print(f"[✓] تم الضغط - {final_size:.1f} MB")
            return True
        return False
        
    except Exception as e:
        print(f"[!] خطأ في الضغط السريع: {e}")
        return False

def download_direct_ultrafast(video_url, output_file):
    """تنزيل مباشر بأقصى سرعة"""
    try:
        # استخدام yt-dlp مع إعدادات السرعة القصوى
        cmd = [
            'yt-dlp',
            '-f', 'worst[height<=360]',  # أسوأ جودة حتى 360p (أسرع تنزيل)
            '--concurrent-fragments', '16',  # زيادة الأجزاء المتوازية
            '--limit-rate', '0',  # لا حدود للسرعة
            '--retries', '3',
            '--fragment-retries', '3',
            '--no-check-certificates',
            '--no-part',
            '--quiet',
            '--progress',
            '--merge-output-format', 'mp4',
            '--external-downloader', 'aria2c',  # إذا كان مثبتاً
            '--external-downloader-args', '-x 16 -s 16 -k 1M',
            '-o', output_file,
            video_url
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        
        if result.returncode == 0 and os.path.exists(output_file):
            elapsed = time.time() - start_time
            file_size = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] {elapsed:.1f} ثانية - {file_size:.1f} MB")
            
            # ضغط سريع إذا لزم الأمر
            if file_size > 30:
                return fast_compress_to_240p(output_file)
            return True
        return False
        
    except Exception as e:
        print(f"[!] خطأ في التنزيل المباشر: {e}")
        return False

def parallel_download_worker(task_queue, results_queue):
    """عامل للتنزيل المتوازي"""
    while True:
        try:
            task = task_queue.get_nowait()
        except:
            break
        
        episode_num, base_url, series_pattern, download_dir = task
        episode_str = f"{episode_num:02d}"
        
        try:
            output_file = os.path.join(download_dir, f"الحلقة_{episode_str}.mp4")
            
            # تخطي إذا كان الملف موجوداً
            if os.path.exists(output_file):
                size = os.path.getsize(output_file) / (1024*1024)
                results_queue.put((episode_num, True, f"موجود ({size:.1f}MB)"))
                task_queue.task_done()
                continue
            
            # استخراج سريع للرابط
            episode_url = get_final_episode_url_fast(base_url, series_pattern, episode_num)
            m3u8_url = extract_m3u8_fast(episode_url)
            
            if not m3u8_url:
                results_queue.put((episode_num, False, "فشل استخراج الرابط"))
                task_queue.task_done()
                continue
            
            print(f"[*] الحلقة {episode_str}: جاري التنزيل...")
            
            # محاولة التنزيل السريع
            success = False
            if m3u8_url and '.m3u8' in m3u8_url:
                success = download_hls_ultrafast(m3u8_url, output_file)
            else:
                success = download_direct_ultrafast(m3u8_url, output_file)
            
            if success:
                results_queue.put((episode_num, True, "نجح"))
            else:
                results_queue.put((episode_num, False, "فشل التنزيل"))
            
        except Exception as e:
            results_queue.put((episode_num, False, f"خطأ: {str(e)[:50]}"))
        
        task_queue.task_done()

def process_episodes_parallel_fast(base_url, series_pattern, start_ep, end_ep, download_dir, num_workers):
    """معالجة الحلقات بشكل متوازي بأقصى سرعة"""
    print(f"\n[*] بدء التنزيل المتوازي ({num_workers} تنزيلات متزامنة)")
    
    # إنشاء قائمة المهام
    task_queue = Queue()
    results_queue = Queue()
    
    for ep in range(start_ep, end_ep + 1):
        task_queue.put((ep, base_url, series_pattern, download_dir))
    
    # إنشاء العمال
    workers = []
    for _ in range(min(num_workers, task_queue.qsize())):
        worker = threading.Thread(target=parallel_download_worker, args=(task_queue, results_queue))
        worker.start()
        workers.append(worker)
    
    # انتظار انتهاء جميع المهام
    task_queue.join()
    
    # جمع النتائج
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # انتظار انتهاء جميع العمال
    for worker in workers:
        worker.join()
    
    return results

def main_lightning_speed():
    """الوظيفة الرئيسية للسرعة القصوى"""
    print("="*60)
    print("تنزيل فيديو - سرعة البرق")
    print("="*60)
    
    # تثبيت سريع
    install_requirements()
    
    # إدخال سريع
    print("\n[*] أدخل المعلومات بسرعة:")
    
    base_url = "https://x.3seq.com/video"
    default_pattern = "modablaj-terzi-episode-"
    
    series_pattern = input(f"نمط المسلسل [{default_pattern}]: ").strip()
    if not series_pattern:
        series_pattern = default_pattern
    
    if not series_pattern.endswith('-'):
        series_pattern += '-'
    
    # استخراج اسم المسلسل
    if '-episode-' in series_pattern:
        series_name = series_pattern.split('-episode-')[0]
    else:
        series_name = series_pattern.rstrip('-')
    
    # إنشاء مجلد التنزيل
    download_dir = series_name
    if os.path.exists(download_dir):
        clean_directory(download_dir)
        print(f"[*] استخدام المجلد الموجود: {download_dir}")
    else:
        os.makedirs(download_dir, exist_ok=True)
        print(f"[*] تم إنشاء مجلد: {download_dir}")
    
    # إدخال الحلقات
    try:
        start_ep = int(input("الحلقة الأولى [1]: ").strip() or "1")
        end_ep = int(input("الحلقة الأخيرة [10]: ").strip() or "10")
        
        if start_ep > end_ep:
            start_ep, end_ep = end_ep, start_ep
    except:
        print("[!] أرقام غير صالحة")
        return
    
    # عدد التنزيلات المتوازية (يمكن زيادته)
    max_workers = min(MAX_WORKERS, (end_ep - start_ep + 1))
    workers_input = input(f"التنزيلات المتوازية [1-{max_workers}، الافتراضي: {max_workers}]: ").strip()
    
    try:
        if workers_input:
            num_workers = min(int(workers_input), max_workers)
        else:
            num_workers = max_workers
    except:
        num_workers = max_workers
    
    print(f"\n{'='*60}")
    print("[*] إعدادات السرعة القصوى:")
    print('='*60)
    print(f"    المسلسل: {series_name}")
    print(f"    الحلقات: {start_ep:02d} إلى {end_ep:02d}")
    print(f"    التنزيلات المتوازية: {num_workers}")
    print(f"    الضغط السريع: ✓")
    print(f"    التحسينات: ✓")
    print('='*60)
    
    # بدء التنزيل المتوازي
    start_time = time.time()
    results = process_episodes_parallel_fast(base_url, series_pattern, start_ep, end_ep, download_dir, num_workers)
    
    # تحليل النتائج
    successful = 0
    failed = []
    
    for ep_num, success, message in results:
        if success:
            successful += 1
            print(f"[✓] الحلقة {ep_num:02d}: {message}")
        else:
            failed.append(ep_num)
            print(f"[✗] الحلقة {ep_num:02d}: {message}")
    
    # النتائج النهائية
    total_time = time.time() - start_time
    
    print(f"\n{'='*60}")
    print("[*] النتائج النهائية:")
    print('='*60)
    print(f"    الوقت الإجمالي: {total_time:.1f} ثانية")
    print(f"    الناجحة: {successful}/{len(results)}")
    
    if successful > 0:
        avg_time = total_time / successful
        print(f"    متوسط الوقت للحلقة: {avg_time:.1f} ثانية")
    
    if failed:
        print(f"    الفاشلة: {[f'{ep:02d}' for ep in failed]}")
    
    # عرض الملفات النهائية
    print(f"\n[*] الملفات النهائية:")
    total_size = 0
    
    try:
        mp4_files = [f for f in sorted(os.listdir(download_dir)) if f.endswith('.mp4')]
        
        for file in mp4_files:
            file_path = os.path.join(download_dir, file)
            size = os.path.getsize(file_path) / (1024*1024)
            total_size += size
            print(f"    {file}: {size:.1f} MB")
        
        if mp4_files:
            avg_size = total_size / len(mp4_files)
            print(f"\n[*] الإحصائيات:")
            print(f"    الحجم الإجمالي: {total_size:.1f} MB")
            print(f"    متوسط الحجم: {avg_size:.1f} MB")
            
    except Exception as e:
        print(f"[!] خطأ في قراءة الملفات: {e}")
    
    # تنظيف نهائي
    clean_directory(download_dir)
    
    print('='*60)
    print("[*] اكتمل العمل بسرعة البرق!")

def test_single_fast():
    """اختبار سريع لحلقة واحدة"""
    print("\n[*] اختبار سريع لحلقة واحدة")
    
    url = input("أدخل رابط الحلقة: ").strip()
    
    if not url:
        print("[!] لم يتم إدخال رابط")
        return
    
    # استخراج اسم
    match = re.search(r'/([^/]+)-episode-', url)
    if match:
        name = match.group(1)
    else:
        name = "test"
    
    output_file = f"{name}_fast_{int(time.time())}.mp4"
    
    print(f"\n[*] بدء الاختبار السريع...")
    
    # استخراج m3u8 بسرعة
    m3u8_url = extract_m3u8_fast(url)
    
    if not m3u8_url:
        print("[!] فشل استخراج رابط الفيديو")
        return
    
    print(f"[*] رابط الفيديو: {m3u8_url[:80]}...")
    
    # تنزيل سريع
    start_time = time.time()
    
    if m3u8_url and '.m3u8' in m3u8_url:
        success = download_hls_ultrafast(m3u8_url, output_file)
    else:
        success = download_direct_ultrafast(m3u8_url, output_file)
    
    if success:
        elapsed = time.time() - start_time
        if os.path.exists(output_file):
            size = os.path.getsize(output_file) / (1024*1024)
            print(f"\n[✓] نجح الاختبار!")
            print(f"    الوقت: {elapsed:.1f} ثانية")
            print(f"    الحجم: {size:.1f} MB")
            print(f"    الملف: {output_file}")
    else:
        print("\n[!] فشل الاختبار")

def batch_test():
    """اختبار دفعة من الحلقات"""
    print("\n[*] اختبار دفعة سريع")
    
    base_url = input("الرابط الأساسي [https://x.3seq.com/video]: ").strip() or "https://x.3seq.com/video"
    pattern = input("نمط المسلسل [modablaj-terzi-episode-]: ").strip() or "modablaj-terzi-episode-"
    
    if not pattern.endswith('-'):
        pattern += '-'
    
    test_episodes = input("الحلقات (مثال: 1,3,5 أو 1-5) [1-3]: ").strip() or "1-3"
    
    # تحليل الحلقات
    episodes = []
    if '-' in test_episodes:
        start, end = map(int, test_episodes.split('-'))
        episodes = list(range(start, end + 1))
    elif ',' in test_episodes:
        episodes = [int(x.strip()) for x in test_episodes.split(',')]
    else:
        episodes = [int(test_episodes)]
    
    print(f"\n[*] اختبار {len(episodes)} حلقة...")
    
    results = []
    start_time = time.time()
    
    for ep in episodes:
        print(f"\n[*] الحلقة {ep:02d}...")
        
        episode_url = get_final_episode_url_fast(base_url, pattern, ep)
        m3u8_url = extract_m3u8_fast(episode_url)
        
        if m3u8_url:
            print(f"[*] عثر على الرابط: {m3u8_url[:60]}...")
            results.append((ep, True))
        else:
            print(f"[!] فشل استخراج الرابط")
            results.append((ep, False))
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print("[*] نتائج الاختبار:")
    print('='*60)
    
    successful = sum(1 for _, success in results if success)
    print(f"    الناجحة: {successful}/{len(episodes)}")
    print(f"    الوقت: {elapsed:.1f} ثانية")
    
    if successful > 0:
        avg_time = elapsed / len(episodes)
        print(f"    متوسط الوقت: {avg_time:.1f} ثانية")
    
    print('='*60)

if __name__ == "__main__":
    print("="*60)
    print("تنزيل فيديو - سرعة البرق v2.0")
    print("="*60)
    
    print("\nالخيارات السريعة:")
    print("  1. تنزيل سريع لعدة حلقات (متوازي)")
    print("  2. اختبار حلقة واحدة (سريع)")
    print("  3. اختبار دفعة من الحلقات")
    print("  4. تنظيف سريع لمجلد")
    print("  5. خروج")
    
    choice = input("\nاختر الخيار [1]: ").strip() or "1"
    
    if choice == "1":
        main_lightning_speed()
    elif choice == "2":
        test_single_fast()
    elif choice == "3":
        batch_test()
    elif choice == "4":
        dir_path = input("مسار المجلد: ").strip()
        if os.path.isdir(dir_path):
            clean_directory(dir_path)
            print("[✓] تم التنظيف السريع")
        else:
            print("[!] مسار غير صالح")
    else:
        print("[*] انتهى!")
