#!/usr/bin/env python3
"""
ULTRA FAST 240p Video Downloader for 3seq.com
Maximum speed with direct 240p download or GPU acceleration
"""

import os
import sys
import re
import time
import requests
import subprocess
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# ===== CONFIGURATION =====
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
HEADERS = {'User-Agent': USER_AGENT}

def check_gpu_acceleration():
    """Check if GPU acceleration is available"""
    gpu_types = [
        ('nvidia', ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader']),
        ('amd', ['rocminfo']),
        ('intel', ['intel_gpu_top', '--version']),
    ]
    
    for gpu_type, cmd in gpu_types:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[✓] {gpu_type.upper()} GPU detected")
                return gpu_type
        except:
            continue
    
    print("[*] No GPU detected, using CPU acceleration")
    return None

def install_requirements():
    """Install required packages quickly"""
    print("[*] Quick system check...")
    
    # Check yt-dlp (most important)
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        print(f"  ✓ yt-dlp {result.stdout.strip()}")
    except:
        print("  ✗ Installing yt-dlp...")
        subprocess.run(['pip', 'install', '--upgrade', 'yt-dlp'], check=True)
    
    # Check ffmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("  ✓ ffmpeg")
    except:
        print("  ✗ Installing ffmpeg...")
        subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], check=True)

def get_final_url_fast(initial_url):
    """Fast URL discovery with minimal delays"""
    print(f"[*] Getting final URL...")
    
    try:
        response = requests.get(initial_url, headers=HEADERS, timeout=5, allow_redirects=True)
        final_url = response.url
        
        if final_url != initial_url:
            print(f"[*] Redirected to: {final_url}")
            return final_url
        
        # Quick check for meta refresh
        if 'refresh' in response.text.lower():
            soup = BeautifulSoup(response.text, 'html.parser')
            meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if meta_refresh and 'url=' in meta_refresh.get('content', ''):
                new_url = meta_refresh['content'].split('url=')[-1]
                return urljoin(initial_url, new_url)
        
        return final_url
        
    except Exception as e:
        print(f"[!] URL error: {e}")
        return initial_url

