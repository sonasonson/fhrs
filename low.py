#!/usr/bin/env python3
"""
Smart Video Downloader for Streaming Sites
Supports 3seq.com and similar sites with dynamic URLs and m3u8 streams
Allows custom base URL and quality selection (240p, 480p, best)
"""

import os
import sys
import re
import time
import requests
import subprocess
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Configuration
DEFAULT_BASE_URL = "https://x.3seq.com/video"
DEFAULT_QUALITY = "240p"

def print_banner():
    """Display script banner"""
    banner = """
============================================================
      Smart Video Downloader for Streaming Sites
         Supports Dynamic URLs & HLS Streams
============================================================
    """
    print(banner)

def check_and_install_dependencies():
    """
    Check for required Python packages and install them if missing.
    Also check for yt-dlp installation.
    """
    print("[*] Checking system dependencies...")
    
    # Check Python packages
    required_packages = ['requests', 'beautifulsoup4']
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package} is already installed")
        except ImportError:
            print(f"  ✗ {package} not found. Installing...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"  ✓ {package} installed successfully")
            except subprocess.CalledProcessError:
                print(f"  ✗ Failed to install {package}. Please install manually: pip install {package}")
                return False
    
    # Check if yt-dlp is installed
    print("[*] Checking for yt-dlp...")
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ yt-dlp is installed (Version: {result.stdout.strip()})")
            return True
        else:
            print("  ✗ yt-dlp is not working properly")
    except FileNotFoundError:
        print("  ✗ yt-dlp is not installed")
    
    # Offer to install yt-dlp
    print("\n[*] yt-dlp is required for downloading videos.")
    choice = input("[?] Do you want to install yt-dlp now? (y/n): ").strip().lower()
    
    if choice == 'y':
        print("[*] Installing yt-dlp...")
        try:
            # Try pip installation first
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'yt-dlp'])
            print("  ✓ yt-dlp installed successfully via pip")
            return True
        except subprocess.CalledProcessError:
            print("  ✗ Failed to install via pip. Trying alternative methods...")
            
            # Try system package manager for Ubuntu/Debian
            try:
                subprocess.check_call(['sudo', 'apt', 'update'])
                subprocess.check_call(['sudo', 'apt', 'install', '-y', 'yt-dlp'])
                print("  ✓ yt-dlp installed successfully via apt")
                return True
            except:
                print("  ✗ Could not install yt-dlp automatically.")
                print("  [!] Please install manually:")
                print("      For Ubuntu/Debian: sudo apt install yt-dlp")
                print("      For other systems: pip install yt-dlp")
                return False
    else:
        print("[!] yt-dlp is required. Please install it manually.")
        return False

def get_user_input():
    """
    Get user input for download parameters
    """
    print("\n" + "="*60)
    print("[*] Configuration Settings")
    print("="*60)
    
    # Get base URL
    base_url = input(f"[?] Enter base URL [{DEFAULT_BASE_URL}]: ").strip()
    if not base_url:
        base_url = DEFAULT_BASE_URL
    
    # Get series name pattern
    print("\n[*] Series name pattern examples:")
    print("    - modablaj-the-protector-episode-s01e")
    print("    - series-name-season1-episode")
    
    series_pattern = input("[?] Enter series name pattern: ").strip()
    if not series_pattern:
        print("[!] Series pattern is required!")
        sys.exit(1)
    
    # Get number of episodes
    try:
        num_episodes = int(input("[?] Enter number of episodes to download: "))
        if num_episodes <= 0:
            print("[!] Please enter a positive number")
            sys.exit(1)
    except ValueError:
        print("[!] Please enter a valid number")
        sys.exit(1)
    
    # Get quality preference
    print("\n[*] Available quality options:")
    print("    1. 240p (Lowest quality)")
    print("    2. 480p (Standard quality)")
    print("    3. 720p (HD quality)")
    print("    4. best (Best available quality)")
    
    quality_map = {
        '1': '240p',
        '2': '480p', 
        '3': '720p',
        '4': 'best'
    }
    
    quality_choice = input("[?] Select quality (1-4) [1]: ").strip()
    if not quality_choice or quality_choice not in quality_map:
        quality = '240p'
    else:
        quality = quality_map[quality_choice]
    
    # Get season number (optional)
    season_num = input("[?] Enter season number [01]: ").strip()
    if not season_num:
        season_num = "01"
    
    return {
        'base_url': base_url.rstrip('/'),
        'series_pattern': series_pattern,
        'num_episodes': num_episodes,
        'quality': quality,
        'season_num': season_num
    }

