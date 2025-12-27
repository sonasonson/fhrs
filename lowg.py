#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import subprocess
import threading
from queue import Queue

BASE_URL = "https://x.3seq.com/video"
DEFAULT_PATTERN = "modablaj-terzi-episode-"
MAX_WORKERS = min(6, os.cpu_count() or 4)
TIMEOUT = 1800

def check_tools():
    for tool in ("ffmpeg", "yt-dlp"):
        try:
            subprocess.run([tool, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            print(f"[!] {tool} غير مثبت")
            sys.exit(1)

def episode_url(pattern, ep):
    return f"{BASE_URL}/{pattern}{ep:02d}"

def extract_m3u8(url):
    """استخراج m3u8 عبر yt-dlp (مضمون)"""
    try:
        cmd = [
            "yt-dlp",
            "-J",
            "--no-warnings",
            "--quiet",
            url
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        data = json.loads(p.stdout)

        for f in data.get("formats", []):
            if f.get("protocol") == "m3u8" and f.get("url"):
                return f["url"]
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

            url = episode_url(pattern, ep)
            m3u8 = extract_m3u8(url)

            if not m3u8:
                results.append((ep, False, "m3u8 غير موجود"))
                q.task_done()
                continue

            print(f"[*] EP {ep:02d} → تحميل 240p")
            ok = download_240p(m3u8, out)

            if ok and os.path.exists(out):
                size = os.path.getsize(out) / (1024 * 1024)
                results.append((ep, True, f"{size:.1f}MB"))
            else:
                results.append((ep, False, "فشل ffmpeg"))

        except Exception as e:
            results.append((ep, False, str(e)))

        q.task_done()

def main():
    check_tools()

    pattern = input(f"نمط المسلسل [{DEFAULT_PATTERN}]: ").strip() or DEFAULT_PATTERN
    if not pattern.endswith("-"):
        pattern += "-"

    name = pattern.replace("-episode-", "").rstrip("-")
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

    print("\n🚀 بدء التحميل الحقيقي (yt-dlp + ffmpeg)\n")
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

if __name__ == "__main__":
    main()