def extract_video_url_fast(page_url):
    """Fast video URL extraction"""
    print(f"[*] Extracting video URL...")
    
    try:
        # Add watch parameter
        if not page_url.endswith('/'):
            page_url += '/'
        watch_url = page_url + '?do=watch'
        
        response = requests.get(watch_url, headers=HEADERS, timeout=5)
        
        # Quick regex search for iframe or m3u8
        patterns = [
            r'src="(https?://v\.vidsp\.net/embed-[^"]+)"',
            r'src="(https?://v\.vidsp\.net/[^"]+\.html)"',
            r'(https?://[^"\']+\.m3u8[^"\']*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                video_url = match.group(1)
                print(f"[*] Found: {video_url[:60]}...")
                return video_url
        
        return None
        
    except Exception as e:
        print(f"[!] Extraction error: {e}")
        return None

def download_ultrafast(video_url, output_file, use_gpu=False):
    """
    Ultra fast download with multiple speed optimization techniques
    """
    print(f"[*] ULTRA FAST download to: {output_file}")
    
    # Speed optimization parameters
    speed_params = [
        '--concurrent-fragments', '8',  # More parallel fragments
        '--limit-rate', '10M',  # Higher rate limit
        '--retries', '3',  # Fewer retries
        '--fragment-retries', '3',
        '--socket-timeout', '5',
        '--extractor-retries', '1',
        '--no-part',
        '--no-mtime',
        '--downloader', 'aria2c',  # Use aria2c if available
        '--downloader-args', 'aria2c:-x 16 -k 10M -s 16',  # aria2c optimizations
    ]
    
    # Try to download 240p directly first
    print("[*] Trying direct 240p download...")
    
    # First attempt: Direct 240p with worst quality selection
    cmd_240p = [
        'yt-dlp',
        '-f', 'worst[height<=240]/worst',  # Prefer <=240p, fallback to worst
        '--merge-output-format', 'mp4',
        *speed_params,
        '-o', output_file,
        '--quiet',
        video_url
    ]
    
    # Second attempt: If no 240p, download worst and convert with GPU if available
    gpu_encoder = None
    if use_gpu:
        gpu_type = check_gpu_acceleration()
        if gpu_type == 'nvidia':
            gpu_encoder = 'h264_nvenc'
        elif gpu_type == 'amd':
            gpu_encoder = 'h264_amf'
        elif gpu_type == 'intel':
            gpu_encoder = 'h264_qsv'
    
    try:
        # Attempt 1: Direct 240p
        print("[*] Attempt 1: Direct 240p download")
        result = subprocess.run(cmd_240p, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(output_file):
            size = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] Direct 240p success: {size:.1f} MB")
            return True
        
        # Attempt 2: Download and fast convert
        print("[*] Attempt 2: Fast download + convert")
        temp_file = output_file + '.temp.mp4'
        
        # Download worst quality fastest
        cmd_download = [
            'yt-dlp',
            '-f', 'worst',
            '--merge-output-format', 'mp4',
            *speed_params,
            '-o', temp_file,
            '--quiet',
            video_url
        ]
        
        # Convert with maximum speed
        if gpu_encoder:
            # GPU acceleration
            cmd_convert = [
                'ffmpeg',
                '-i', temp_file,
                '-vf', 'scale=-2:240',
                '-c:v', gpu_encoder,
                '-preset', 'fast',  # Fastest GPU preset
                '-b:v', '500k',
                '-c:a', 'aac',
                '-b:a', '64k',
                '-y',
                output_file
            ]
            print(f"[*] Using GPU acceleration: {gpu_encoder}")
        else:
            # CPU with ultrafast settings
            cmd_convert = [
                'ffmpeg',
                '-i', temp_file,
                '-vf', 'scale=-2:240',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',  # Fastest CPU preset
                '-tune', 'zerolatency',
                '-crf', '30',  # Slightly worse quality for speed
                '-c:a', 'aac',
                '-b:a', '64k',
                '-threads', str(os.cpu_count() or 4),  # Use all CPU cores
                '-y',
                output_file
            ]
            print("[*] Using CPU ultrafast preset")
        
        # Download
        print("[*] Downloading source...")
        dl_result = subprocess.run(cmd_download, capture_output=True, text=True, timeout=300)
        
        if dl_result.returncode != 0 or not os.path.exists(temp_file):
            print("[!] Download failed")
            return False
        
        # Convert
        print("[*] Converting to 240p...")
        conv_result = subprocess.run(cmd_convert, capture_output=True, text=True, timeout=300)
        
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        if conv_result.returncode == 0 and os.path.exists(output_file):
            size = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] Convert success: {size:.1f} MB")
            return True
        
        return False
        
    except subprocess.TimeoutExpired:
        print("[!] Timeout - operation took too long")
        return False
    except Exception as e:
        print(f"[!] Error: {e}")
        return False

def process_episode_ultrafast(base_url, series_pattern, episode_num, download_dir, use_gpu=False):
    """Ultra fast episode processing"""
    print(f"\n[*] EPISODE {episode_num:02d} - ULTRA FAST")
    
    start_time = time.time()
    
    try:
        # Build URL
        episode_str = f"{episode_num:02d}"
        if 's01e' in series_pattern:
            initial_url = f"{base_url}/{series_pattern}{episode_str}"
        else:
            initial_url = f"{base_url}/{series_pattern}{episode_num}"
        
        # Fast URL discovery
        final_url = get_final_url_fast(initial_url)
        
        # Fast video extraction
        video_url = extract_video_url_fast(final_url)
        if not video_url:
            print(f"[!] No video URL found")
            return False
        
        # Output file
        output_file = f"{download_dir}/E{episode_str}.mp4"
        
        # Ultra fast download
        success = download_ultrafast(video_url, output_file, use_gpu)
        
        elapsed = time.time() - start_time
        if success:
            size = os.path.getsize(output_file) / (1024*1024) if os.path.exists(output_file) else 0
            print(f"[✓] Completed in {elapsed:.1f}s, Size: {size:.1f}MB")
        else:
            print(f"[!] Failed in {elapsed:.1f}s")
        
        return success
        
    except Exception as e:
        print(f"[!] Processing error: {e}")
        return False

