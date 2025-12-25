#!/usr/bin/env python3
"""
Complete Video Downloader for 3seq.com
Handles dynamic URLs, quality selection (240p/480p), and compression
"""

import os
import sys
import re
import time
import json
import requests
import subprocess
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# ===== CONFIGURATION =====
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
HEADERS = {'User-Agent': USER_AGENT}

# ===== UTILITY FUNCTIONS =====
def install_requirements():
    """Install required packages"""
    print("[*] Checking system requirements...")
    
    # Check Python packages
    packages = ['requests', 'beautifulsoup4']
    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ✗ Installing {pkg}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
    
    # Check yt-dlp
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("  ✓ yt-dlp")
    except:
        print("  ✗ Installing yt-dlp...")
        subprocess.run(['pip', 'install', 'yt-dlp'], check=True)
    
    # Check ffmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("  ✓ ffmpeg")
    except:
        print("  ✗ Installing ffmpeg...")
        subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], check=True)

def clean_filename(name):
    """Clean filename from special characters"""
    # Remove special characters but keep Arabic
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    return cleaned.strip()

# ===== URL DISCOVERY FUNCTIONS =====
def discover_final_url(initial_url, max_retries=5):
    """
    Discover the final URL after dynamic transformation
    Example: /video/modablaj-the-protector-episode-s01e01 
      -> /video/modablaj-the-protector-episode-s01e01-cksi
    """
    print(f"[*] Discovering final URL for: {initial_url}")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for attempt in range(max_retries):
        try:
            # First request (may redirect or have meta refresh)
            response = session.get(initial_url, timeout=10, allow_redirects=True)
            current_url = response.url
            
            # Check if URL already changed
            if current_url != initial_url:
                print(f"[*] Redirected to: {current_url}")
                initial_url = current_url
            
            # Parse HTML for clues
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for meta refresh
            meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if meta_refresh and 'url=' in meta_refresh.get('content', ''):
                new_url = meta_refresh['content'].split('url=')[-1]
                if new_url:
                    final_url = urljoin(initial_url, new_url)
                    print(f"[*] Meta refresh to: {final_url}")
                    return final_url
            
            # Look for canonical URL or alternative links
            canonical = soup.find('link', {'rel': 'canonical'})
            if canonical and canonical.get('href'):
                final_url = canonical['href']
                if final_url != initial_url:
                    print(f"[*] Canonical URL: {final_url}")
                    return final_url
            
            # Check for og:url
            og_url = soup.find('meta', {'property': 'og:url'})
            if og_url and og_url.get('content'):
                final_url = og_url['content']
                if final_url != initial_url:
                    print(f"[*] OpenGraph URL: {final_url}")
                    return final_url
            
            # Try to find episode links in the page
            episode_links = soup.find_all('a', href=re.compile(r'episode-s\d+e\d+'))
            for link in episode_links:
                href = link.get('href')
                if href and href != initial_url:
                    final_url = urljoin(initial_url, href)
                    print(f"[*] Found episode link: {final_url}")
                    return final_url
            
            # If still same URL, check if it's already the final format
            if re.search(r'episode-s\d+e\d+-[a-z0-9]+/?$', initial_url):
                print(f"[*] Already in final format: {initial_url}")
                return initial_url
            
            # Wait and retry
            if attempt < max_retries - 1:
                print(f"[*] Waiting for dynamic content... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
                
        except Exception as e:
            print(f"[!] Error discovering URL: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    
    print(f"[!] Could not discover final URL, using original")
    return initial_url

def extract_video_embed_url(page_url):
    """Extract video embed URL from watch page"""
    print(f"[*] Extracting video from: {page_url}")
    
    try:
        # Add ?do=watch if not present
        if '?do=watch' not in page_url:
            if not page_url.endswith('/'):
                page_url += '/'
            watch_url = page_url + '?do=watch'
        else:
            watch_url = page_url
        
        response = requests.get(watch_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        # Save for debugging if needed
        # with open(f'debug_page_{int(time.time())}.html', 'w', encoding='utf-8') as f:
        #     f.write(response.text)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Method 1: Direct m3u8 in page
        m3u8_pattern = r'(https?://[^\s"\']+\.m3u8[^\s"\']*)'
        m3u8_matches = re.findall(m3u8_pattern, response.text)
        for match in m3u8_matches:
            if 'cdn-vids.xyz' in match or 'm3u8' in match.lower():
                print(f"[*] Found direct m3u8: {match}")
                return match
        
        # Method 2: Iframe src
        iframe = soup.find('iframe', {'src': re.compile(r'vidsp\.net|embed')})
        if iframe:
            iframe_src = iframe.get('src')
            if iframe_src:
                print(f"[*] Found iframe: {iframe_src}")
                return iframe_src
        
        # Method 3: JavaScript variables
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                # Look for JW Player or similar
                patterns = [
                    r'file["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'sources?\s*:\s*\[[^\]]*["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'embed-([a-z0-9]+)\.html'
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, script.string, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            if 'embed-' in match:
                                return f"https://v.vidsp.net/{match}" if not match.startswith('http') else match
                            elif 'm3u8' in match:
                                return match
        
        # Method 4: Try to find video server URL
        server_links = soup.find_all('a', {'class': re.compile(r'server|watch')})
        for link in server_links:
            href = link.get('href')
            if href and ('vidsp.net' in href or 'embed' in href):
                full_url = urljoin(watch_url, href)
                print(f"[*] Found server link: {full_url}")
                return full_url
        
        print("[!] Could not extract video URL")
        return None
        
    except Exception as e:
        print(f"[!] Error extracting video: {e}")
        return None

def get_m3u8_from_embed(embed_url):
    """Get m3u8 URL from embed page"""
    print(f"[*] Getting m3u8 from embed: {embed_url}")
    
    try:
        response = requests.get(embed_url, headers=HEADERS, timeout=15)
        
        # Look for m3u8 in embed page
        patterns = [
            r'src["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response.text)
            for match in matches:
                if 'm3u8' in match and 'cdn-vids.xyz' in match:
                    print(f"[*] Found m3u8 in embed: {match}")
                    return match
        
        # If not found, return embed URL for yt-dlp to handle
        print("[*] No direct m3u8 found, using embed URL")
        return embed_url
        
    except Exception as e:
        print(f"[!] Error processing embed: {e}")
        return embed_url

# ===== DOWNLOAD FUNCTIONS =====
def download_with_ytdlp(video_url, output_file, quality='240p'):
    """Download video using yt-dlp with specified quality"""
    
    # Map quality to yt-dlp format selector
    quality_map = {
        '144p': 'worstvideo[height<=144]+worstaudio/worst[height<=144]',
        '240p': 'worstvideo[height<=240]+worstaudio/worst[height<=240]',
        '360p': 'worstvideo[height<=360]+worstaudio/worst[height<=360]',
        '480p': 'worstvideo[height<=480]+worstaudio/worst[height<=480]',
        '720p': 'worstvideo[height<=720]+worstaudio/worst[height<=720]',
        'best': 'best'
    }
    
    format_selector = quality_map.get(quality, 'worstvideo[height<=240]+worstaudio/worst[height<=240]')
    
    print(f"[*] Downloading with quality: {quality}")
    print(f"[*] Output: {output_file}")
    
    # Build command
    cmd = [
        'yt-dlp',
        '-f', format_selector,
        '--merge-output-format', 'mp4',
        '--no-part',
        '--concurrent-fragments', '4',
        '--limit-rate', '2M',
        '--retries', '10',
        '--fragment-retries', '10',
        '--skip-unavailable-fragments',
        '--quiet',
        '--no-warnings',
        '-o', output_file,
        video_url
    ]
    
    try:
        # Run yt-dlp
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Monitor progress
        last_progress = ""
        for line in process.stdout:
            if '[download]' in line:
                if 'ETA' in line or '%' in line:
                    progress = line.strip()
                    if progress != last_progress:
                        print(f"    {progress}", end='\r')
                        last_progress = progress
        
        process.wait()
        
        if process.returncode == 0:
            if os.path.exists(output_file):
                size_mb = os.path.getsize(output_file) / (1024*1024)
                print(f"\n[✓] Download complete: {size_mb:.1f} MB")
                return True
            else:
                print("\n[!] Download completed but file not found")
                return False
        else:
            print(f"\n[!] yt-dlp failed with code: {process.returncode}")
            return False
            
    except Exception as e:
        print(f"\n[!] Download error: {e}")
        return False

def compress_to_240p(input_file, output_file):
    """Compress video to 240p using ffmpeg"""
    if not os.path.exists(input_file):
        return False
    
    print(f"[*] Compressing to 240p: {input_file}")
    
    # Get original duration for progress
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
               '-of', 'default=noprint_wrappers=1:nokey=1', input_file]
        duration = float(subprocess.check_output(cmd).decode().strip())
    except:
        duration = 0
    
    # Compression command
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-vf', 'scale=-2:240',
        '-c:v', 'libx264',
        '-preset', 'slow',        # Better compression
        '-crf', '30',             # Higher CRF = smaller file (18-28 is normal, 30-32 is high compression)
        '-c:a', 'aac',
        '-b:a', '64k',            # Lower audio bitrate
        '-ac', '2',               # Stereo
        '-ar', '44100',           # Audio sample rate
        '-movflags', '+faststart',
        '-y',                     # Overwrite output
        output_file
    ]
    
    try:
        print(f"[*] Running ffmpeg compression...")
        if duration > 0:
            print(f"[*] Original duration: {duration:.1f} seconds")
        
        # Run with progress
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Parse ffmpeg output for progress
        for line in process.stderr:
            if 'time=' in line and 'bitrate=' in line:
                # Extract time
                time_match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line)
                if time_match and duration > 0:
                    # Convert time to seconds
                    t = time_match.group(1)
                    h, m, s = t.split(':')
                    seconds = int(h)*3600 + int(m)*60 + float(s)
                    percent = (seconds / duration) * 100
                    print(f"    Progress: {percent:.1f}%", end='\r')
        
        process.wait()
        
        if process.returncode == 0:
            if os.path.exists(output_file):
                orig_size = os.path.getsize(input_file) / (1024*1024)
                new_size = os.path.getsize(output_file) / (1024*1024)
                
                print(f"\n[✓] Compression successful!")
                print(f"    Size: {orig_size:.1f}MB → {new_size:.1f}MB")
                print(f"    Reduction: {((orig_size - new_size)/orig_size*100):.1f}%")
                return True
        else:
            print(f"\n[!] Compression failed")
            return False
            
    except Exception as e:
        print(f"\n[!] Compression error: {e}")
        return False

# ===== MAIN PROCESS =====
def process_episode(base_url, series_pattern, episode_num, quality, download_dir, compress=False):
    """Process a single episode"""
    print(f"\n{'='*60}")
    print(f"[*] EPISODE {episode_num:02d}")
    print('='*60)
    
    try:
        # Step 1: Build initial URL
        episode_str = f"{episode_num:02d}"
        initial_url = f"{base_url}/{series_pattern}{episode_str}"
        print(f"[*] Initial URL: {initial_url}")
        
        # Step 2: Discover final URL
        final_url = discover_final_url(initial_url)
        print(f"[*] Final URL: {final_url}")
        
        # Step 3: Extract video embed URL
        embed_url = extract_video_embed_url(final_url)
        if not embed_url:
            print(f"[!] Failed to extract video URL")
            return False
        
        # Step 4: Get m3u8 URL
        video_url = get_m3u8_from_embed(embed_url)
        if not video_url:
            print(f"[!] Failed to get video stream URL")
            return False
        
        print(f"[*] Video stream: {video_url[:80]}...")
        
        # Step 5: Download
        temp_file = f"{download_dir}/temp_ep{episode_str}.mp4"
        final_file = f"{download_dir}/الحلقة_{episode_str}.mp4"
        
        # Remove temp file if exists
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Download with desired quality
        if quality == '240p':
            # Try to download 240p directly
            if download_with_ytdlp(video_url, temp_file, '240p'):
                # Rename to final
                os.rename(temp_file, final_file)
                print(f"[✓] Episode {episode_num} downloaded at 240p")
                return True
            else:
                # Fallback: download lowest quality then compress
                print(f"[*] 240p not available, downloading lowest quality...")
                if download_with_ytdlp(video_url, temp_file, 'worst'):
                    if compress_to_240p(temp_file, final_file):
                        os.remove(temp_file)
                        print(f"[✓] Episode {episode_num} compressed to 240p")
                        return True
        else:
            # Download at requested quality
            if download_with_ytdlp(video_url, final_file, quality):
                print(f"[✓] Episode {episode_num} downloaded at {quality}")
                return True
        
        print(f"[!] All download attempts failed for episode {episode_num}")
        return False
        
    except Exception as e:
        print(f"[!] Error processing episode {episode_num}: {e}")
        return False

def main():
    """Main function"""
    print("="*60)
    print("3SEQ VIDEO DOWNLOADER - Complete Solution")
    print("="*60)
    
    # Install requirements
    install_requirements()
    
    # Get user input
    print("\n[*] Enter download parameters:")
    base_url = input("Base URL [https://x.3seq.com/video]: ").strip()
    if not base_url:
        base_url = "https://x.3seq.com/video"
    
    series = input("Series pattern [modablaj-the-protector-episode-s01e]: ").strip()
    if not series:
        series = "modablaj-the-protector-episode-s01e"
    
    try:
        start_ep = int(input("Start episode [1]: ").strip() or "1")
        end_ep = int(input("End episode [10]: ").strip() or "10")
    except:
        print("[!] Invalid episode numbers")
        return
    
    print("\n[*] Quality options:")
    print("    1. 240p (Smallest size, may compress if needed)")
    print("    2. 480p (Standard quality)")
    print("    3. 720p (HD)")
    print("    4. Best available")
    
    quality_choice = input("Select quality [1]: ").strip()
    qualities = {'1': '240p', '2': '480p', '3': '720p', '4': 'best'}
    quality = qualities.get(quality_choice, '240p')
    
    # Create download directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    download_dir = f"المحافظ_S01_{timestamp}"
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print("[*] STARTING DOWNLOAD")
    print(f"    Series: {series}")
    print(f"    Episodes: {start_ep} to {end_ep}")
    print(f"    Quality: {quality}")
    print(f"    Output: {download_dir}/")
    print('='*60)
    
    # Process episodes
    successful = 0
    failed = []
    
    for ep in range(start_ep, end_ep + 1):
        if process_episode(base_url, series, ep, quality, download_dir, compress=True):
            successful += 1
        else:
            failed.append(ep)
        
        # Delay between episodes
        if ep < end_ep:
            print(f"[*] Waiting 5 seconds...")
            time.sleep(5)
    
    # Summary
    print(f"\n{'='*60}")
    print("[*] DOWNLOAD COMPLETE")
    print('='*60)
    print(f"[*] Successful: {successful}/{end_ep - start_ep + 1}")
    if failed:
        print(f"[!] Failed episodes: {failed}")
    
    # Show file sizes
    print(f"\n[*] Files in {download_dir}:")
    total_size = 0
    try:
        for file in sorted(os.listdir(download_dir)):
            if file.endswith('.mp4'):
                size = os.path.getsize(f"{download_dir}/{file}") / (1024*1024)
                total_size += size
                print(f"    {file}: {size:.1f} MB")
        print(f"[*] Total size: {total_size:.1f} MB")
    except:
        pass
    
    print('='*60)

if __name__ == "__main__":
    main()
