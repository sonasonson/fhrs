#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess
import threading
from queue import Queue

BASE_URL = "https://x.3seq.com/video"
DEFAULT_PATTERN = "modablaj-terzi-episode-"

MAX_WORKERS = min(4, os.cpu_count() or 2)
TIMEOUT = 1800

def check_tools():
    for tool in ("yt-dlp", "ffmpeg"):
        try:
            subprocess.run([tool, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            print(f"[!] {tool} غير مثبت")
            sys.exit(1)

def episode_watch_url(pattern, ep):
    return f"{BASE_URL}/{pattern}{ep:02d}/?do=watch"

def download_240p(url, output):
    """
    نترك yt-dlp يقوم بكل شيء:
    - استخراج
    - فك الحماية
    - اختيار أقل جودة
    """
    cmd = [
        "yt-dlp",
        "-f", "bv*[height<=240]/bv*+ba/b",
        "--merge-output-format", "mp4",
        "--no-part",
        "--no-warnings",
        "--retries", "5",
        "--fragment-retries", "5",
        "--concurrent-fragments", "8",
        "--downloader", "ffmpeg",
        "--downloader-args", "ffmpeg:-threads 0",
        "-o", output,
        url
    ]

    return subprocess.run(cmd, timeout=TIMEOUT).returncode == 0

def worker(q, results, pattern, folder):
    while not q.empty():
        ep = q.get()
        try:
            out = os.path.join(folder, f"EP_{ep:02d}.mp4")
            if os.path.exists(out):
                results.append((ep, True, "موجود"))
                q.task_done()
                continue

            url = episode_watch_url(pattern, ep)
            print(f"[*] EP {ep:02d} → تحميل مباشر 240p")

            ok = download_240p(url, out)

            if ok and os.path.exists(out):
                size = os.path.getsize(out) / (1024 * 1024)
                results.append((ep, True, f"{size:.1f}MB"))
            else:
                results.append((ep, False, "فشل yt-dlp"))

        except Exception as e:
            results.append((ep, False, str(e)))

        q.task_done()

def main():
    check_tools()

    pattern = input(f"نمط المسلسل [{DEFAULT_PATTERN}]: ").strip() or DEFAULT_PATTERN
    if not pattern.endswith("-"):
        pattern += "-"

    folder = pattern.replace("-episode-", "").rstrip("-")
    os.makedirs(folder, exist_ok=True)

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

    print("\n🚀 بدء التحميل (yt-dlp مباشر)\n")
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