def main_ultrafast():
    """Main ultra fast downloader"""
    print("="*60)
    print("ULTRA FAST 240p VIDEO DOWNLOADER")
    print("Maximum speed optimization")
    print("="*60)
    
    # Quick install check
    install_requirements()
    
    # Check for GPU
    use_gpu = False
    gpu_choice = input("\n[*] Enable GPU acceleration if available? (y/n) [y]: ").strip().lower()
    if gpu_choice != 'n':
        use_gpu = True
    
    # Get parameters
    print("\n[*] Fast configuration:")
    base_url = "https://x.3seq.com/video"
    print(f"    Base URL: {base_url} (fixed)")
    
    series = "modablaj-sarmasik-zamani-episode-"
    series_input = input(f"    Series pattern [{series}]: ").strip()
    if series_input:
        series = series_input
    
    start_ep = 1
    end_ep = 10
    try:
        ep_range = input("    Episodes (e.g., 1-10) [1-10]: ").strip()
        if ep_range and '-' in ep_range:
            start_ep, end_ep = map(int, ep_range.split('-'))
    except:
        pass
    
    # Create output directory
    timestamp = time.strftime("%H%M%S")
    download_dir = f"FAST_{timestamp}"
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print("[*] ULTRA FAST DOWNLOAD STARTING")
    print(f"    Series: {series}")
    print(f"    Episodes: {start_ep}-{end_ep}")
    print(f"    GPU Acceleration: {'YES' if use_gpu else 'NO'}")
    print(f"    Output: {download_dir}/")
    print('='*60)
    
    # Process episodes
    successful = 0
    total_start = time.time()
    
    for ep in range(start_ep, end_ep + 1):
        if process_episode_ultrafast(base_url, series, ep, download_dir, use_gpu):
            successful += 1
    
    # Summary
    total_time = time.time() - total_start
    print(f"\n{'='*60}")
    print("[*] DOWNLOAD COMPLETE")
    print('='*60)
    print(f"[*] Successful: {successful}/{end_ep - start_ep + 1}")
    print(f"[*] Total time: {total_time:.1f} seconds")
    print(f"[*] Average time per episode: {total_time/max(successful,1):.1f} seconds")
    
    # File summary
    if successful > 0:
        total_size = 0
        for file in os.listdir(download_dir):
            if file.endswith('.mp4'):
                total_size += os.path.getsize(f"{download_dir}/{file}")
        total_size_mb = total_size / (1024*1024)
        print(f"[*] Total size: {total_size_mb:.1f} MB")
        print(f"[*] Average size: {total_size_mb/successful:.1f} MB")
    
    print(f"\n[*] Files saved in: {download_dir}/")
    print('='*60)

def direct_command_mode():
    """Generate direct commands for maximum speed"""
    print("\n[*] DIRECT COMMAND MODE - MAXIMUM SPEED")
    print("[*] Copy and paste these commands in terminal:")
    
    base_url = "https://x.3seq.com/video"
    series = "modablaj-sarmasik-zamani-episode-"
    
    print(f"\n1. For SINGLE episode (fastest):")
    print(f"   yt-dlp -f worst[height<=240]/worst --concurrent-fragments 8 \\")
    print(f"     --limit-rate 20M --downloader aria2c '{base_url}/{series}1'")
    
    print(f"\n2. For MULTIPLE episodes (parallel):")
    print(f"   for i in {{1..10}}; do")
    print(f"     yt-dlp -f worst[height<=240]/worst --concurrent-fragments 8 \\")
    print(f"       --limit-rate 20M '{base_url}/{series}$i' &")
    print(f"   done")
    print(f"   wait")
    
    print(f"\n3. With GPU acceleration (if available):")
    print(f"   yt-dlp -f worst '{base_url}/{series}1' -o temp.mp4 && \\")
    print(f"   ffmpeg -i temp.mp4 -vf scale=-2:240 -c:v h264_nvenc \\")
    print(f"     -preset fast -b:v 500k -c:a aac -b:a 64k output_240p.mp4")
    
    print(f"\n[*] Replace '1' with episode number as needed")

if __name__ == "__main__":
    print("="*60)
    print("ULTRA FAST DOWNLOADER - Choose Mode")
    print("="*60)
    print("\n1. Automated ultra fast download")
    print("2. Direct command mode (maximum speed)")
    print("3. Exit")
    
    choice = input("\nSelect [1]: ").strip() or "1"
    
    if choice == "1":
        main_ultrafast()
    elif choice == "2":
        direct_command_mode()
    else:
        print("[*] Goodbye!")
