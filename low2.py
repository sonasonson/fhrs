#!/usr/bin/env python3
"""
Ultra Fast Video Downloader for 3seq.com
Direct 240p download with parallel processing and lightning compression
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
    """اكتشاف الرابط النهائي بعد التحويل الديناميكي"""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for attempt in range(max_retries):
        try:
            response = session.get(initial_url, timeout=8, allow_redirects=True)
            current_url = response.url
            
            if current_url != initial_url:
                return current_url
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # البحث عن meta refresh
            meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if meta_refresh and 'url=' in meta_refresh.get('content', ''):
                new_url = meta_refresh['content'].split('url=')[-1]
                if new_url:
                    return urljoin(initial_url, new_url)
            
            # البحث عن الرابط الأساسي
            canonical = soup.find('link', {'rel': 'canonical'})
            if canonical and canonical.get('href'):
                final_url = canonical['href']
                if final_url != initial_url:
                    return final_url
            
            time.sleep(1)
                
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2)
    
    return initial_url

def extract_video_embed_url(page_url):
    """استخراج رابط الفيديو من صفحة المشاهدة"""
    try:
        if '?do=watch' not in page_url:
            watch_url = page_url.rstrip('/') + '/?do=watch'
        else:
            watch_url = page_url
        
        response = requests.get(watch_url, headers=HEADERS, timeout=8)
        
        # الطريقة 1: البحث عن m3u8 مباشرة
        m3u8_pattern = r'(https?://[^\s"\']+\.m3u8[^\s"\']*)'
        m3u8_matches = re.findall(m3u8_pattern, response.text)
        for match in m3u8_matches:
            if 'cdn-vids.xyz' in match or 'm3u8' in match.lower():
                return match
        
        # الطريقة 2: البحث عن iframe
        soup = BeautifulSoup(response.text, 'html.parser')
        iframe_patterns = ['vidsp.net', 'player', 'embed', 'video']
        for pattern in iframe_patterns:
            iframe = soup.find('iframe', {'src': re.compile(pattern, re.I)})
            if iframe:
                iframe_src = iframe.get('src')
                if iframe_src:
                    if iframe_src.startswith('//'):
                        iframe_src = 'https:' + iframe_src
                    return iframe_src
        
        return None
        
    except Exception:
        return None

def download_with_lightning_compression(video_url, output_file):
    """
    تنزيل بسرعة البرق مع ضغط فوري
    """
    try:
        # استخدام yt-dlp للعثور على أفضل صيغة منخفضة الجودة
        cmd_find = [
            'yt-dlp',
            '-F',
            '--quiet',
            video_url
        ]
        
        result = subprocess.run(cmd_find, capture_output=True, text=True, timeout=30)
        
        # البحث عن الصيغة الأصغر (الأدنى جودة)
        format_id = None
        best_height = 9999
        
        for line in result.stdout.split('\n'):
            if 'x' in line and ('mp4' in line.lower() or 'm3u8' in line.lower() or 'webm' in line.lower()):
                # استخراج معلومات الارتفاع
                match = re.search(r'(\d{3,4})x\d{3,4}', line)
                if match:
                    height = int(match.group(1))
                    if height < best_height:
                        best_height = height
                        # الحصول على معرف الصيغة
                        parts = line.split()
                        if parts and parts[0].isdigit():
                            format_id = parts[0]
        
        if not format_id:
            format_id = 'worst'
        
        print(f"[*] تم اختيار الصيغة {format_id} (ارتفاع {best_height})")
        
        # الآن التنزيل المباشر مع الضغط الفوري
        cmd_download = [
            'yt-dlp',
            '-f', format_id,
            '--concurrent-fragments', '16',  # زيادة الأجزاء المتوازية
            '--limit-rate', '0',  # لا حدود للسرعة
            '--retries', '10',
            '--fragment-retries', '10',
            '--skip-unavailable-fragments',
            '--no-part',
            '--no-check-certificates',
            '--no-warnings',
            '--quiet',
            '--progress',
            '-o', '-',  # الإخراج إلى stdout
            video_url
        ]
        
        # إعدادات ffmpeg للضغط السريع جداً
        cmd_compress = [
            'ffmpeg',
            '-i', 'pipe:0',  # الإدخال من stdin
            '-vf', 'scale=-2:240',  # تغيير الحجم إلى 240p
            '-c:v', 'libx264',  # استخدام h.264
            '-preset', 'ultrafast',  # أسرع إعداد
            '-tune', 'fastdecode',  # تحسين للسرعة
            '-crf', '34',  # جودة أقل للسرعة (أعلى = أصغر حجم وأقل جودة)
            '-c:a', 'aac',  # الصوت
            '-b:a', '48k',  # معدل بت صوت منخفض
            '-ac', '1',  # صوت أحادي (أصغر)
            '-y',  # الكتابة فوق الملف
            '-threads', '0',  # استخدام كل الأنوية
            '-loglevel', 'error',  # تقليل السجلات
            output_file
        ]
        
        print(f"[*] بدء التنزيل والضغط الفوري...")
        start_time = time.time()
        
        # تشغيل yt-dlp وإرسال مخرجاته إلى ffmpeg
        process_ytdlp = subprocess.Popen(
            cmd_download,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8  # buffer كبير
        )
        
        process_ffmpeg = subprocess.Popen(
            cmd_compress,
            stdin=process_ytdlp.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # الانتظار حتى الانتهاء
        process_ytdlp.stdout.close()
        process_ytdlp.wait()
        process_ffmpeg.wait()
        
        elapsed = time.time() - start_time
        
        if process_ffmpeg.returncode == 0 and os.path.exists(output_file):
            size_mb = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] اكتمل في {elapsed:.1f} ثانية - الحجم: {size_mb:.1f} MB")
            return True
        else:
            print(f"[!] فشل التنزيل السريع")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"[!] انتهت مهلة التنزيل")
        return False
    except Exception as e:
        print(f"[!] خطأ في التنزيل: {e}")
        return False

def download_direct_without_reencode(video_url, output_file):
    """
    محاولة تنزيل مباشر بدون إعادة ترميز (أسرع)
    """
    try:
        # محاولة العثور على فيديو 240p جاهز
        cmd = [
            'yt-dlp',
            '-f', 'best[height<=240]',  # أفضل جودة لا تتعدى 240p
            '--merge-output-format', 'mp4',
            '--concurrent-fragments', '8',
            '--limit-rate', '0',
            '--retries', '5',
            '--no-part',
            '--quiet',
            '--progress',
            '-o', output_file.replace('.mp4', '.%(ext)s'),
            video_url
        ]
        
        print(f"[*] محاولة تنزيل 240p جاهز...")
        start_time = time.time()
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        
        if result.returncode == 0 and os.path.exists(output_file):
            elapsed = time.time() - start_time
            size_mb = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] تم تنزيل 240p جاهز في {elapsed:.1f} ثانية - الحجم: {size_mb:.1f} MB")
            return True
        else:
            # إذا لم نجد 240p جاهز، نبحث عن أدنى جودة
            cmd2 = [
                'yt-dlp',
                '-f', 'worst',  # أسوأ جودة
                '--merge-output-format', 'mp4',
                '--concurrent-fragments', '8',
                '--limit-rate', '0',
                '--quiet',
                '--progress',
                '-o', output_file,
                video_url
            ]
            
            print(f"[*] تنزيل أدنى جودة متاحة...")
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
            
            if result2.returncode == 0 and os.path.exists(output_file):
                elapsed = time.time() - start_time
                size_mb = os.path.getsize(output_file) / (1024*1024)
                print(f"[✓] تم التنزيل في {elapsed:.1f} ثانية - الحجم: {size_mb:.1f} MB")
                return True
        
        return False
        
    except Exception as e:
        print(f"[!] خطأ في التنزيل المباشر: {e}")
        return False

def process_episode_ultrafast(base_url, series_pattern, episode_num, download_dir):
    """
    معالجة حلقة واحدة بأقصى سرعة
    """
    episode_str = f"{episode_num:02d}"  # دائماً رقمين: 01, 02, ..., 10, 11, إلخ.
    print(f"\n[*] بدء معالجة الحلقة {episode_str}")
    
    try:
        # بناء الرابط مع التركيز على رقم الحلقة المكون من خانتين دائمًا
        # مثال: modablaj-terzi-episode-01, modablaj-terzi-episode-02, ..., modablaj-terzi-episode-10
        initial_url = f"{base_url}/{series_pattern}{episode_str}"
        
        print(f"[*] الرابط: {initial_url}")
        
        # الحصول على الرابط النهائي
        start_time = time.time()
        final_url = discover_final_url(initial_url)
        url_time = time.time() - start_time
        print(f"[*] اكتشاف الرابط في {url_time:.1f} ثانية")
        
        # استخراج رابط الفيديو
        video_url = extract_video_embed_url(final_url)
        if not video_url:
            print(f"[!] فشل في استخراج رابط الفيديو")
            return (episode_num, False, "فشل استخراج الرابط")
        
        # اسم ملف الإخراج
        output_file = f"{download_dir}/الحلقة_{episode_str}.mp4"
        
        # المحاولة الأولى: الضغط السريع جداً
        print(f"[*] بدء التنزيل والضغط الفوري...")
        compress_start = time.time()
        
        if download_with_lightning_compression(video_url, output_file):
            elapsed = time.time() - start_time
            compress_time = time.time() - compress_start
            
            if os.path.exists(output_file):
                size_mb = os.path.getsize(output_file) / (1024*1024)
                print(f"[✓] اكتملت الحلقة {episode_str} في {elapsed:.1f} ثانية")
                print(f"    الضغط: {compress_time:.1f} ثانية | الحجم: {size_mb:.1f} MB")
                return (episode_num, True, f"اكتمل في {elapsed:.1f} ثانية")
        
        # المحاولة الثانية: تنزيل مباشر بدون إعادة ترميز
        print(f"[*] تجربة التنزيل المباشر...")
        if download_direct_without_reencode(video_url, output_file):
            elapsed = time.time() - start_time
            return (episode_num, True, f"اكتمل في {elapsed:.1f} ثانية")
        
        return (episode_num, False, "فشل جميع المحاولات")
        
    except Exception as e:
        print(f"[!] خطأ في الحلقة {episode_str}: {e}")
        return (episode_num, False, str(e))

def main_parallel_ultrafast():
    """التنزيل المتوازي الرئيسي بأقصى سرعة"""
    print("="*60)
    print("تنزيل فيديو متوازي - جودة 240p - أقصى سرعة")
    print("="*60)
    
    # تثبيت المتطلبات
    install_requirements()
    
    # إدخال المستخدم
    print("\n[*] أدخل معاملات التنزيل:")
    
    base_url = input("الرابط الأساسي [https://x.3seq.com/video]: ").strip()
    if not base_url:
        base_url = "https://x.3seq.com/video"
    
    # طلب نمط المسلسل مع التأكد من أنه ينتهي بـ "-"
    default_pattern = "modablaj-terzi-episode-"
    series_pattern = input(f"نمط المسلسل [{default_pattern}]: ").strip()
    if not series_pattern:
        series_pattern = default_pattern
    
    # التأكد من أن النمط ينتهي بـ "-" لإضافة الأرقام
    if not series_pattern.endswith('-'):
        series_pattern += '-'
    
    # استخراج اسم المسلسل للمجلد (الجزء قبل أول "-episode-")
    series_name = series_pattern.split('-episode-')[0] if '-episode-' in series_pattern else series_pattern.rstrip('-')
    
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
        
        if start_ep > end_ep:
            print("[!] رقم الحلقة الأولى يجب أن يكون أصغر من الأخيرة")
            return
    except:
        print("[!] أرقام حلقات غير صالحة")
        return
    
    # عدد العمليات المتوازية
    workers_input = input(f"عدد التنزيلات المتوازية [1-{MAX_WORKERS}، الافتراضي: 3]: ").strip()
    try:
        parallel_workers = int(workers_input) if workers_input else MAX_WORKERS
        parallel_workers = min(max(1, parallel_workers), MAX_WORKERS)
    except:
        parallel_workers = MAX_WORKERS
    
    print(f"\n{'='*60}")
    print("[*] بدء التنزيل المتوازي")
    print(f"    المسلسل: {series_name}")
    print(f"    النمط: {series_pattern}XX")
    print(f"    الحلقات: من {start_ep:02d} إلى {end_ep:02d}")
    print(f"    الجودة: 240p فائق السرعة")
    print(f"    التنزيلات المتوازية: {parallel_workers}")
    print(f"    المجلد: {download_dir}/")
    print('='*60)
    
    # إعداد قائمة الحلقات
    episodes = list(range(start_ep, end_ep + 1))
    
    # تنزيل متوازي
    successful = 0
    failed = []
    results = []
    
    total_start_time = time.time()
    
    # استخدام ThreadPoolExecutor للتنزيل المتوازي
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_workers) as executor:
        # إنشاء قائمة المهام
        future_to_episode = {}
        
        for ep in episodes:
            future = executor.submit(
                process_episode_ultrafast,
                base_url,
                series_pattern,
                ep,
                download_dir
            )
            future_to_episode[future] = ep
        
        # معالجة النتائج عند اكتمالها
        for future in concurrent.futures.as_completed(future_to_episode):
            ep = future_to_episode[future]
            try:
                ep_num, success, message = future.result()
                if success:
                    successful += 1
                    print(f"[✓] الحلقة {ep_num:02d}: {message}")
                else:
                    failed.append(ep_num)
                    print(f"[!] الحلقة {ep_num:02d}: {message}")
                
                # تقرير تقدم
                completed = successful + len(failed)
                total = len(episodes)
                print(f"[*] التقدم: {completed}/{total} ({completed/total*100:.0f}%)")
                
            except Exception as e:
                failed.append(ep)
                print(f"[!] خطأ غير متوقع للحلقة {ep:02d}: {e}")
    
    # الملخص
    total_time = time.time() - total_start_time
    print(f"\n{'='*60}")
    print("[*] اكتمل التنزيل")
    print('='*60)
    
    if successful > 0:
        avg_time = total_time / successful
        print(f"[*] الوقت الإجمالي: {total_time:.1f} ثانية")
        print(f"[*] متوسط الوقت للحلقة: {avg_time:.1f} ثانية")
        print(f"[*] الحلقات الناجحة: {successful}/{len(episodes)}")
        
        # حساب الحجم الإجمالي
        total_size = 0
        mp4_files = []
        try:
            for f in os.listdir(download_dir):
                if f.endswith('.mp4'):
                    mp4_files.append(f)
                    size = os.path.getsize(f"{download_dir}/{f}") / (1024*1024)
                    total_size += size
            
            print(f"[*] الحجم الإجمالي: {total_size:.1f} MB")
            if successful > 0:
                avg_size = total_size / successful
                print(f"[*] متوسط الحجم للحلقة: {avg_size:.1f} MB")
        except:
            pass
    else:
        print(f"[!] لم يتم تنزيل أي حلقات")
    
    if failed:
        print(f"[!] الحلقات الفاشلة: {[f'{ep:02d}' for ep in failed]}")
        print(f"\n[*] للحلقات الفاشلة، حاول التنزيل يدوياً:")
        print(f"    yt-dlp -f worst 'رابط_الحلقة'")
    
    print('='*60)

def quick_download_single_fast():
    """تنزيل سريع لحلقة واحدة"""
    print("\n[*] تنزيل حلقة واحدة سريع")
    
    # خياران: إدخال رابط كامل أو بناء من مكونات
    print("\nخيارات الإدخال:")
    print("  1. إدخال رابط كامل")
    print("  2. بناء الرابط من مكونات")
    
    choice = input("\nاختر الخيار [1]: ").strip() or "1"
    
    if choice == "1":
        url = input("أدخل رابط الحلقة الكامل: ").strip()
        
        if not url.startswith('http'):
            print("[!] رابط غير صالح")
            return
        
        # استخراج اسم المسلسل
        match = re.search(r'/([^/]+)-episode-', url)
        series_name = match.group(1) if match else "episode"
        output_file = f"{series_name}_240p.mp4"
        
        final_url = discover_final_url(url)
        video_url = extract_video_embed_url(final_url)
        
    else:
        # بناء الرابط من مكونات
        base_url = input("الرابط الأساسي [https://x.3seq.com/video]: ").strip() or "https://x.3seq.com/video"
        series_pattern = input("نمط المسلسل (مثل: modablaj-terzi-episode-): ").strip()
        
        if not series_pattern.endswith('-'):
            series_pattern += '-'
        
        episode_num = input("رقم الحلقة (مثال: 01): ").strip()
        # إذا أدخل المستخدم 1، نحوله إلى 01
        if episode_num.isdigit():
            episode_num = f"{int(episode_num):02d}"
        
        series_name = series_pattern.split('-episode-')[0] if '-episode-' in series_pattern else series_pattern.rstrip('-')
        output_file = f"{series_name}_الحلقة_{episode_num}.mp4"
        
        initial_url = f"{base_url}/{series_pattern}{episode_num}"
        final_url = discover_final_url(initial_url)
        video_url = extract_video_embed_url(final_url)
    
    if not video_url:
        print("[!] فشل استخراج رابط الفيديو")
        return
    
    print(f"\n[*] التنزيل إلى: {output_file}")
    
    # التنزيل
    start_time = time.time()
    
    # المحاولة الأولى: الضغط السريع
    if download_with_lightning_compression(video_url, output_file):
        elapsed = time.time() - start_time
        size = os.path.getsize(output_file) / (1024*1024) if os.path.exists(output_file) else 0
        print(f"\n[✓] نجاح! الملف: {output_file}")
        print(f"    الوقت: {elapsed:.1f} ثانية | الحجم: {size:.1f} MB")
    else:
        # المحاولة الثانية: تنزيل مباشر
        print(f"\n[*] تجربة طريقة بديلة...")
        if download_direct_without_reencode(video_url, output_file):
            elapsed = time.time() - start_time
            size = os.path.getsize(output_file) / (1024*1024) if os.path.exists(output_file) else 0
            print(f"\n[✓] نجاح! الملف: {output_file}")
            print(f"    الوقت: {elapsed:.1f} ثانية | الحجم: {size:.1f} MB")
        else:
            print(f"\n[!] فشل التنزيل")

if __name__ == "__main__":
    print("="*60)
    print("تنزيل فيديو فائق السرعة - جودة 240p")
    print("="*60)
    
    print("\nالخيارات:")
    print("  1. تنزيل عدة حلقات (متوازي فائق السرعة)")
    print("  2. تنزيل حلقة واحدة سريع")
    print("  3. خروج")
    
    choice = input("\nاختر الخيار [1]: ").strip() or "1"
    
    if choice == "1":
        main_parallel_ultrafast()
    elif choice == "2":
        quick_download_single_fast()
    else:
        print("[*] مع السلامة!")
