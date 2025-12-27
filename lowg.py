#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ULTRA FAST HLS DOWNLOADER & COMPRESSOR
Direct download + convert to 240p (ONE STEP)
Author: Optimized by ChatGPT
"""

import os
import re
import sys
import time
import subprocess
import threading
import requests
from queue import Queue

# ================== CONFIG ==================
BASE_URL = "https://x.3seq.com/video"
DEFAULT_PATTERN = "modablaj-terzi-episode-"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
HEADERS = {"User-Agent": USER_AGENT}

DOWNLOAD_TIMEOUT = 1200  # 20 دقيقة
MAX_WORKERS = min(8, os.cpu_count() or 4)

# ============================================

def ensure_tools():
    """تأكد من وجود ffmpeg"""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        print("[!] ffmpeg غير مثبت")
        sys.exit(1)

def clean_name(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name)

def get_episode_url(base, pattern, ep):
    return f"{base}/{pattern}{ep:02d}/?do=watch"

def extract_m3u8(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', r.text)
        if iframe:
            iframe_url = iframe.group(1)
            if iframe_url.startswith("//"):
                iframe_url = "https:" + iframe_url

            r2 = requests.get(iframe_url, headers=HEADERS, timeout=10)
            m3u8 = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', r2.text)
            if m3u8:
                return m3u8.group(0)

        m3u8 = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', r.text)
        if m3u8:
            return m3u8.group(0)

    except:
        pass
    return None

def download_240p(m3u8, output):
    cmd = [
        "ffmpeg",
        "-threads", "0",
        "-hwaccel", "auto",

        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "2",

        "-fflags", "+nobuffer",
        "-flags", "low_delay",
        "-analyzeduration", "0",
        "-probesize", "32",

        "-i", m3u8,

        "-vf", "scale=426:240:flags=fast_bilinear",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "36",
        "-pix_fmt", "yuv420p",

        "-c:a", "aac",
        "-b:a", "24k",
        "-ac", "1",
        "-ar", "22050",

        "-movflags", "+faststart",
        "-y",
        "-loglevel", "error",

        output
    ]

    return subprocess.run(cmd, timeout=DOWNLOAD_TIMEOUT).returncode == 0

def worker(queue, results, pattern, folder):
    while not queue.empty():
        ep = queue.get()
        try:
            filename = os.path.join(folder, f"EP_{ep:02d}.mp4")
            if os.path.exists(filename):
                results.append((ep, True, "موجود"))
                queue.task_done()
                continue

            url = get_episode_url(BASE_URL, pattern, ep)
            m3u8 = extract_m3u8(url)

            if not m3u8:
                results.append((ep, False, "فشل استخراج الرابط"))
                queue.task_done()
                continue

            print(f"[*] EP {ep:02d} → تحميل 240p ...")
            ok = download_240p(m3u8, filename)

            if ok and os.path.exists(filename):
                size = os.path.getsize(filename) / (1024 * 1024)
                results.append((ep, True, f"{size:.1f}MB"))
            else:
                results.append((ep, False, "فشل التحميل"))

        except Exception as e:
            results.append((ep, False, str(e)))

        queue.task_done()

def main():
    ensure_tools()

    pattern = input(f"نمط المسلسل [{DEFAULT_PATTERN}]: ").strip() or DEFAULT_PATTERN
    if not pattern.endswith("-"):
        pattern += "-"

    name = clean_name(pattern.replace("-episode-", "").rstrip("-"))
    os.makedirs(name, exist_ok=True)

    start = int(input("الحلقة الأولى [1]: ") or 1)
    end = int(input("الحلقة الأخيرة [10]: ") or 10)
    if start > end:
        start, end = end, start

    workers = int(input(f"عدد التحميلات المتوازية [{MAX_WORKERS}]: ") or MAX_WORKERS)
    workers = min(workers, MAX_WORKERS)

    q = Queue()
    results = []

    for ep in range(start, end + 1):
        q.put(ep)

    print("\n🚀 بدء التحميل السريع إلى 240p ...\n")
    t0 = time.time()

    threads = []
    for _ in range(workers):
        t = threading.Thread(target=worker, args=(q, results, pattern, name))
        t.start()
        threads.append(t)

    q.join()
    for t in threads:
        t.join()

    print("\n" + "=" * 50)
    ok = 0
    for ep, success, msg in sorted(results):
        if success:
            ok += 1
            print(f"[✓] EP {ep:02d} → {msg}")
        else:
            print(f"[✗] EP {ep:02d} → {msg}")

    print("=" * 50)
    print(f"✔ تم تحميل {ok}/{len(results)}")
    print(f"⏱️ الوقت: {time.time() - t0:.1f} ثانية")
    print("🔥 الجودة: 240p | الحجم صغير | أسرع أداء")

if __name__ == "__main__":
    main()
