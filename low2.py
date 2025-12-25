#!/usr/bin/env python3
"""
Ultra Fast Video Downloader for 3seq.com with correct URL handling
"""

import os
import sys
import re
import time
import requests
import subprocess
import shutil
import concurrent.futures
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# ===== CONFIGURATION =====
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
HEADERS = {'User-Agent': USER_AGENT}
MAX_WORKERS = 3
DOWNLOAD_TIMEOUT = 300

def clean_directory(directory):
    """تنظيف الملفات غير المرغوب فيها من المجلد"""
    extensions_to_keep = ['.mp4', '.txt', '.json']
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        # حذف الملفات المؤقتة
        if any(filename.endswith(ext) for ext in ['.part', '.ytdl', '.temp', '.tmp', '.mkv', '.webm', '.m4a']):
            try:
                os.remove(file_path)
                print(f"[*] حذف ملف مؤقت: {filename}")
            except:
                pass
        
        # حذف المجلدات الفارغة
        elif os.path.isdir(file_path) and filename.endswith('.temp.download'):
            try:
                shutil.rmtree(file_path)
                print(f"[*] حذف مجلد مؤقت: {filename}")
            except:
                pass

def install_requirements():
    """تثبيت الحزم المطلوبة"""
    print("[*] فحص المتطلبات...")
    
    packages = ['requests', 'beautifulsoup4']
    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ✗ تثبيت {pkg}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
    
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("  ✓ yt-dlp")
    except:
        print("  ✗ تثبيت yt-dlp...")
        subprocess.run(['pip', 'install', 'yt-dlp'], check=True)
    
    try:
        subprocess.run(['ffmpeg', '--version'], capture_output=True, check=True)
        print("  ✓ ffmpeg")
    except:
        print("  ✗ تثبيت ffmpeg...")
        subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], check=True)

