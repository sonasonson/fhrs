#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ultra Fast Video Downloader for 3seq.com
KEEP ORIGINAL DOWNLOAD LOGIC
OPTIMIZED 240p COMPRESSION ONLY
"""

import os
import sys
import re
import time
import requests
import subprocess
import shutil
import threading
from queue import Queue

# ================= CONFIG =================
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
HEADERS = {"User-Agent": USER_AGENT, "Referer": "https://3seq.com/"}

BASE_URL = "https://x.3seq.com/video"
DEFAULT_PATTERN = "modablaj-terzi-episode-"

MAX_WORKERS = 5
DOWNLOAD_TIMEOUT = 300
COMPRESS_TIMEOUT = 900
# ========================================


def clean_directory(directory):
    if not os.path.exists(directory):
        return
    for f in os.listdir(directory):
        if f.endswith((".part", ".tmp", ".frag", ".m3u8")):
            try:
                os.remove(os.path.join(directory, f))
            except:
                pass


def get_final_episode_url_fast(base_url, series_pattern, episode_num):
    ep = f"{episode_num:02d}"
    url = f"{base_url}/{series_pattern}{ep}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5, allow_redirects=True)
        return r.url
    except:
        return url


def extract_m3u8_fast(episode_url):
    try:
        if "?do=watch" not in episode_url:
            episode_url += "/?do=watch"

        r = requests.get(episode_url, headers=HEADERS, timeout=10)

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


# ========== OPTIMIZED 240p COMPRESSION ==========
def fast_compress_to_240p(input_file):
    try:
        temp = input_file.replace(".mp4", "_240p.mp4")

        cmd = [
            "ffmpeg",
            "-y",
            "-threads", "0",
            "-i", input_file,

            "-vf", "scale=426:240:flags=fast_bilinear",

            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "fastdecode",
            "-crf", "36",

            "-c:a", "aac",
            "-b:a", "24k",
            "-ac", "1",
            "-ar", "22050",

            "-movflags", "+faststart",
            "-loglevel", "error",

            temp
        ]

        start = time.time()
        subprocess.run(cmd, timeout=COMPRESS_TIMEOUT, check=True)

        os.replace(temp, input_file)

        size = os.path.getsize(input_file) / (1024 * 1024)
        print(f"[✓] ضغط فائق السرعة → {size:.1f}MB ({time.time()-start:.1f}s)")
        return True

    except Exception as e:
        print(f"[!] فشل الضغط: {e}")
        if os.path.exists(temp):
            os.remove(temp)
        return False
# =================================================


def download_hls_ultrafast(m3u8_url, output_file):
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-threads", "0",
            "-i", m3u8_url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            "-loglevel", "error",
            output_file
        ]

        subprocess.run(cmd, timeout=DOWNLOAD_TIMEOUT, check=True)

        size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"[✓] تحميل تم → {size:.1f}MB")

        if size > 20:
            return fast_compress_to_240p(output_file)

        return True

    except Exception as e:
        print(f"[!] خطأ التحميل: {e}")
        return False


def worker(queue, results, pattern, folder):
    while not queue.empty():
        ep = queue.get()
        try:
            out = os.path.join(folder, f"EP_{ep:02d}.mp4")
            if os.path.exists(out):
                results.append((ep, True, "موجود"))
                queue.task_done()
                continue

            ep_url = get_final_episode_url_fast(BASE_URL, pattern, ep)
            m3u8 = extract_m3u8_fast(ep_url)

            if not m3u8:
                results.append((ep, False, "m3u8 غير موجود"))
                queue.task_done()
                continue

            print(f"[*] EP {ep:02d} → تحميل...")
            ok = download_hls_ultrafast(m3u8, out)

            if ok:
                results.append((ep, True, "تم"))
            else:
                results.append((ep, False, "فشل"))

        except Exception as e:
            results.append((ep, False, str(e)))

        queue.task_done()


def main():
    pattern = input(f"نمط المسلسل [{DEFAULT_PATTERN}]: ").strip() or DEFAULT_PATTERN
    if not pattern.endswith("-"):
        pattern += "-"

    folder = pattern.replace("-episode-", "").rstrip("-")
    os.makedirs(folder, exist_ok=True)
    clean_directory(folder)

    start = int(input("الحلقة الأولى [1]: ") or 1)
    end = int(input("الحلقة الأخيرة [10]: ") or 10)
    if start > end:
        start, end = end, start

    workers = min(MAX_WORKERS, end - start + 1)

    q = Queue()
    results = []

    for ep in range(start, end + 1):
        q.put(ep)

    print("\n🚀 بدء التحميل بنفس منطق السكربت الأصلي\n")
    t0 = time.time()

    threads = []
    for _ in range(workers):
        t = threading.Thread(target=worker, args=(q, results, pattern, folder))
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


if __name__ == "__main__":
    main()
