#!/usr/bin/env python3
"""
HLS Video Downloader for 3seq website
Automatically finds and downloads HLS streams using yt-dlp
"""

import subprocess
import sys
import re
import os
import time
import requests
from urllib.parse import urljoin, urlparse

def check_dependencies():
    """Check if required tools are installed"""
    print("[*] Checking dependencies...")
    
    # Check for yt-dlp
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("[✓] yt-dlp is installed")
    except:
        print("[X] yt-dlp is not installed. Installing...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)
            print("[✓] yt-dlp installed successfully")
        except:
            print("[X] Failed to install yt-dlp. Please install manually.")
            print("    Command: pip install yt-dlp")
            return False
    
    # Check for ffmpeg (recommended for HLS)
    if subprocess.run(['which', 'ffmpeg'], capture_output=True).returncode == 0:
        print("[✓] ffmpeg is installed")
    else:
        print("[!] ffmpeg is not installed. HLS downloads may not merge properly.")
        print("    Install with: sudo apt install ffmpeg")
    
    return True

def extract_m3u8_from_page(url):
    """
    Extract m3u8 URL from the watch page
    Returns m3u8 URL if found, None otherwise
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://x.3seq.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    try:
        print(f"[*] Fetching page: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Look for m3u8 URLs in the HTML
        html_content = response.text
        
        # Pattern 1: Direct m3u8 URLs in src or file attributes
        m3u8_patterns = [
            r'"(https?://[^"]+\.m3u8[^"]*)"',
            r"'(https?://[^']+\.m3u8[^']*)'",
            r'src="([^"]+\.m3u8)"',
            r"src='([^']+\.m3u8)'",
            r'file:"([^"]+\.m3u8)"',
            r"file:'([^']+\.m3u8)'",
        ]
        
        found_urls = []
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            found_urls.extend(matches)
        
        # Remove duplicates
        found_urls = list(set(found_urls))
        
        if found_urls:
            print(f"[✓] Found {len(found_urls)} potential m3u8 URLs")
            
            # Prioritize URLs that look like master playlists
            for m3u8_url in found_urls:
                if 'master' in m3u8_url.lower() or 'index' in m3u8_url.lower():
                    print(f"[*] Selected master playlist: {m3u8_url}")
                    return m3u8_url
            
            # Otherwise return the first one
            print(f"[*] Selected: {found_urls[0]}")
            return found_urls[0]
        
        # Pattern 2: Look for the ts segment pattern and construct m3u8 URL
        # Based on your example: seg-1-v1-a1.ts
        ts_matches = re.findall(r'(https?://[^"\']+/[^/]+/)seg-\d+-v\d+-a\d+\.ts', html_content)
        if ts_matches:
            base_url = ts_matches[0]
            # Try common m3u8 filenames
            possible_m3u8_paths = [
                'master.m3u8',
                'index.m3u8',
                'playlist.m3u8',
                'video.m3u8'
            ]
            
            for m3u8_file in possible_m3u8_paths:
                test_url = urljoin(base_url, m3u8_file)
                try:
                    test_response = requests.head(test_url, headers=headers, timeout=5)
                    if test_response.status_code == 200:
                        print(f"[✓] Constructed m3u8 URL: {test_url}")
                        return test_url
                except:
                    continue
        
        print("[!] No m3u8 URL found in page HTML")
        return None
        
    except Exception as e:
        print(f"[X] Error extracting m3u8: {e}")
        return None

def extract_m3u8_from_network(url):
    """
    Alternative method: Try to find m3u8 by analyzing network patterns
    """
    try:
        # Extract domain and path to construct possible m3u8 URLs
        parsed_url = urlparse(url)
        base_path = parsed_url.path
        
        # Remove the /?do=watch part if present
        if '/?do=watch' in url:
            base_url = url.replace('/?do=watch', '')
        else:
            base_url = url
            
        # Common m3u8 URL patterns for video sites
        possible_m3u8_urls = [
            base_url.replace('/video/', '/hls/') + '/master.m3u8',
            base_url.replace('/video/', '/stream/') + '/index.m3u8',
            base_url + '/master.m3u8',
            base_url + '/playlist.m3u8',
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://x.3seq.com/',
        }
        
        for test_url in possible_m3u8_urls:
            try:
                print(f"[*] Testing: {test_url}")
                response = requests.head(test_url, headers=headers, timeout=5)
                if response.status_code == 200:
                    print(f"[✓] Found m3u8 via pattern: {test_url}")
                    return test_url
            except:
                continue
        
        return None
        
    except Exception as e:
        print(f"[X] Error in network extraction: {e}")
        return None

def download_with_ytdlp(m3u8_url, output_filename, quality='worst'):
    """
    Download HLS stream using yt-dlp
    """
    try:
        print(f"[*] Starting download with yt-dlp...")
        print(f"    URL: {m3u8_url}")
        print(f"    Output: {output_filename}")
        print(f"    Quality: {quality}")
        
        # Basic yt-dlp command for HLS
        cmd = [
            'yt-dlp',
            '-f', quality,  # 'worst' for lowest quality
            '--merge-output-format', 'mp4',
            '--add-header', 'Referer:https://x.3seq.com/',
            '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--concurrent-fragments', '4',  # Download multiple fragments concurrently
            '-o', output_filename,
            m3u8_url
        ]
        
        print(f"[*] Command: {' '.join(cmd)}")
        
        # Run yt-dlp
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[✓] Download completed successfully!")
            print(f"    Output file: {output_filename}")
            return True
        else:
            print(f"[X] Download failed with yt-dlp")
            print(f"    Error: {result.stderr[:500]}")
            return False
            
    except Exception as e:
        print(f"[X] Error downloading with yt-dlp: {e}")
        return False

def process_episode(base_url, episode_num, quality='worst'):
    """
    Process a single episode
    """
    print(f"\n{'='*60}")
    print(f"[*] PROCESSING EPISODE {episode_num}")
    print(f"{'='*60}")
    
    # 1. Generate episode URL
    episode_url = generate_episode_url(base_url, episode_num)
    print(f"[*] Episode URL: {episode_url}")
    
    # 2. Add ?do=watch if needed
    if '?do=watch' not in episode_url:
        watch_url = episode_url + ('/?do=watch' if episode_url.endswith('/') else '/?do=watch')
    else:
        watch_url = episode_url
    
    print(f"[*] Watch URL: {watch_url}")
    
    # 3. Try to extract m3u8 URL
    m3u8_url = extract_m3u8_from_page(watch_url)
    
    if not m3u8_url:
        print("[!] Failed to extract m3u8 from HTML, trying network patterns...")
        m3u8_url = extract_m3u8_from_network(watch_url)
    
    if not m3u8_url:
        print("[X] Could not find m3u8 URL for this episode")
        return False
    
    # 4. Download with yt-dlp
    output_file = f"The_Protector_S01E{episode_num:02d}.mp4"
    success = download_with_ytdlp(m3u8_url, output_file, quality)
    
    return success

def generate_episode_url(base_url, episode_num):
    """Generate URL for specific episode"""
    # Remove any existing random code
    base_url = re.sub(r'-[a-z0-9]{4}(?=/|$)', '', base_url)
    
    # Replace episode number
    if 's01e' in base_url.lower():
        return re.sub(r's01e\d+', f's01e{episode_num:02d}', base_url, flags=re.IGNORECASE)
    elif re.search(r'episode-?\d+', base_url, re.IGNORECASE):
        return re.sub(r'episode-?\d+', f'episode-{episode_num}', base_url, flags=re.IGNORECASE)
    else:
        numbers = re.findall(r'\d+', base_url)
        if numbers:
            last_num = numbers[-1]
            return base_url[::-1].replace(last_num[::-1], str(episode_num)[::-1], 1)[::-1]
        else:
            return f"{base_url}-{episode_num}"

def manual_m3u8_discovery():
    """
    Guide for manual m3u8 discovery
    """
    print("\n" + "="*60)
    print("MANUAL M3U8 DISCOVERY GUIDE")
    print("="*60)
    print("""
If the script fails to find m3u8 automatically, follow these steps:

1. Open the watch page in Chrome/Firefox
2. Press F12 to open Developer Tools
3. Go to the Network tab
4. Reload the page and start playing the video
5. Look for requests containing '.m3u8' in the URL
6. Right-click on the m3u8 request → Copy → Copy link address
7. Use that URL directly with yt-dlp:

   yt-dlp -f worst --add-header "Referer:https://x.3seq.com/" "COPIED_M3U8_URL"

Common m3u8 URL patterns on this site:
  • https://s31.cdn-vids.xyz/hls/.../master.m3u8
  • https://s31.cdn-vids.xyz/hls/.../index.m3u8
  • https://.../playlist.m3u8
""")

def main():
    print("="*60)
    print("HLS VIDEO DOWNLOADER FOR 3SEQ")
    print("="*60)
    
    # Check dependencies
    if not check_dependencies():
        print("[X] Cannot proceed without required dependencies")
        sys.exit(1)
    
    # Get user input
    print("\n" + "="*60)
    print("CONFIGURATION")
    print("="*60)
    
    default_url = "https://x.3seq.com/video/modablaj-the-protector-episode-s01e01"
    base_url = input(f"Enter first episode URL [default: {default_url}]: ").strip()
    if not base_url:
        base_url = default_url
    
    # Get number of episodes
    while True:
        try:
            num_input = input("Enter number of episodes to download: ").strip()
            num_episodes = int(num_input) if num_input else 1
            if num_episodes > 0:
                break
            else:
                print("[!] Please enter a positive number")
        except ValueError:
            print("[!] Please enter a valid number")
    
    # Get starting episode
    while True:
        try:
            start_input = input("Enter starting episode number [default: 1]: ").strip()
            start_episode = int(start_input) if start_input else 1
            if start_episode > 0:
                break
            else:
                print("[!] Please enter a positive number")
        except ValueError:
            print("[!] Please enter a valid number")
    
    # Quality selection
    print("\nSelect quality:")
    print("1. Lowest (recommended for faster download)")
    print("2. Best")
    print("3. Manual format selection")
    
    quality_choice = input("Enter choice [default: 1]: ").strip()
    if quality_choice == '2':
        quality = 'best'
    elif quality_choice == '3':
        quality = input("Enter yt-dlp format: ").strip()
        if not quality:
            quality = 'worst'
    else:
        quality = 'worst'
    
    print(f"\n[*] Starting download of {num_episodes} episode(s)...")
    print(f"[*] Quality setting: {quality}")
    
    successful = 0
    
    for episode_num in range(start_episode, start_episode + num_episodes):
        if process_episode(base_url, episode_num, quality):
            successful += 1
        else:
            print(f"[X] Failed to download episode {episode_num}")
            
            # Offer manual discovery help
            if episode_num == start_episode:  # Only for first failure
                manual = input("\n[?] Do you want to try manual m3u8 discovery? (y/n): ").strip().lower()
                if manual == 'y':
                    manual_m3u8_discovery()
                    print("\n[!] Please find the m3u8 URL manually and update the script.")
                    break
        
        # Delay between episodes
        if episode_num < start_episode + num_episodes - 1:
            print(f"\n[*] Waiting 2 seconds before next episode...")
            time.sleep(2)
    
    # Summary
    print("\n" + "="*60)
    print("DOWNLOAD SUMMARY")
    print("="*60)
    print(f"Total episodes attempted: {num_episodes}")
    print(f"Successfully downloaded: {successful}")
    print(f"Failed: {num_episodes - successful}")
    
    if successful == 0:
        print("\n[!] All downloads failed. The site may have changed.")
        print("[*] Try manual m3u8 discovery as shown above.")
        manual_m3u8_discovery()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Download interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        sys.exit(1)