def get_final_url(initial_url, timeout=30):
    """
    Wait for the URL to transform to its final form with dynamic suffix
    """
    print(f"[*] Accessing initial URL: {initial_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    start_time = time.time()
    final_url = initial_url
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(initial_url, headers=headers, timeout=10, allow_redirects=True)
            current_url = response.url
            
            if current_url != initial_url:
                final_url = current_url
                print(f"[*] URL transformed to: {final_url}")
                return final_url
            
            # Check for meta refresh
            soup = BeautifulSoup(response.content, 'html.parser')
            meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
            
            if meta_refresh and 'url=' in meta_refresh.get('content', ''):
                new_url = meta_refresh['content'].split('url=')[-1]
                if new_url and new_url != initial_url:
                    final_url = urljoin(initial_url, new_url)
                    print(f"[*] Meta refresh detected. New URL: {final_url}")
                    return final_url
            
            # Check for JavaScript redirect in response
            if 'location.href' in response.text or 'window.location' in response.text:
                print("[*] JavaScript redirect detected, waiting for page load...")
                time.sleep(3)
                continue
                
            time.sleep(2)
            
        except requests.RequestException as e:
            print(f"[!] Error accessing URL: {e}")
            time.sleep(3)
    
    print(f"[!] Timeout waiting for URL transformation. Using: {final_url}")
    return final_url

def extract_video_url(watch_url):
    """
    Extract m3u8 video URL from the watch page
    """
    print(f"[*] Extracting video from watch page...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://x.3seq.com/'
    }
    
    try:
        response = requests.get(watch_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Method 1: Look for iframe with video embed
        iframe = soup.find('iframe', src=re.compile(r'vidsp\.net|embed'))
        if iframe:
            iframe_src = iframe.get('src')
            if iframe_src:
                print(f"[*] Found video iframe: {iframe_src}")
                return extract_m3u8_from_embed(iframe_src)
        
        # Method 2: Look for direct m3u8 links in page
        m3u8_patterns = [
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'"(https?://[^"]+\.m3u8[^"]*)"',
            r"'(https?://[^']+\.m3u8[^']*)'",
            r'src:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']'
        ]
        
        page_text = response.text
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                if 'm3u8' in match:
                    print(f"[*] Found m3u8 URL: {match}")
                    return match
        
        # Method 3: Look for video sources
        video_tags = soup.find_all(['video', 'source'])
        for tag in video_tags:
            video_src = tag.get('src') or tag.get('data-src')
            if video_src and 'm3u8' in video_src:
                print(f"[*] Found video source: {video_src}")
                return video_src
        
        print("[!] Could not find video URL in the page")
        return None
        
    except requests.RequestException as e:
        print(f"[!] Error accessing watch page: {e}")
        return None

def extract_m3u8_from_embed(embed_url):
    """
    Extract m3u8 URL from embed page
    """
    print(f"[*] Extracting from embed page: {embed_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://x.3seq.com/'
    }
    
    try:
        response = requests.get(embed_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Look for m3u8 links in embed page
        m3u8_patterns = [
            r'src:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'"(https?://[^"]+\.m3u8[^"]*)"',
            r"'(https?://[^']+\.m3u8[^']*)'",
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)'
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, response.text)
            for match in matches:
                if 'm3u8' in match:
                    print(f"[*] Found m3u8 URL in embed: {match}")
                    return match
        
        # If no m3u8 found, return embed URL for yt-dlp to handle
        print("[*] No direct m3u8 found, using embed URL")
        return embed_url
        
    except requests.RequestException as e:
        print(f"[!] Error accessing embed page: {e}")
        return embed_url

def download_with_ytdlp(video_url, episode_num, quality, download_dir):
    """
    Download video using yt-dlp with specified quality
    """
    # Create filename
    filename = f"{download_dir}/الحلقة_{episode_num:02d}.mp4"
    
    # Map quality to yt-dlp format selector
    quality_map = {
        '240p': 'best[height<=240]',
        '480p': 'best[height<=480]', 
        '720p': 'best[height<=720]',
        'best': 'best'
    }
    
    format_selector = quality_map.get(quality, 'best[height<=240]')
    
    # Build yt-dlp command
    command = [
        'yt-dlp',
        '-f', format_selector,
        '--merge-output-format', 'mp4',
        '--no-part',
        '--progress',
        '--quiet',
        '--no-warnings',
        '-o', filename,
        video_url
    ]
    
    print(f"[*] Downloading with quality: {quality}")
    print(f"[*] Command: yt-dlp -f '{format_selector}' -o '{filename}' '{video_url[:50]}...'")
    
    try:
        # Execute yt-dlp
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Monitor progress
        for line in process.stdout:
            if '[download]' in line:
                print(f"    {line.strip()}")
            elif 'ETA' in line or '%' in line:
                print(f"    {line.strip()}", end='\r')
        
        process.wait()
        
        if process.returncode == 0:
            # Check if file was created
            if os.path.exists(filename):
                file_size = os.path.getsize(filename) / (1024*1024)  # MB
                print(f"\n[*] Download complete: {filename} ({file_size:.1f} MB)")
                return True
            else:
                print("[!] Download completed but file not found")
                return False
        else:
            print(f"[!] yt-dlp failed with exit code: {process.returncode}")
            return False
            
    except Exception as e:
        print(f"[!] Error during download: {e}")
        return False

def download_episodes(params):
    """
    Main function to download multiple episodes
    """
    base_url = params['base_url']
    series_pattern = params['series_pattern']
    num_episodes = params['num_episodes']
    quality = params['quality']
    season_num = params['season_num']
    
    # Create download directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    download_dir = f"downloads_{timestamp}"
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"\n[*] Starting download session...")
    print(f"    Base URL: {base_url}")
    print(f"    Series: {series_pattern}")
    print(f"    Episodes: 1-{num_episodes}")
    print(f"    Quality: {quality}")
    print(f"    Output: {download_dir}/")
    
    successful = 0
    failed = []
    
    for episode in range(1, num_episodes + 1):
        print(f"\n{'='*60}")
        print(f"[*] Processing Episode {episode}/{num_episodes}")
        print('='*60)
        
        try:
            # Construct episode URL
            episode_str = f"{episode:02d}"
            episode_pattern = series_pattern.replace('s01', f's{season_num}').replace('e01', f'e{episode_str}')
            
            initial_url = f"{base_url}/{episode_pattern}"
            
            # Get final URL with dynamic suffix
            final_url = get_final_url(initial_url)
            
            # Add watch parameter
            if '?do=watch' not in final_url:
                if not final_url.endswith('/'):
                    final_url += '/'
                watch_url = final_url + '?do=watch'
            else:
                watch_url = final_url
            
            print(f"[*] Watch URL: {watch_url}")
            
            # Extract video URL
            video_url = extract_video_url(watch_url)
            
            if not video_url:
                print(f"[!] Failed to extract video URL for episode {episode}")
                failed.append(episode)
                continue
            
            # Download video using yt-dlp
            if download_with_ytdlp(video_url, episode, quality, download_dir):
                successful += 1
                print(f"[✓] Episode {episode} downloaded successfully")
            else:
                print(f"[!] Failed to download episode {episode}")
                failed.append(episode)
            
            # Delay between episodes
            if episode < num_episodes:
                delay = 3
                print(f"[*] Waiting {delay} seconds before next episode...")
                time.sleep(delay)
                
        except Exception as e:
            print(f"[!] Error processing episode {episode}: {e}")
            failed.append(episode)
            continue
    
    # Print summary
    print(f"\n{'='*60}")
    print("[*] DOWNLOAD SESSION COMPLETED")
    print('='*60)
    print(f"[*] Successful: {successful}/{num_episodes}")
    
    if failed:
        print(f"[!] Failed episodes: {failed}")
    
    print(f"[*] Files saved in: {download_dir}/")
    print('='*60)

def main():
    """
    Main execution function
    """
    print_banner()
    
    # Check dependencies
    if not check_and_install_dependencies():
        print("[!] Dependencies check failed. Exiting.")
        sys.exit(1)
    
    # Get user input
    params = get_user_input()
    
    # Confirm settings
    print("\n[*] Confirm settings:")
    print(f"    Base URL: {params['base_url']}")
    print(f"    Series Pattern: {params['series_pattern']}")
    print(f"    Episodes: 1-{params['num_episodes']}")
    print(f"    Quality: {params['quality']}")
    
    confirm = input("\n[?] Start download? (y/n): ").strip().lower()
    if confirm != 'y':
        print("[*] Download cancelled.")
        sys.exit(0)
    
    # Start download
    download_episodes(params)
    
    print("\n[*] Script execution completed!")

if __name__ == "__main__":
    main()
