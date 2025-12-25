#!/usr/bin/env python3
"""
Ultra Fast Video Downloader for 3seq.com - Enhanced Version
"""

import os
import sys
import re
import time
import requests
import subprocess
import shutil
import concurrent.futures
from urllib.parse import urljoin, parse_qs, urlparse
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
    'Upgrade-Insecure-Requests': '1'
}
MAX_WORKERS = 3
DOWNLOAD_TIMEOUT = 300

def clean_directory(directory):
    """تنظيف الملفات غير المرغوب فيها"""
    if not os.path.exists(directory):
        return
    
    extensions_to_delete = ['.part', '.ytdl', '.temp', '.tmp', '.mkv', '.webm', '.m4a', '.frag', '.ytdlp']
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        try:
            # حذف الملفات المؤقتة
            if any(filename.endswith(ext) for ext in extensions_to_delete):
                os.remove(file_path)
                print(f"[*] حذف مؤقت: {filename}")
            
            # حذف المجلدات المؤقتة
            elif os.path.isdir(file_path) and filename.endswith('.temp'):
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
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("  ✓ ffmpeg")
    except:
        print("  ✗ تثبيت ffmpeg...")
        subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], check=True)

def get_redirect_url(initial_url, max_redirects=5):
    """الحصول على رابط التوجيه النهائي"""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        # عدم متابعة التوجيهات تلقائياً لرؤية جميع الخطوات
        response = session.get(initial_url, timeout=10, allow_redirects=False)
        
        if response.status_code in [301, 302, 303, 307, 308]:
            redirect_url = response.headers.get('Location')
            if redirect_url:
                if redirect_url.startswith('/'):
                    redirect_url = urljoin(initial_url, redirect_url)
                print(f"[*] توجيه إلى: {redirect_url}")
                return redirect_url
        
        # إذا لم يكن هناك توجيه، البحث في HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن meta refresh
        meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
        if meta_refresh and 'url=' in meta_refresh.get('content', ''):
            redirect_url = meta_refresh['content'].split('url=')[-1].strip()
            if redirect_url.startswith('/'):
                redirect_url = urljoin(initial_url, redirect_url)
            print(f"[*] Meta refresh إلى: {redirect_url}")
            return redirect_url
        
        # البحث عن روابط JavaScript
        script_patterns = [
            r'window\.location\s*=\s*["\']([^"\']+)["\']',
            r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
            r'location\.replace\s*\(\s*["\']([^"\']+)["\']',
            r'location\.href\s*=\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in script_patterns:
            matches = re.findall(pattern, response.text)
            for match in matches:
                if match and 'http' in match:
                    print(f"[*] JavaScript redirect إلى: {match}")
                    return match
                elif match and match.startswith('/'):
                    redirect_url = urljoin(initial_url, match)
                    print(f"[*] JavaScript redirect إلى: {redirect_url}")
                    return redirect_url
        
        return initial_url
        
    except Exception as e:
        print(f"[!] خطأ في تتبع التوجيه: {e}")
        return initial_url

def discover_final_episode_url(base_url, series_pattern, episode_num):
    """اكتشاف رابط الحلقة النهائي مع الرمز العشوائي"""
    episode_str = f"{episode_num:02d}"
    
    # الرابط الأساسي (بدون الرمز العشوائي)
    initial_url = f"{base_url}/{series_pattern}{episode_str}"
    print(f"[*] المحاولة: {initial_url}")
    
    # متابعة التوجيهات
    current_url = initial_url
    visited_urls = []
    
    for _ in range(5):  # أقصى 5 توجيهات
        if current_url in visited_urls:
            break
            
        visited_urls.append(current_url)
        next_url = get_redirect_url(current_url)
        
        if next_url == current_url or next_url in visited_urls:
            break
            
        current_url = next_url
    
    print(f"[*] الرابط النهائي: {current_url}")
    return current_url

def extract_video_url_from_page(page_url):
    """استخراج رابط الفيديو من صفحة المشاهدة"""
    try:
        # التأكد من وجود ?do=watch
        if '?do=watch' not in page_url:
            if not page_url.endswith('/'):
                page_url += '/'
            watch_url = page_url + '?do=watch'
        else:
            watch_url = page_url
        
        print(f"[*] جلب: {watch_url}")
        
        session = requests.Session()
        session.headers.update(HEADERS)
        response = session.get(watch_url, timeout=15)
        
        # حفظ HTML للتصحيح (اختياري)
        debug_file = f"debug_page_{int(time.time())}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"[*] تم حفظ HTML للتصحيح: {debug_file}")
        
        # البحث عن مصادر الفيديو بطرق متعددة
        
        # 1. البحث عن iframe
        soup = BeautifulSoup(response.text, 'html.parser')
        iframes = soup.find_all('iframe', {'src': True})
        
        for iframe in iframes:
            src = iframe['src']
            if any(keyword in src for keyword in ['vidsp.net', 'player', 'embed', 'video', 'stream']):
                if src.startswith('//'):
                    src = 'https:' + src
                print(f"[*] iframe: {src}")
                return src
        
        # 2. البحث عن video tags
        videos = soup.find_all('video')
        for video in videos:
            if video.get('src'):
                src = video['src']
                if src.startswith('//'):
                    src = 'https:' + src
                print(f"[*] video tag: {src}")
                return src
            
            # مصادر داخل video tag
            sources = video.find_all('source', {'src': True})
            for source in sources:
                src = source['src']
                if src.startswith('//'):
                    src = 'https:' + src
                print(f"[*] video source: {src}")
                return src
        
        # 3. البحث عن m3u8 في الكود
        m3u8_patterns = [
            r'src\s*[:=]\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'file\s*[:=]\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'videoSrc\s*[:=]\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'url\s*[:=]\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)'
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            for match in matches:
                if match and '.m3u8' in match.lower():
                    if match.startswith('//'):
                        match = 'https:' + match
                    print(f"[*] m3u8: {match[:100]}...")
                    return match
        
        # 4. استخدام yt-dlp لاستخراج الرابط
        print("[*] محاولة استخدام yt-dlp لاستخراج الرابط...")
        try:
            cmd = [
                'yt-dlp',
                '--quiet',
                '--no-warnings',
                '--get-url',
                watch_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                video_url = result.stdout.strip()
                print(f"[*] yt-dlp أعطى: {video_url[:100]}...")
                return video_url
        except:
            pass
        
        return None
        
    except Exception as e:
        print(f"[!] خطأ في استخراج الفيديو: {e}")
        return None

def get_best_stream_url(video_url):
    """الحصول على أفضل تدفق متاح"""
    try:
        # الحصول على معلومات التدفقات
        cmd = [
            'yt-dlp',
            '-F',
            '--quiet',
            '--no-warnings',
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # تحليل النتائج للعثور على أقل جودة
        lines = result.stdout.split('\n')
        format_ids = []
        
        for line in lines:
            if 'x' in line and ('mp4' in line.lower() or 'm3u8' in line.lower()):
                parts = line.split()
                if parts and parts[0].isdigit():
                    format_id = parts[0]
                    
                    # البحث عن الارتفاع
                    height_match = re.search(r'(\d{3,4})x\d{3,4}', line)
                    if height_match:
                        height = int(height_match.group(1))
                        # تفضيل التدفقات المنخفضة (144p, 240p, 360p)
                        if height <= 480:
                            format_ids.append((height, format_id))
        
        if format_ids:
            # ترتيب حسب الارتفاع (الأقل أولاً)
            format_ids.sort()
            best_height, best_format = format_ids[0]
            print(f"[*] أفضل تدفق: {best_format} ({best_height}p)")
            return best_format
        
        return 'worst'
        
    except Exception as e:
        print(f"[!] خطأ في اختيار التدفق: {e}")
        return 'worst'

def download_video_smart(video_url, output_file):
    """تنزيل ذكي للفيديو مع معالجة التدفقات المختلفة"""
    try:
        # الحصول على معرف التنسيق الأفضل
        format_id = get_best_stream_url(video_url)
        
        print(f"[*] بدء التنزيل باستخدام التنسيق: {format_id}")
        
        # تنزيل مباشر مع yt-dlp
        cmd = [
            'yt-dlp',
            '-f', format_id,
            '--concurrent-fragments', '8',
            '--limit-rate', '0',
            '--retries', '10',
            '--fragment-retries', '10',
            '--no-check-certificates',
            '--no-part',
            '--quiet',
            '--progress',
            '--merge-output-format', 'mp4',
            '-o', output_file,
            video_url
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        
        if result.returncode == 0 and os.path.exists(output_file):
            download_time = time.time() - start_time
            file_size = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] اكتمل التنزيل في {download_time:.1f} ثانية")
            print(f"[*] الحجم: {file_size:.1f} MB")
            
            # التحقق من الحجم والضغط إذا لزم الأمر
            if file_size > 100:  # إذا كان أكبر من 100MB، قم بالضغط
                print("[*] الحجم كبير، جاري الضغط إلى 240p...")
                return compress_to_240p(output_file)
            else:
                return True
        else:
            print("[!] فشل التنزيل المباشر")
            return False
            
    except subprocess.TimeoutExpired:
        print("[!] انتهت مهلة التنزيل")
        return False
    except Exception as e:
        print(f"[!] خطأ في التنزيل: {e}")
        return False

def compress_to_240p(input_file):
    """ضغط الفيديو إلى 240p"""
    try:
        temp_file = input_file.replace('.mp4', '_240p_temp.mp4')
        
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-vf', 'scale=-2:240',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '28',
            '-c:a', 'aac',
            '-b:a', '64k',
            '-y',
            temp_file
        ]
        
        print("[*] جاري الضغط إلى 240p...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(temp_file):
            # استبدال الملف الأصلي بالمضغوط
            os.remove(input_file)
            shutil.move(temp_file, input_file)
            
            final_size = os.path.getsize(input_file) / (1024*1024)
            print(f"[✓] تم الضغط - الحجم النهائي: {final_size:.1f} MB")
            return True
        else:
            print("[!] فشل الضغط")
            return False
            
    except Exception as e:
        print(f"[!] خطأ في الضغط: {e}")
        return False

def download_direct_lowest(video_url, output_file):
    """تنزيل مباشر لأدنى جودة متاحة"""
    try:
        cmd = [
            'yt-dlp',
            '-f', 'worst[height<=480]',  # أسوأ جودة حتى 480p
            '--concurrent-fragments', '4',
            '--limit-rate', '0',
            '--retries', '5',
            '--no-check-certificates',
            '--no-part',
            '--quiet',
            '--progress',
            '--merge-output-format', 'mp4',
            '-o', output_file,
            video_url
        ]
        
        print("[*] تنزيل أدنى جودة...")
        start_time = time.time()
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        
        if result.returncode == 0 and os.path.exists(output_file):
            elapsed = time.time() - start_time
            size = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] اكتمل في {elapsed:.1f} ثانية - {size:.1f} MB")
            
            # إذا كان الحجم لا يزال كبيراً
            if size > 50:
                print("[*] جاري تحسين الحجم...")
                compress_to_240p(output_file)
                
            return True
        else:
            return False
            
    except Exception as e:
        print(f"[!] خطأ في التنزيل المباشر: {e}")
        return False

def process_episode_enhanced(base_url, series_pattern, episode_num, download_dir):
    """معالجة محسنة للحلقة"""
    episode_str = f"{episode_num:02d}"
    print(f"\n{'='*60}")
    print(f"[*] معالجة الحلقة {episode_str}")
    print('='*60)
    
    output_file = os.path.join(download_dir, f"الحلقة_{episode_str}.mp4")
    
    # تخطي إذا كان الملف موجوداً
    if os.path.exists(output_file):
        size = os.path.getsize(output_file) / (1024*1024)
        print(f"[*] الملف موجود ({size:.1f} MB) - تخطي")
        return (episode_num, True, "موجود مسبقاً")
    
    try:
        # الخطوة 1: الحصول على رابط الحلقة النهائي
        episode_url = discover_final_episode_url(base_url, series_pattern, episode_num)
        
        # الخطوة 2: استخراج رابط الفيديو
        video_url = extract_video_url_from_page(episode_url)
        
        if not video_url:
            print(f"[!] فشل استخراج رابط الفيديو للحلقة {episode_str}")
            return (episode_num, False, "فشل استخراج الرابط")
        
        print(f"[*] تم العثور على رابط الفيديو")
        
        # الخطوة 3: محاولة التنزيل الذكي
        print("[*] محاولة التنزيل الذكي...")
        if download_video_smart(video_url, output_file):
            return (episode_num, True, "نجح بالتنزيل الذكي")
        
        # الخطوة 4: محاولة التنزيل المباشر
        print("[*] محاولة التنزيل المباشر...")
        if download_direct_lowest(video_url, output_file):
            return (episode_num, True, "نجح بالتنزيل المباشر")
        
        print(f"[!] فشلت جميع المحاولات للحلقة {episode_str}")
        return (episode_num, False, "فشل جميع المحاولات")
        
    except Exception as e:
        print(f"[!] خطأ في معالجة الحلقة {episode_str}: {e}")
        return (episode_num, False, str(e))

def main():
    """الدالة الرئيسية"""
    print("="*60)
    print("تنزيل فيديو محسن - دعم التدفقات العالية")
    print("="*60)
    
    install_requirements()
    
    # الإدخال
    print("\n[*] أدخل المعلومات المطلوبة:")
    
    base_url = input("الرابط الأساسي [https://x.3seq.com/video]: ").strip()
    if not base_url:
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
    counter = 1
    while os.path.exists(download_dir):
        download_dir = f"{series_name}_{counter}"
        counter += 1
    
    os.makedirs(download_dir, exist_ok=True)
    
    # تنظيف المجلد قبل البدء
    clean_directory(download_dir)
    
    # إدخال الحلقات
    try:
        start_ep = int(input("الحلقة الأولى [1]: ").strip() or "1")
        end_ep = int(input("الحلقة الأخيرة [10]: ").strip() or "10")
        
        if start_ep > end_ep:
            start_ep, end_ep = end_ep, start_ep
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
    print("[*] بدء العملية")
    print('='*60)
    print(f"    المسلسل: {series_name}")
    print(f"    النمط: {series_pattern}XX")
    print(f"    الحلقات: {start_ep:02d} إلى {end_ep:02d}")
    print(f"    المتوازية: {parallel_workers}")
    print(f"    المجلد: {download_dir}/")
    print('='*60)
    
    # قائمة الحلقات
    episodes = list(range(start_ep, end_ep + 1))
    
    # التنزيل المتوازي
    successful = 0
    failed = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_workers) as executor:
        futures = []
        
        for ep in episodes:
            future = executor.submit(
                process_episode_enhanced,
                base_url,
                series_pattern,
                ep,
                download_dir
            )
            futures.append(future)
        
        # تتبع التقدم
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                ep_num, success, message = future.result()
                
                if success:
                    successful += 1
                    status = "✓"
                else:
                    failed.append(ep_num)
                    status = "✗"
                
                print(f"{status} الحلقة {ep_num:02d}: {message}")
                
                # عرض التقدم
                progress = (i / len(episodes)) * 100
                print(f"[*] التقدم: {i}/{len(episodes)} ({progress:.0f}%)")
                
            except Exception as e:
                print(f"[!] خطأ غير متوقع: {e}")
    
    # النتائج
    total_time = time.time() - start_time
    
    print(f"\n{'='*60}")
    print("[*] النتائج النهائية")
    print('='*60)
    print(f"    الوقت الإجمالي: {total_time:.1f} ثانية")
    print(f"    الناجحة: {successful}/{len(episodes)}")
    
    if failed:
        print(f"    الفاشلة: {[f'{ep:02d}' for ep in failed]}")
    
    # عرض الملفات
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
    print("[*] اكتمل العمل")

def test_single_episode():
    """اختبار حلقة واحدة"""
    print("\n[*] اختبار حلقة واحدة")
    
    url = input("أدخل رابط الحلقة: ").strip()
    
    if not url:
        print("[!] لم يتم إدخال رابط")
        return
    
    # استخراج معلومات من الرابط
    match = re.search(r'/([^/]+)-episode-', url)
    if match:
        name = match.group(1)
    else:
        name = "test"
    
    output_dir = f"test_{int(time.time())}"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{name}_240p.mp4")
    
    print(f"\n[*] جاري الاختبار...")
    print(f"[*] المخرج: {output_file}")
    
    # استخراج رابط الفيديو
    video_url = extract_video_url_from_page(url)
    
    if not video_url:
        print("[!] فشل استخراج رابط الفيديو")
        return
    
    print(f"[*] رابط الفيديو: {video_url[:100]}...")
    
    # التنزيل
    start_time = time.time()
    
    if download_direct_lowest(video_url, output_file):
        elapsed = time.time() - start_time
        if os.path.exists(output_file):
            size = os.path.getsize(output_file) / (1024*1024)
            print(f"\n[✓] نجح الاختبار!")
            print(f"    الوقت: {elapsed:.1f} ثانية")
            print(f"    الحجم: {size:.1f} MB")
            print(f"    الملف: {output_file}")
    else:
        print("\n[!] فشل الاختبار")

if __name__ == "__main__":
    print("="*60)
    print("تنزيل فيديو - إصدار معزز")
    print("="*60)
    
    print("\nالخيارات:")
    print("  1. تنزيل عدة حلقات (رئيسي)")
    print("  2. اختبار حلقة واحدة")
    print("  3. تنظيف مجلد")
    print("  4. خروج")
    
    choice = input("\nاختر الخيار [1]: ").strip() or "1"
    
    if choice == "1":
        main()
    elif choice == "2":
        test_single_episode()
    elif choice == "3":
        dir_path = input("أدخل مسار المجلد: ").strip()
        if os.path.isdir(dir_path):
            clean_directory(dir_path)
            print("[✓] تم التنظيف")
        else:
            print("[!] مسار غير صالح")
    else:
        print("[*] مع السلامة!")
