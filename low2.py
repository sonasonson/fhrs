#!/usr/bin/env python3
"""
Ultra Fast Video Downloader for 3seq.com - Fixed Embed Extraction
"""

import os
import sys
import re
import time
import json
import requests
import subprocess
import shutil
import concurrent.futures
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
            # حذف المجلدات المؤقتة
            elif os.path.isdir(file_path) and filename.endswith('.temp'):
                shutil.rmtree(file_path)
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

def get_final_episode_url(base_url, series_pattern, episode_num):
    """الحصول على رابط الحلقة النهائي"""
    episode_str = f"{episode_num:02d}"
    initial_url = f"{base_url}/{series_pattern}{episode_str}"
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        # محاولة الوصول للرابط
        response = session.get(initial_url, timeout=10, allow_redirects=True)
        final_url = response.url
        
        # التحقق من أننا حصلنا على الرابط الصحيح (يجب أن يحتوي على الرمز العشوائي)
        if final_url != initial_url:
            print(f"[*] الرابط النهائي: {final_url}")
            return final_url
        
        # إذا لم يكن هناك توجيه، نبحث في الصفحة
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن رابط يحتوي على episode-XX- (مع الرمز العشوائي)
        pattern = re.compile(rf'{series_pattern}{episode_str}-[a-z0-9]+')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if pattern.search(href):
                final_url = urljoin(base_url, href)
                print(f"[*] عثر على رابط في الصفحة: {final_url}")
                return final_url
        
        return initial_url
        
    except Exception as e:
        print(f"[!] خطأ في الحصول على الرابط: {e}")
        return initial_url

