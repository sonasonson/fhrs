#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import requests
import subprocess
import threading
from queue import Queue

# ================== CONFIG ==================
BASE_URL = "https://x.3seq.com/video"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://3seq.com/"
}
DEFAULT_PATTERN = "modablaj-terzi-episode-"
MAX_THREADS = 4
TIMEOUT = 1200
# ============================================


def get_episode_url(pattern, ep):
    ep = f"{ep:02d}"
    url = f"{BASE_URL}/{pattern}{ep}"
    try:
        r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=5)
        return r.url
    except:
        return url


def extract_m3u8(url):
    try:
        if "?do=watch" not in url:
            url += "/?do=watch"

        r = requests.get(url, headers=HEADERS, timeout=10)

        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', r.text)
        if iframe:
            iframe_url = iframe.group(1)
            if iframe_url.startswith("//"):
                iframe_url = "https:" + iframe_url

            r2 = requests.get(iframe_url, headers=HEADERS, timeout=10)
            m3u8 = re.search(r'https?://[^"\']+\.m3u8[^"\']*', r2.text)
            if m3u8:
                return m3u8.group(0)

        m3u8 = re.search(r'https?://[^"\']+\.m3u8[^"\']*', r.text)
        if m3u8:
            return m3u8.group(0)

    except:
        pass

    return None


# 🚀 تحميل + تحويل مباشر
def download_and_convert_240p(m3u8, output):
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-threads", "0",
            "-i", m3u8,

            "-vf", "scale=426:240:flags=fast_bilinear",

            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "35",

            "-c:a", "aac",
            "-b:a", "24k",
            "-ac", "1",
            "-ar", "22050",

            "-movflags", "+faststart",
            "-loglevel", "error",

            output
        ]

        start = time.time()
        subprocess.run(cmd, timeout=TIMEOUT, check=True)

        size = os.path.getsize(output) / (1024 * 1024)
        print(f"[✓] تم → {size:.1f}MB | {time.time()-start:.1f}s")
        return True

    except Exception as e:
        print(f"[✗] ffmpeg فشل: {e}")
        if os.path.exists(output):
            os.remove(output)
        return False


def worker(queue, results, pattern, folder):
    while not queue.empty():
        ep = queue.get()
        out = os.path.join(folder, f"EP_{ep:02d}.mp4")

        if os.path.exists(out):
            results.append((ep, True))
            queue.task_done()
            continue

        print(f"[*] EP {ep:02d} → استخراج الرابط")
        url = get_episode_url(pattern, ep)
        m3u8 = extract_m3u8(url)

        if not m3u8:
            results.append((ep, False))
            queue.task_done()
            continue

        print(f"[*] EP {ep:02d} → تحميل + تحويل 240p")
        ok = download_and_convert_240p(m3u8, out)
        results.append((ep, ok))

        queue.task_done()


def main():
    pattern = input(f"نمط المسلسل [{DEFAULT_PATTERN}]: ").strip() or DEFAULT_PATTERN
    if not pattern.endswith("-"):
        pattern += "-"

    folder = pattern.replace("-episode-", "").rstrip("-")
    os.makedirs(folder, exist_ok=True)

    start = int(input("الحلقة الأولى [1]: ") or 1)
    end = int(input("الحلقة الأخيرة [10]: ") or 10)
    if start > end:
        start, end = end, start

    q = Queue()
    results = []

    for ep in range(start, end + 1):
        q.put(ep)

    print("\n🚀 تحميل وتحويل مباشر إلى 240p\n")
    t0 = time.time()

    threads = []
    for _ in range(min(MAX_THREADS, end - start + 1)):
        t = threading.Thread(target=worker, args=(q, results, pattern, folder))
        t.start()
        threads.append(t)

    q.join()

    print("\n" + "=" * 40)
    ok = sum(1 for _, s in results if s)
    print(f"✔ تم {ok}/{len(results)}")
    print(f"⏱️ الوقت: {time.time()-t0:.1f} ثانية")
    print("=" * 40)


if __name__ == "__main__":
    main()