def discover_final_url_with_retry(initial_url, max_retries=3):
    """
    اكتشاف الرابط النهائي بعد إعادة التوجيه والتحويلات
    الآن يتبع نمط: /modablaj-terzi-episode-01-n78j/
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for attempt in range(max_retries):
        try:
            print(f"[*] محاولة {attempt + 1}: الوصول إلى {initial_url}")
            response = session.get(initial_url, timeout=10, allow_redirects=True)
            current_url = response.url
            
            # إذا تم إعادة التوجيه
            if current_url != initial_url:
                print(f"[*] تم إعادة التوجيه إلى: {current_url}")
                return current_url
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # التحقق من أننا في الصفحة الصحيحة
            title = soup.find('title')
            if title:
                print(f"[*] عنوان الصفحة: {title.text[:50]}...")
            
            # البحث عن أي رابط يشبه نمط المسلسل مع الرمز العشوائي
            episode_pattern = r'/video/[^/]+-episode-\d{2}-[a-z0-9]+/'
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link['href']
                if re.search(episode_pattern, href):
                    final_url = urljoin(initial_url, href)
                    if final_url != initial_url:
                        print(f"[*] عثر على رابط الحلقة: {final_url}")
                        return final_url
            
            # البحث في محتوى الصفحة عن الأنماط
            content_pattern = r'(https?://[^"\'\s]+?episode-\d{2}-[a-z0-9]+/?[^"\'\s]*)'
            matches = re.findall(content_pattern, response.text)
            
            for match in matches:
                if '3seq.com' in match:
                    print(f"[*] عثر على رابط في المحتوى: {match}")
                    return match
            
            time.sleep(1)
            
        except Exception as e:
            print(f"[!] خطأ في اكتشاف الرابط: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    print("[!] لم يتم العثور على رابط نهائي، استخدام الرابط الأصلي")
    return initial_url

def extract_video_url_from_watch_page(page_url):
    """
    استخراج رابط الفيديو من صفحة المشاهدة مع ?do=watch
    """
    try:
        # إضافة ?do=watch إذا لم يكن موجوداً
        if '?do=watch' not in page_url:
            if not page_url.endswith('/'):
                page_url += '/'
            watch_url = page_url + '?do=watch'
        else:
            watch_url = page_url
        
        print(f"[*] جلب صفحة المشاهدة: {watch_url}")
        
        session = requests.Session()
        session.headers.update(HEADERS)
        response = session.get(watch_url, timeout=15)
        
        # البحث عن m3u8 مباشرة
        m3u8_patterns = [
            r'(https?://[^"\'\s]+?\.m3u8[^"\'\s]*)',
            r'src:\s*["\']([^"\']+?\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+?\.m3u8[^"\']*)["\']'
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            for match in matches:
                if match and ('m3u8' in match.lower() or 'cdn' in match):
                    if match.startswith('//'):
                        match = 'https:' + match
                    print(f"[*] عثر على m3u8: {match[:80]}...")
                    return match
        
        # البحث عن iframe
        soup = BeautifulSoup(response.text, 'html.parser')
        iframe_sources = []
        
        # جميع إمكانيات iframe
        for iframe in soup.find_all('iframe', {'src': True}):
            src = iframe['src']
            if src and ('vidsp.net' in src or 'player' in src or 'embed' in src):
                if src.startswith('//'):
                    src = 'https:' + src
                iframe_sources.append(src)
                print(f"[*] عثر على iframe: {src[:80]}...")
        
        if iframe_sources:
            return iframe_sources[0]
        
        # البحث عن مصادر الفيديو المباشرة
        video_sources = []
        for video in soup.find_all('video'):
            for source in video.find_all('source', {'src': True}):
                src = source['src']
                if src:
                    video_sources.append(src)
        
        if video_sources:
            print(f"[*] عثر على مصادر فيديو مباشرة")
            return video_sources[0]
        
        # محاولة استخراج من البيانات
        data_patterns = [
            r'data-video=["\']([^"\']+)["\']',
            r'data-src=["\']([^"\']+)["\']',
            r'data-file=["\']([^"\']+)["\']',
            r'video_url\s*=\s*["\']([^"\']+)["\']',
            r'videoUrl\s*=\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in data_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            for match in matches:
                if match and ('http' in match or '//' in match):
                    if match.startswith('//'):
                        match = 'https:' + match
                    print(f"[*] عثر على رابط في البيانات: {match[:80]}...")
                    return match
        
        return None
        
    except Exception as e:
        print(f"[!] خطأ في استخراج رابط الفيديو: {e}")
        return None

def smart_video_url_extractor(base_url, series_pattern, episode_num):
    """
    استخراج ذكي لرابط الفيديو مع معالجة كاملة للمسار
    """
    episode_str = f"{episode_num:02d}"
    
    # الخطوة 1: بناء الرابط الأساسي
    initial_url = f"{base_url}/{series_pattern}{episode_str}"
    print(f"[*] الرابط الأساسي: {initial_url}")
    
    # الخطوة 2: اكتشاف الرابط النهائي (مع الرمز العشوائي)
    final_url = discover_final_url_with_retry(initial_url)
    print(f"[*] الرابط النهائي: {final_url}")
    
    # الخطوة 3: استخراج رابط الفيديو من صفحة المشاهدة
    video_url = extract_video_url_from_watch_page(final_url)
    
    if not video_url:
        print("[!] فشل استخراج رابط الفيديو، محاولة بديلة...")
        
        # محاولة استخدام yt-dlp مباشرة
        try:
            cmd = [
                'yt-dlp',
                '--quiet',
                '--get-url',
                final_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                video_url = result.stdout.strip()
                print(f"[*] yt-dlp أعطى الرابط: {video_url[:80]}...")
        except:
            pass
    
    return video_url

def download_with_optimized_pipeline(video_url, output_file):
    """
    تنزيل محسن مع معالجة أنظف للملفات
    """
    temp_dir = f"{output_file}_temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # إنشاء أسماء ملفات مؤقتة في المجلد المؤقت
        temp_download = os.path.join(temp_dir, "download.temp")
        temp_output = os.path.join(temp_dir, "output.temp.mp4")
        
        # الخطوة 1: التنزيل إلى ملف مؤقت
        print("[*] بدء التنزيل...")
        download_cmd = [
            'yt-dlp',
            '-f', 'worst[height<=480]',
            '--concurrent-fragments', '8',
            '--limit-rate', '0',
            '--retries', '10',
            '--fragment-retries', '10',
            '--no-part',
            '--no-check-certificates',
            '--quiet',
            '--progress',
            '--merge-output-format', 'mp4',
            '-o', temp_download + '.%(ext)s',
            video_url
        ]
        
        download_start = time.time()
        result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        
        if result.returncode != 0:
            print(f"[!] فشل التنزيل: {result.stderr[:200]}")
            return False
        
        # البحث عن الملف الذي تم تنزيله
        downloaded_file = None
        for f in os.listdir(temp_dir):
            if f.startswith("download.temp") and not f.endswith('.part'):
                downloaded_file = os.path.join(temp_dir, f)
                break
        
        if not downloaded_file:
            print("[!] لم يتم العثور على الملف الذي تم تنزيله")
            return False
        
        download_time = time.time() - download_start
        file_size = os.path.getsize(downloaded_file) / (1024*1024)
        print(f"[*] اكتمل التنزيل في {download_time:.1f} ثانية - الحجم: {file_size:.1f} MB")
        
        # الخطوة 2: الضغط السريع جداً
        print("[*] بدء الضغط السريع...")
        compress_cmd = [
            'ffmpeg',
            '-i', downloaded_file,
            '-vf', 'scale=-2:240',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',  # أسرع إعداد
            '-tune', 'fastdecode',   # لسرعة التشغيل
            '-crf', '36',            # ضغط عالي للسرعة
            '-c:a', 'aac',
            '-b:a', '48k',
            '-ac', '1',              # صوت أحادي
            '-y',
            '-threads', '0',         # استخدام كل الأنوية
            '-loglevel', 'error',
            temp_output
        ]
        
        compress_start = time.time()
        result = subprocess.run(compress_cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode != 0:
            print(f"[!] فشل الضغط: {result.stderr[:200]}")
            return False
        
        compress_time = time.time() - compress_start
        
        # الخطوة 3: نقل الملف النهائي
        if os.path.exists(temp_output):
            shutil.move(temp_output, output_file)
            final_size = os.path.getsize(output_file) / (1024*1024)
            total_time = time.time() - download_start
            
            print(f"[✓] اكتمل في {total_time:.1f} ثانية")
            print(f"    التنزيل: {download_time:.1f} ثانية")
            print(f"    الضغط: {compress_time:.1f} ثانية")
            print(f"    الحجم النهائي: {final_size:.1f} MB")
            return True
        else:
            print("[!] الملف النهائي غير موجود")
            return False
            
    except subprocess.TimeoutExpired:
        print("[!] انتهت مهلة العملية")
        return False
    except Exception as e:
        print(f"[!] خطأ: {e}")
        return False
    finally:
        # تنظيف المجلد المؤقت
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def download_alternative_method(video_url, output_file):
    """
    طريقة بديلة للتنزيل مع تقليل العمليات
    """
    try:
        # استخدام yt-dlp مع إعدادات مبسطة
        cmd = [
            'yt-dlp',
            '-f', 'worst[height<=360]',  # البحث عن جودة منخفضة
            '--concurrent-fragments', '4',
            '--no-part',
            '--merge-output-format', 'mp4',
            '--quiet',
            '--progress',
            '--exec', f'mv {{}} {output_file}',
            '-o', 'temp_video',
            video_url
        ]
        
        print("[*] تجربة طريقة التنزيل المبسطة...")
        start_time = time.time()
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        
        if result.returncode == 0 and os.path.exists(output_file):
            elapsed = time.time() - start_time
            size_mb = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] اكتمل في {elapsed:.1f} ثانية - الحجم: {size_mb:.1f} MB")
            return True
        else:
            print("[!] فشلت الطريقة المبسطة")
            return False
            
    except Exception as e:
        print(f"[!] خطأ في الطريقة البديلة: {e}")
        return False

def process_episode_smart(base_url, series_pattern, episode_num, download_dir):
    """
    معالجة حلقة واحدة بذكاء مع تنظيف الملفات
    """
    episode_str = f"{episode_num:02d}"
    print(f"\n{'='*50}")
    print(f"[*] بدء الحلقة {episode_str}")
    print('='*50)
    
    output_file = os.path.join(download_dir, f"الحلقة_{episode_str}.mp4")
    
    # إذا كان الملف موجوداً بالفعل
    if os.path.exists(output_file):
        size = os.path.getsize(output_file) / (1024*1024)
        print(f"[!] الملف موجود بالفعل ({size:.1f} MB)، تخطي...")
        return (episode_num, True, "موجود مسبقاً")
    
    try:
        # استخراج رابط الفيديو
        video_url = smart_video_url_extractor(base_url, series_pattern, episode_num)
        
        if not video_url:
            print(f"[!] فشل استخراج رابط الفيديو للحلقة {episode_str}")
            return (episode_num, False, "فشل استخراج الرابط")
        
        print(f"[*] رابط الفيديو: {video_url[:100]}...")
        
        # المحاولة الأولى: الطريقة المحسنة
        print("[*] المحاولة 1: التنزيل المحسن...")
        if download_with_optimized_pipeline(video_url, output_file):
            # تنظيف المجلد بعد النجاح
            clean_directory(download_dir)
            return (episode_num, True, "نجح بالطريقة المحسنة")
        
        # المحاولة الثانية: الطريقة البديلة
        print("[*] المحاولة 2: الطريقة البديلة...")
        if download_alternative_method(video_url, output_file):
            # تنظيف المجلد بعد النجاح
            clean_directory(download_dir)
            return (episode_num, True, "نجح بالطريقة البديلة")
        
        print(f"[!] فشلت جميع المحاولات للحلقة {episode_str}")
        return (episode_num, False, "فشل جميع المحاولات")
        
    except Exception as e:
        print(f"[!] خطأ غير متوقع للحلقة {episode_str}: {e}")
        return (episode_num, False, str(e))
    finally:
        # تنظيف نهائي للمجلد
        clean_directory(download_dir)

def main_parallel_smart():
    """التنزيل المتوازي الرئيسي مع المعالجة الذكية"""
    print("="*60)
    print("تنزيل فيديو ذكي - جودة 240p")
    print("="*60)
    
    # تثبيت المتطلبات
    install_requirements()
    
    # إدخال المستخدم
    print("\n[*] أدخل معاملات التنزيل:")
    
    base_url = input("الرابط الأساسي [https://x.3seq.com/video]: ").strip()
    if not base_url:
        base_url = "https://x.3seq.com/video"
    
    # نمط المسلسل (يجب أن ينتهي بـ -)
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
        # تنظيف المجلد الموجود
        clean_directory(download_dir)
        print(f"[*] استخدام المجلد الموجود: {download_dir}")
    else:
        os.makedirs(download_dir, exist_ok=True)
        print(f"[*] تم إنشاء مجلد جديد: {download_dir}")
    
    # إدخال أرقام الحلقات
    try:
        start_ep = int(input("الحلقة الأولى [1]: ").strip() or "1")
        end_ep = int(input("الحلقة الأخيرة [10]: ").strip() or "10")
        
        if start_ep > end_ep:
            print("[!] الحلقة الأولى يجب أن تكون أصغر من الأخيرة")
            return
    except:
        print("[!] أرقام غير صالحة")
        return
    
    # عدد التنزيلات المتوازية
    workers_input = input(f"التنزيلات المتوازية [1-{MAX_WORKERS}، الافتراضي: 2]: ").strip()
    try:
        parallel_workers = int(workers_input) if workers_input else 2
        parallel_workers = min(max(1, parallel_workers), MAX_WORKERS)
    except:
        parallel_workers = 2
    
    print(f"\n{'='*60}")
    print("[*] بدء التنزيل الذكي")
    print('='*60)
    print(f"    المسلسل: {series_name}")
    print(f"    النمط: {series_pattern}XX")
    print(f"    الحلقات: {start_ep:02d} إلى {end_ep:02d}")
    print(f"    التنزيلات المتوازية: {parallel_workers}")
    print(f"    المجلد: {download_dir}/")
    print('='*60)
    
    # إنشاء قائمة الحلقات
    episodes = list(range(start_ep, end_ep + 1))
    
    # التنزيل المتوازي
    successful = 0
    failed = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_workers) as executor:
        # إرسال المهام
        future_to_ep = {}
        
        for ep in episodes:
            future = executor.submit(
                process_episode_smart,
                base_url,
                series_pattern,
                ep,
                download_dir
            )
            future_to_ep[future] = ep
        
        # معالجة النتائج
        completed = 0
        total = len(episodes)
        
        for future in concurrent.futures.as_completed(future_to_ep):
            ep = future_to_ep[future]
            completed += 1
            
            try:
                ep_num, success, message = future.result()
                
                if success:
                    successful += 1
                    print(f"[✓] الحلقة {ep_num:02d}: {message}")
                else:
                    failed.append(ep_num)
                    print(f"[!] الحلقة {ep_num:02d}: {message}")
                
                # عرض التقدم
                progress = (completed / total) * 100
                print(f"[*] التقدم: {completed}/{total} ({progress:.0f}%)")
                
            except Exception as e:
                failed.append(ep)
                print(f"[!] خطأ غير متوقع للحلقة {ep:02d}: {e}")
    
    # النتائج النهائية
    total_time = time.time() - start_time
    
    print(f"\n{'='*60}")
    print("[*] اكتمل التنزيل")
    print('='*60)
    
    if successful > 0:
        avg_time = total_time / successful
        print(f"[*] الوقت الإجمالي: {total_time:.1f} ثانية")
        print(f"[*] متوسط الوقت للحلقة: {avg_time:.1f} ثانية")
        print(f"[*] الناجحة: {successful}/{total}")
    
    if failed:
        print(f"[!] الفاشلة: {[f'{ep:02d}' for ep in failed]}")
    
    # عرض الملفات النهائية
    print(f"\n[*] الملفات في {download_dir}:")
    try:
        mp4_files = [f for f in sorted(os.listdir(download_dir)) if f.endswith('.mp4')]
        total_size = 0
        
        for file in mp4_files:
            file_path = os.path.join(download_dir, file)
            size = os.path.getsize(file_path) / (1024*1024)
            total_size += size
            print(f"    {file}: {size:.1f} MB")
        
        if total_size > 0:
            print(f"[*] الحجم الإجمالي: {total_size:.1f} MB")
            
    except Exception as e:
        print(f"[!] خطأ في قراءة الملفات: {e}")
    
    print('='*60)

def quick_single_download():
    """تنزيل حلقة واحدة سريع"""
    print("\n[*] تنزيل حلقة واحدة")
    
    url = input("أدخل رابط الحلقة الكامل: ").strip()
    
    if not url:
        print("[!] لم يتم إدخال رابط")
        return
    
    # استخراج اسم للملف
    match = re.search(r'/([^/]+)-episode-', url)
    if match:
        base_name = match.group(1)
    else:
        base_name = "video"
    
    # إنشاء مجلد للتنزيل
    download_dir = f"{base_name}_download"
    os.makedirs(download_dir, exist_ok=True)
    
    output_file = os.path.join(download_dir, f"{base_name}_240p.mp4")
    
    print(f"\n[*] جاري المعالجة...")
    print(f"[*] الملف النهائي: {output_file}")
    
    # استخراج رابط الفيديو
    print("[*] استخراج رابط الفيديو...")
    video_url = extract_video_url_from_watch_page(url)
    
    if not video_url:
        print("[!] فشل استخراج رابط الفيديو")
        return
    
    # التنزيل
    print("[*] بدء التنزيل...")
    start_time = time.time()
    
    if download_with_optimized_pipeline(video_url, output_file):
        elapsed = time.time() - start_time
        if os.path.exists(output_file):
            size = os.path.getsize(output_file) / (1024*1024)
            print(f"\n[✓] اكتمل التنزيل!")
            print(f"    الملف: {output_file}")
            print(f"    الحجم: {size:.1f} MB")
            print(f"    الوقت: {elapsed:.1f} ثانية")
    else:
        print(f"\n[!] فشل التنزيل")

if __name__ == "__main__":
    print("="*60)
    print("تنزيل فيديو - إصدار محسن")
    print("="*60)
    
    print("\nالخيارات:")
    print("  1. تنزيل عدة حلقات (ذكي)")
    print("  2. تنزيل حلقة واحدة")
    print("  3. تنظيف مجلد (حذف الملفات المؤقتة)")
    print("  4. خروج")
    
    choice = input("\nاختر الخيار [1]: ").strip() or "1"
    
    if choice == "1":
        main_parallel_smart()
    elif choice == "2":
        quick_single_download()
    elif choice == "3":
        dir_path = input("أدخل مسار المجلد المراد تنظيفه: ").strip()
        if os.path.isdir(dir_path):
            clean_directory(dir_path)
            print("[✓] تم تنظيف المجلد")
        else:
            print("[!] مسار غير صالح")
    else:
        print("[*] مع السلامة!")