def extract_from_vidsp_embed(embed_url):
    """استخراج رابط الفيديو من صفحة vidsp.net"""
    try:
        print(f"[*] معالجة صفحة التضمين: {embed_url}")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': USER_AGENT,
            'Referer': 'https://3seq.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })
        
        response = session.get(embed_url, timeout=15)
        
        # حفظ للتصحيح
        debug_file = f"vidsp_debug_{int(time.time())}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"[*] تم حفظ صفحة vidsp: {debug_file}")
        
        # البحث عن مصادر الفيديو بطرق مختلفة
        
        # 1. البحث عن m3u8 مباشرة
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
                    print(f"[*] عثر على m3u8 في vidsp: {match[:100]}...")
                    return match
        
        # 2. البحث عن mp4 مباشرة
        mp4_patterns = [
            r'src\s*[:=]\s*["\'](https?://[^"\']+\.mp4[^"\']*)["\']',
            r'file\s*[:=]\s*["\'](https?://[^"\']+\.mp4[^"\']*)["\']',
            r'(https?://[^\s"\']+\.mp4[^\s"\']*)'
        ]
        
        for pattern in mp4_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            for match in matches:
                if match and '.mp4' in match.lower():
                    if match.startswith('//'):
                        match = 'https:' + match
                    print(f"[*] عثر على mp4 في vidsp: {match[:100]}...")
                    return match
        
        # 3. البحث في script tags عن بيانات JSON
        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string:
                # البحث عن JSON يحتوي على روابط
                json_patterns = [
                    r'{\s*["\']sources["\']\s*:\s*\[[^\]]+\]}',
                    r'{\s*["\']file["\']\s*:\s*["\'][^"\']+["\']\}',
                    r'playerInstance\.setup\((\{.*?\})\)',
                    r'jwplayer\(\)\.setup\((\{.*?\})\)'
                ]
                
                for json_pattern in json_patterns:
                    matches = re.findall(json_pattern, script.string, re.DOTALL)
                    for match in matches:
                        try:
                            data = json.loads(match)
                            if 'sources' in data:
                                for source in data['sources']:
                                    if 'file' in source:
                                        video_url = source['file']
                                        print(f"[*] عثر على رابط في JSON: {video_url[:100]}...")
                                        return video_url
                            elif 'file' in data:
                                video_url = data['file']
                                print(f"[*] عثر على رابط في JSON: {video_url[:100]}...")
                                return video_url
                        except:
                            pass
        
        # 4. استخدام yt-dlp لاستخراج الرابط من صفحة التضمين
        print("[*] محاولة استخدام yt-dlp على صفحة التضمين...")
        try:
            cmd = [
                'yt-dlp',
                '--quiet',
                '--no-warnings',
                '--get-url',
                embed_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                video_url = result.stdout.strip()
                print(f"[*] yt-dlp أعطى الرابط: {video_url[:100]}...")
                return video_url
        except Exception as e:
            print(f"[!] خطأ في yt-dlp: {e}")
        
        return None
        
    except Exception as e:
        print(f"[!] خطأ في معالجة صفحة التضمين: {e}")
        return None

def extract_video_url(episode_url):
    """استخراج رابط الفيديو من صفحة الحلقة"""
    try:
        # إضافة ?do=watch إذا لم يكن موجوداً
        if '?do=watch' not in episode_url:
            if not episode_url.endswith('/'):
                episode_url += '/'
            watch_url = episode_url + '?do=watch'
        else:
            watch_url = episode_url
        
        print(f"[*] جلب صفحة المشاهدة: {watch_url}")
        
        session = requests.Session()
        session.headers.update(HEADERS)
        response = session.get(watch_url, timeout=15)
        
        # حفظ للتصحيح
        debug_file = f"watch_debug_{int(time.time())}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"[*] تم حفظ صفحة المشاهدة: {debug_file}")
        
        # البحث عن iframe
        soup = BeautifulSoup(response.text, 'html.parser')
        iframes = soup.find_all('iframe', {'src': True})
        
        for iframe in iframes:
            src = iframe['src']
            print(f"[*] عثر على iframe: {src}")
            
            # إذا كان رابط vidsp.net
            if 'vidsp.net' in src:
                if src.startswith('//'):
                    src = 'https:' + src
                # استخراج الفيديو من صفحة التضمين
                video_url = extract_from_vidsp_embed(src)
                if video_url:
                    return video_url
        
        # إذا لم نجد iframe، جرب yt-dlp مباشرة على صفحة المشاهدة
        print("[*] لم يتم العثور على iframe، جرب yt-dlp مباشرة...")
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
                print(f"[*] yt-dlp أعطى الرابط: {video_url[:100]}...")
                return video_url
        except:
            pass
        
        return None
        
    except Exception as e:
        print(f"[!] خطأ في استخراج رابط الفيديو: {e}")
        return None

def download_video_simple(video_url, output_file):
    """تنزيل فيديو بطريقة مبسطة"""
    try:
        print(f"[*] بدء تنزيل الفيديو...")
        
        cmd = [
            'yt-dlp',
            '-f', 'best[height<=480]',  # أفضل جودة حتى 480p
            '--concurrent-fragments', '4',
            '--limit-rate', '0',
            '--retries', '5',
            '--fragment-retries', '5',
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
            elapsed = time.time() - start_time
            file_size = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] اكتمل التنزيل في {elapsed:.1f} ثانية")
            print(f"[*] الحجم: {file_size:.1f} MB")
            
            # إذا كان الحجم كبيراً، قم بالضغط
            if file_size > 50:
                print("[*] جاري ضغط الفيديو إلى 240p...")
                return compress_video(output_file)
            
            return True
        else:
            print(f"[!] فشل التنزيل: {result.stderr[:200] if result.stderr else 'لا يوجد تفاصيل'}")
            return False
            
    except subprocess.TimeoutExpired:
        print("[!] انتهت مهلة التنزيل")
        return False
    except Exception as e:
        print(f"[!] خطأ في التنزيل: {e}")
        return False

def compress_video(input_file):
    """ضغط الفيديو إلى 240p"""
    try:
        temp_file = input_file.replace('.mp4', '_compressed.mp4')
        
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-vf', 'scale=-2:240',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '28',
            '-c:a', 'aac',
            '-b:a', '64k',
            '-y',
            '-threads', '0',
            temp_file
        ]
        
        print("[*] جاري ضغط الفيديو...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(temp_file):
            # استبدال الملف القديم
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

def process_single_episode(base_url, series_pattern, episode_num, download_dir):
    """معالجة حلقة واحدة"""
    episode_str = f"{episode_num:02d}"
    print(f"\n{'='*50}")
    print(f"[*] معالجة الحلقة {episode_str}")
    print('='*50)
    
    output_file = os.path.join(download_dir, f"الحلقة_{episode_str}.mp4")
    
    # تخطي إذا كان الملف موجوداً
    if os.path.exists(output_file):
        size = os.path.getsize(output_file) / (1024*1024)
        print(f"[*] الملف موجود ({size:.1f} MB) - تخطي")
        return (episode_num, True, "موجود مسبقاً")
    
    try:
        # الخطوة 1: الحصول على رابط الحلقة النهائي
        episode_url = get_final_episode_url(base_url, series_pattern, episode_num)
        
        # الخطوة 2: استخراج رابط الفيديو
        video_url = extract_video_url(episode_url)
        
        if not video_url:
            print(f"[!] فشل استخراج رابط الفيديو")
            return (episode_num, False, "فشل استخراج الرابط")
        
        print(f"[*] تم العثور على رابط الفيديو: {video_url[:100]}...")
        
        # الخطوة 3: تنزيل الفيديو
        if download_video_simple(video_url, output_file):
            return (episode_num, True, "نجح التنزيل")
        else:
            return (episode_num, False, "فشل التنزيل")
        
    except Exception as e:
        print(f"[!] خطأ في معالجة الحلقة: {e}")
        return (episode_num, False, str(e))

def main_parallel():
    """الدالة الرئيسية للتنزيل المتوازي"""
    print("="*60)
    print("تنزيل فيديو - استخراج محسن من vidsp.net")
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
                process_single_episode,
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

def test_video_extraction():
    """اختبار استخراج الفيديو"""
    print("\n[*] اختبار استخراج الفيديو")
    
    url = input("أدخل رابط الحلقة: ").strip()
    
    if not url:
        print("[!] لم يتم إدخال رابط")
        return
    
    print(f"\n[*] جاري الاختبار...")
    
    # استخراج رابط الفيديو
    video_url = extract_video_url(url)
    
    if video_url:
        print(f"\n[✓] نجح الاستخراج!")
        print(f"[*] رابط الفيديو: {video_url}")
        
        # اختبار التنزيل
        test_file = f"test_video_{int(time.time())}.mp4"
        print(f"[*] جاري اختبار التنزيل...")
        
        if download_video_simple(video_url, test_file):
            if os.path.exists(test_file):
                size = os.path.getsize(test_file) / (1024*1024)
                print(f"[✓] نجح التنزيل!")
                print(f"[*] الملف: {test_file}")
                print(f"[*] الحجم: {size:.1f} MB")
                # حذف الملف الاختباري
                os.remove(test_file)
        else:
            print("[!] فشل التنزيل")
    else:
        print("\n[!] فشل استخراج رابط الفيديو")

if __name__ == "__main__":
    print("="*60)
    print("تنزيل فيديو - إصلاح استخراج vidsp.net")
    print("="*60)
    
    print("\nالخيارات:")
    print("  1. تنزيل عدة حلقات (رئيسي)")
    print("  2. اختبار استخراج الفيديو")
    print("  3. تنظيف مجلد")
    print("  4. خروج")
    
    choice = input("\nاختر الخيار [1]: ").strip() or "1"
    
    if choice == "1":
        main_parallel()
    elif choice == "2":
        test_video_extraction()
    elif choice == "3":
        dir_path = input("أدخل مسار المجلد: ").strip()
        if os.path.isdir(dir_path):
            clean_directory(dir_path)
            print("[✓] تم التنظيف")
        else:
            print("[!] مسار غير صالح")
    else:
        print("[*] مع السلامة!")
