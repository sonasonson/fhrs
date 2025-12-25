#!/usr/bin/env python3
"""
Enhanced Video Downloader for 3seq.com
Direct 240p download with PARALLEL processing and high speed
"""

import os
import sys
import re
import time
import requests
import subprocess
import concurrent.futures
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import datetime

# ===== CONFIGURATION =====
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
HEADERS = {'User-Agent': USER_AGENT}
MAX_WORKERS = 3  # عدد التنزيلات المتوازية
DOWNLOAD_TIMEOUT = 300  # 5 دقائق لكل حلقة

def install_requirements():
    """Install required packages"""
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

def discover_final_url(initial_url, max_retries=2):
    """Discover the final URL after dynamic transformation"""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for attempt in range(max_retries):
        try:
            response = session.get(initial_url, timeout=10, allow_redirects=True)
            current_url = response.url
            
            if current_url != initial_url:
                return current_url
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for meta refresh
            meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if meta_refresh and 'url=' in meta_refresh.get('content', ''):
                new_url = meta_refresh['content'].split('url=')[-1]
                if new_url:
                    return urljoin(initial_url, new_url)
            
            # Look for canonical URL
            canonical = soup.find('link', {'rel': 'canonical'})
            if canonical and canonical.get('href'):
                final_url = canonical['href']
                if final_url != initial_url:
                    return final_url
            
            time.sleep(1)
                
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
    
    return initial_url

def extract_video_embed_url(page_url):
    """Extract video embed URL from watch page"""
    try:
        if '?do=watch' not in page_url:
            if not page_url.endswith('/'):
                page_url += '/'
            watch_url = page_url + '?do=watch'
        else:
            watch_url = page_url
        
        response = requests.get(watch_url, headers=HEADERS, timeout=10)
        
        # Method 1: Direct m3u8
        m3u8_pattern = r'(https?://[^\s"\']+\.m3u8[^\s"\']*)'
        m3u8_matches = re.findall(m3u8_pattern, response.text)
        for match in m3u8_matches:
            if 'cdn-vids.xyz' in match or 'm3u8' in match.lower():
                return match
        
        # Method 2: Iframe
        soup = BeautifulSoup(response.text, 'html.parser')
        iframe = soup.find('iframe', {'src': re.compile(r'vidsp\.net|player')})
        if iframe:
            iframe_src = iframe.get('src')
            if iframe_src:
                if iframe_src.startswith('//'):
                    iframe_src = 'https:' + iframe_src
                return iframe_src
        
        return None
        
    except Exception as e:
        return None

def download_ultra_fast(video_url, output_file):
    """
    أسرع طريقة للتنزيل - تنزيل مباشر وتحويل سريع
    """
    try:
        # استخدام yt-dlp مع خيارات السرعة القصوى
        cmd = [
            'yt-dlp',
            '-f', 'worst[height<=480]',  # أسوأ جودة حتى 480p
            '--no-part',
            '--concurrent-fragments', '8',  # 8 أجزاء متوازية
            '--buffer-size', '16K',
            '--http-chunk-size', '10M',
            '--limit-rate', '0',  # لا حدود للسرعة
            '--retries', '3',
            '--fragment-retries', '3',
            '--skip-unavailable-fragments',
            '--merge-output-format', 'mp4',
            '--external-downloader', 'aria2c',  # إذا كان مثبتاً
            '--external-downloader-args', '-x 8 -s 8 -k 1M',
            '--exec', f'ffmpeg -i {{}} -vf scale=-2:240 -c:v libx264 -preset ultrafast -crf 30 -c:a aac -b:a 64k -y {output_file}',
            '-o', 'temp_%(title)s.%(ext)s',
            video_url
        ]
        
        print(f"[*] بدء التنزيل السريع للحلقة...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        
        if result.returncode == 0 and os.path.exists(output_file):
            size_mb = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] اكتمل التنزيل: {size_mb:.1f} MB")
            return True
        else:
            print(f"[!] فشل التنزيل السريع، تجربة الطريقة البديلة...")
            return download_fallback(video_url, output_file)
            
    except subprocess.TimeoutExpired:
        print(f"[!] انتهت مهلة التنزيل")
        return False
    except Exception as e:
        print(f"[!] خطأ في التنزيل السريع: {e}")
        return False

