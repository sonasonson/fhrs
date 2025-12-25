#!/usr/bin/env python3
"""
Video Downloader with Compression
Downloads videos and compresses them to reduce file size
"""

import os
import sys
import subprocess
import requests
from bs4 import BeautifulSoup
import re

def install_dependencies():
    """Install required tools"""
    print("[*] Installing required tools...")
    
    tools = ['yt-dlp', 'ffmpeg']
    for tool in tools:
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
            print(f"  ✓ {tool} is installed")
        except:
            print(f"  ✗ Installing {tool}...")
            if tool == 'ffmpeg':
                subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], check=True)
            elif tool == 'yt-dlp':
                subprocess.run(['sudo', 'pip3', 'install', 'yt-dlp'], check=True)

def get_video_url(episode_url):
    """Extract video URL from episode page"""
    try:
        response = requests.get(episode_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ابحث عن iframe
        iframe = soup.find('iframe', src=re.compile(r'vidsp\.net'))
        if iframe:
            return iframe['src']
        
        # ابحث عن روابط m3u8 مباشرة
        m3u8_matches = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', response.text)
        if m3u8_matches:
            return m3u8_matches[0]
            
        return None
    except:
        return None

def download_video(video_url, output_file):
    """Download video using yt-dlp"""
    print(f"[*] Downloading video...")
    
    # حاول أولاً بأقل جودة متاحة
    formats = [
        'worst',  # أقل جودة مطلقاً
        'best[height<=360]',
        'best[height<=480]',
        'best[height<=720]',
        'best'
    ]
    
    for fmt in formats:
        cmd = [
            'yt-dlp',
            '-f', fmt,
            '--merge-output-format', 'mp4',
            '-o', output_file,
            '--quiet',
            '--no-warnings',
            video_url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0 and os.path.exists(output_file):
                size_mb = os.path.getsize(output_file) / (1024*1024)
                print(f"[✓] Downloaded with {fmt}: {size_mb:.1f} MB")
                return True
        except:
            continue
    
    return False

def compress_video_advanced(input_file, output_file, target='small'):
    """
    Compress video with different presets
    target: 'small' (240p), 'medium' (360p), 'tiny' (144p)
    """
    presets = {
        'tiny': {
            'height': 144,
            'crf': 32,      # High compression
            'bitrate': '300k',
            'audiobitrate': '64k'
        },
        'small': {
            'height': 240,
            'crf': 28,      # Medium compression
            'bitrate': '500k',
            'audiobitrate': '96k'
        },
        'medium': {
            'height': 360,
            'crf': 26,      # Light compression
            'bitrate': '800k',
            'audiobitrate': '128k'
        }
    }
    
    preset = presets.get(target, presets['small'])
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-vf', f'scale=-2:{preset["height"]}',
        '-c:v', 'libx264',
        '-preset', 'slow',      # أفضل ضغط
        '-crf', str(preset['crf']),
        '-c:a', 'aac',
        '-b:a', preset['audiobitrate'],
        '-y',
        output_file
    ]
    
    print(f"[*] Compressing to {preset['height']}p (CRF: {preset['crf']})...")
    
    try:
        # إخفاء إخراج ffmpeg إلا إذا كان هناك خطأ
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            orig = os.path.getsize(input_file)
            new = os.path.getsize(output_file)
            reduction = (1 - new/orig) * 100
            
            print(f"[✓] Compression complete!")
            print(f"    Size: {orig/(1024*1024):.1f}MB → {new/(1024*1024):.1f}MB")
            print(f"    Reduction: {reduction:.1f}%")
            return True
        else:
            print(f"[!] Compression failed")
            return False
            
    except Exception as e:
        print(f"[!] Error: {e}")
        return False

def main():
    """Main function"""
    print("="*60)
    print("Video Downloader with Compression")
    print("="*60)
    
    # تثبيت الأدوات
    install_dependencies()
    
    # إدخال المستخدم
    base_url = input("Enter base URL [https://x.3seq.com/video]: ").strip()
    if not base_url:
        base_url = "https://x.3seq.com/video"
    
    series = input("Enter series name pattern [modablaj-the-protector-episode-s01e]: ").strip()
    if not series:
        series = "modablaj-the-protector-episode-s01e"
    
    try:
        start_ep = int(input("Start episode [1]: ").strip() or "1")
        end_ep = int(input("End episode [10]: ").strip() or "10")
    except:
        print("[!] Invalid episode numbers")
        return
    
    print("\nCompression presets:")
    print("  1. Tiny (144p, smallest size)")
    print("  2. Small (240p, good compression)")
    print("  3. Medium (360p, balanced)")
    
    preset_choice = input("Select preset [2]: ").strip() or "2"
    presets = {'1': 'tiny', '2': 'small', '3': 'medium'}
    preset = presets.get(preset_choice, 'small')
    
    # إنشاء مجلد التنزيل
    import time
    folder = f"videos_{time.strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(folder, exist_ok=True)
    
    print(f"\n[*] Starting download of episodes {start_ep}-{end_ep}")
    print(f"[*] Output folder: {folder}")
    print(f"[*] Compression: {preset}")
    print("="*60)
    
    successful = 0
    
    for ep in range(start_ep, end_ep + 1):
        print(f"\n[*] Episode {ep}")
        
        # رابط الحلقة
        ep_url = f"{base_url}/{series}{ep:02d}"
        
        # استخراج رابط الفيديو
        video_url = get_video_url(ep_url)
        if not video_url:
            print(f"[!] Could not find video URL for episode {ep}")
            continue
        
        print(f"[*] Video URL found")
        
        # تنزيل الفيديو
        temp_file = f"{folder}/ep{ep:02d}_temp.mp4"
        final_file = f"{folder}/الحلقة_{ep:02d}.mp4"
        
        if download_video(video_url, temp_file):
            # ضغط الفيديو
            if compress_video_advanced(temp_file, final_file, preset):
                # حذف الملف المؤقت
                os.remove(temp_file)
                successful += 1
                print(f"[✓] Episode {ep} completed")
            else:
                print(f"[!] Compression failed for episode {ep}")
        else:
            print(f"[!] Download failed for episode {ep}")
        
        # انتظار بين الحلقات
        if ep < end_ep:
            import time
            time.sleep(2)
    
    print("\n" + "="*60)
    print(f"[*] Download complete!")
    print(f"[*] Successful: {successful}/{end_ep - start_ep + 1}")
    print(f"[*] Files saved in: {folder}/")
    print("="*60)

if __name__ == "__main__":
    main()