def download_fallback(video_url, output_file):
    """
    طريقة بديلة إذا فشلت الطريقة السريعة
    """
    try:
        # تنزيل مباشر مع تحويل متزامن
        cmd = [
            'yt-dlp',
            '-f', 'worst',
            '--concurrent-fragments', '4',
            '--no-part',
            '--merge-output-format', 'mp4',
            '--exec', 'ffmpeg -i {} -vf scale=-2:240 -c:v libx264 -preset veryfast -crf 28 -c:a aac -b:a 64k -y {}_240p.mp4 && rm {}',
            '-o', output_file.replace('.mp4', ''),
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        final_file = output_file.replace('.mp4', '_240p.mp4')
        
        if result.returncode == 0:
            if os.path.exists(final_file):
                os.rename(final_file, output_file)
                return True
            elif os.path.exists(output_file):
                return True
        return False
        
    except Exception as e:
        print(f"[!] خطأ في الطريقة البديلة: {e}")
        return False

def process_single_episode(args):
    """
    معالجة حلقة واحدة (للتوازي)
    """
    base_url, series_pattern, episode_num, download_dir = args
    
    episode_str = f"{episode_num:02d}"
    print(f"\n[*] بدء معالجة الحلقة {episode_str}")
    
    try:
        # بناء URL
        if 's01e' in series_pattern.lower():
            initial_url = f"{base_url}/{series_pattern}{episode_str}"
        else:
            initial_url = f"{base_url}/{series_pattern}{episode_num}"
        
        print(f"[*] URL: {initial_url}")
        
        # الحصول على الرابط النهائي
        start_time = time.time()
        final_url = discover_final_url(initial_url)
        print(f"[*] الرابط النهائي: {final_url}")
        
        # استخراج رابط الفيديو
        video_url = extract_video_embed_url(final_url)
        if not video_url:
            print(f"[!] فشل في استخراج رابط الفيديو للحلقة {episode_str}")
            return (episode_num, False, "فشل استخراج الرابط")
        
        print(f"[*] رابط الفيديو: {video_url[:80]}...")
        
        # اسم ملف الإخراج
        output_file = f"{download_dir}/الحلقة_{episode_str}.mp4"
        
        # التنزيل
        if download_ultra_fast(video_url, output_file):
            elapsed = time.time() - start_time
            size_mb = os.path.getsize(output_file) / (1024*1024) if os.path.exists(output_file) else 0
            print(f"[✓] اكتملت الحلقة {episode_str} في {elapsed:.1f} ثانية ({size_mb:.1f} MB)")
            return (episode_num, True, f"اكتمل في {elapsed:.1f} ثانية")
        else:
            return (episode_num, False, "فشل التنزيل")
        
    except Exception as e:
        print(f"[!] خطأ في معالجة الحلقة {episode_str}: {e}")
        return (episode_num, False, str(e))

def main_parallel():
    """التنزيل المتوازي الرئيسي"""
    print("="*60)
    print("تنزيل فيديو متوازي - جودة 240p")
    print("="*60)
    
    # تثبيت المتطلبات
    install_requirements()
    
    # إدخال المستخدم
    print("\n[*] أدخل معاملات التنزيل:")
    
    base_url = input("الرابط الأساسي [https://x.3seq.com/video]: ").strip()
    if not base_url:
        base_url = "https://x.3seq.com/video"
    
    default_pattern = "modablaj-sarmasik-zamani-episode-"
    series = input(f"نمط المسلسل [{default_pattern}]: ").strip()
    if not series:
        series = default_pattern
    
    # استخراج اسم المسلسل للمجلد
    series_name = "المسلسل"
    match = re.search(r'([a-zA-Z]+)-', series)
    if match:
        series_name = match.group(1)
    
    # إنشاء مجلد التنزيل باسم المسلسل فقط
    download_dir = series_name
    counter = 1
    while os.path.exists(download_dir):
        download_dir = f"{series_name}_{counter}"
        counter += 1
    
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        start_ep = input("الحلقة الأولى [1]: ").strip()
        start_ep = int(start_ep) if start_ep else 1
        
        end_ep = input("الحلقة الأخيرة [10]: ").strip()
        end_ep = int(end_ep) if end_ep else 10
    except:
        print("[!] أرقام حلقات غير صالحة")
        return
    
    # عدد العمليات المتوازية
    workers = input(f"عدد التنزيلات المتوازية [1-{MAX_WORKERS}، الافتراضي: 3]: ").strip()
    try:
        workers = int(workers) if workers else MAX_WORKERS
        workers = min(max(1, workers), MAX_WORKERS)
    except:
        workers = MAX_WORKERS
    
    print(f"\n{'='*60}")
    print("[*] بدء التنزيل المتوازي")
    print(f"    المسلسل: {series_name}")
    print(f"    الحلقات: من {start_ep:02d} إلى {end_ep:02d}")
    print(f"    الجودة: 240p مضمونة")
    print(f"    التنزيلات المتوازية: {workers}")
    print(f"    المجلد: {download_dir}/")
    print('='*60)
    
    # إعداد قائمة الحلقات
    episodes = list(range(start_ep, end_ep + 1))
    task_args = [(base_url, series, ep, download_dir) for ep in episodes]
    
    # تنزيل متوازي
    successful = 0
    failed = []
    results = []
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        # إرسال جميع المهام
        future_to_ep = {executor.submit(process_single_episode, args): args[2] for args in task_args}
        
        # متابعة النتائج
        for future in concurrent.futures.as_completed(future_to_ep):
            ep = future_to_ep[future]
            try:
                ep_num, success, message = future.result()
                if success:
                    successful += 1
                    print(f"[✓] الحلقة {ep_num:02d}: {message}")
                else:
                    failed.append(ep_num)
                    print(f"[!] الحلقة {ep_num:02d}: {message}")
            except Exception as e:
                failed.append(ep)
                print(f"[!] خطأ غير متوقع للحلقة {ep:02d}: {e}")
    
    # الملخص
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print("[*] اكتمل التنزيل")
    print('='*60)
    print(f"[*] الوقت الإجمالي: {total_time:.1f} ثانية")
    print(f"[*] الحلقات الناجحة: {successful}/{len(episodes)}")
    
    if failed:
        print(f"[!] الحلقات الفاشلة: {[f'{ep:02d}' for ep in failed]}")
    
    # عرض أحجام الملفات
    print(f"\n[*] الملفات في {download_dir}:")
    total_size = 0
    try:
        mp4_files = [f for f in os.listdir(download_dir) if f.endswith('.mp4')]
        for file in sorted(mp4_files):
            size = os.path.getsize(f"{download_dir}/{file}") / (1024*1024)
            total_size += size
            print(f"    {file}: {size:.1f} MB")
        
        if total_size > 0:
            print(f"[*] الحجم الإجمالي: {total_size:.1f} MB")
            if successful > 0:
                avg_size = total_size / successful
                avg_time = total_time / successful if successful > 0 else 0
                print(f"[*] متوسط الحجم للحلقة: {avg_size:.1f} MB")
                print(f"[*] متوسط الوقت للحلقة: {avg_time:.1f} ثانية")
    except Exception as e:
        print(f"[!] خطأ في قراءة الملفات: {e}")
    
    print('='*60)

def quick_download_single():
    """تنزيل سريع لحلقة واحدة"""
    print("\n[*] تنزيل حلقة واحدة سريع")
    url = input("أدخل رابط الحلقة الكامل: ").strip()
    
    if not url.startswith('http'):
        print("[!] رابط غير صالح")
        return
    
    # استخراج اسم المسلسل للملف
    series_match = re.search(r'/([^/]+)-episode-', url)
    if series_match:
        series_name = series_match.group(1)
    else:
        series_name = "episode"
    
    output_file = f"{series_name}_240p.mp4"
    
    print(f"\n[*] التنزيل إلى: {output_file}")
    
    # استخراج رابط الفيديو
    final_url = discover_final_url(url)
    video_url = extract_video_embed_url(final_url)
    
    if not video_url:
        print("[!] فشل استخراج رابط الفيديو")
        return
    
    # التنزيل
    start_time = time.time()
    if download_ultra_fast(video_url, output_file):
        elapsed = time.time() - start_time
        size = os.path.getsize(output_file) / (1024*1024)
        print(f"\n[✓] نجاح! الملف: {output_file} ({size:.1f} MB)")
        print(f"[*] الوقت المستغرق: {elapsed:.1f} ثانية")
    else:
        print(f"\n[!] فشل التنزيل")

if __name__ == "__main__":
    print("="*60)
    print("تنزيل فيديو - جودة 240p مع توازي")
    print("="*60)
    
    print("\nالخيارات:")
    print("  1. تنزيل عدة حلقات (متوازي)")
    print("  2. تنزيل حلقة واحدة سريع")
    print("  3. خروج")
    
    choice = input("\nاختر الخيار [1]: ").strip() or "1"
    
    if choice == "1":
        main_parallel()
    elif choice == "2":
        quick_download_single()
    else:
        print("[*] مع السلامة!")
