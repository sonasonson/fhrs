#!/usr/bin/env python3
"""
Smart Video Downloader for 3seq.com
Downloads episodes of "المحافظ" (The Protector) series in low quality.
Automatically handles dynamic URL changes and video link extraction.
"""

import os
import sys
import re
import time
import requests
import subprocess
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

def check_and_install_dependencies():
    """
    Check for required Python packages and install them if missing.
    """
    required_packages = ['requests', 'beautifulsoup4']
    
    print("[*] Checking dependencies...")
    
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
                sys.exit(1)

def get_final_url(initial_url, timeout=30):
    """
    Wait for the URL to transform to its final form with the dynamic suffix.
    Example: https://x.3seq.com/video/modablaj-the-protector-episode-s01e01
    transforms to: https://x.3seq.com/video/modablaj-the-protector-episode-s01e01-cksi
    """
    print(f"[*] Accessing initial URL: {initial_url}")
    
    start_time = time.time()
    final_url = initial_url
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(initial_url, timeout=10, allow_redirects=True)
            current_url = response.url
            
            # Check if URL has changed (has dynamic suffix like -cksi)
            if current_url != initial_url:
                final_url = current_url
                print(f"[*] URL transformed to: {final_url}")
                return final_url
            
            # Also check for meta refresh or JavaScript redirects
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for meta refresh
            meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if meta_refresh and 'url=' in meta_refresh.get('content', ''):
                new_url = meta_refresh['content'].split('url=')[-1]
                if new_url and new_url != initial_url:
                    final_url = urljoin(initial_url, new_url)
                    print(f"[*] Meta refresh detected. New URL: {final_url}")
                    return final_url
            
            time.sleep(2)  # Wait before next check
            
        except requests.RequestException as e:
            print(f"[!] Error accessing URL: {e}")
            time.sleep(3)
    
    print(f"[!] Timeout waiting for URL transformation. Using initial URL.")
    return final_url

def extract_video_url(watch_url):
    """
    Extract the actual video URL from the watch page.
    The video is embedded from v.vidsp.net domain.
    """
    print(f"[*] Extracting video from watch page: {watch_url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(watch_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Pattern 1: Look for iframe with vidsp.net
        iframe = soup.find('iframe', src=re.compile(r'vidsp\.net'))
        if iframe:
            iframe_src = iframe.get('src')
            if iframe_src:
                print(f"[*] Found video iframe: {iframe_src}")
                return iframe_src
        
        # Pattern 2: Look for script with video embed
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Look for embed patterns
                patterns = [
                    r'embed-\w+\.html',
                    r'v\.vidsp\.net/embed',
                    r'src=["\'](https?://v\.vidsp\.net/[^"\']+)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, script.string)
                    if match:
                        video_url = match.group(0)
                        if not video_url.startswith('http'):
                            video_url = 'https://' + video_url if not video_url.startswith('//') else 'https:' + video_url
                        print(f"[*] Found video URL in script: {video_url}")
                        return video_url
        
        # Pattern 3: Look for video source in HTML
        video_tags = soup.find_all(['video', 'source'])
        for tag in video_tags:
            video_src = tag.get('src')
            if video_src and 'vidsp' in video_src:
                print(f"[*] Found video source: {video_src}")
                return video_src
        
        print("[!] Could not find video URL in the page")
        print("[*] Trying alternative extraction from page content...")
        
        # Save page for debugging
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("[*] Saved page content to debug_page.html for inspection")
        
        return None
        
    except requests.RequestException as e:
        print(f"[!] Error accessing watch page: {e}")
        return None

def download_video(video_url, episode_num, quality='low'):
    """
    Download the video file.
    In actual implementation, this would need to handle the actual video streaming.
    For vidsp.net, we might need to use yt-dlp or similar tool.
    """
    print(f"[*] Preparing to download Episode {episode_num}...")
    print(f"[*] Video URL: {video_url}")
    
    # Create downloads directory
    download_dir = "المحافظ_الموسم_1"
    os.makedirs(download_dir, exist_ok=True)
    
    filename = f"{download_dir}/المحافظ_الحلقة_{episode_num:02d}.mp4"
    
    print(f"[*] This script has extracted the video embed URL.")
    print(f"[*] For actual video download, you need to use yt-dlp or similar tool.")
    print(f"[*] Recommended command:")
    print(f"    yt-dlp -f 'best[height<=480]' -o '{filename}' '{video_url}'")
    
    # Alternative: Use requests for direct download (if direct link available)
    try:
        # First, try to get the direct video link from the embed page
        embed_response = requests.get(video_url, timeout=10)
        
        # Look for m3u8 or mp4 links (common for video streaming)
        m3u8_pattern = r'(https?://[^\s"\']+\.m3u8[^\s"\']*)'
        mp4_pattern = r'(https?://[^\s"\']+\.mp4[^\s"\']*)'
        
        for pattern in [m3u8_pattern, mp4_pattern]:
            matches = re.findall(pattern, embed_response.text)
            if matches:
                direct_url = matches[0]  # Take first match
                print(f"[*] Found direct video URL: {direct_url}")
                
                # Try to download
                print(f"[*] Downloading {filename}...")
                
                video_response = requests.get(direct_url, stream=True, timeout=30)
                video_response.raise_for_status()
                
                total_size = int(video_response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(filename, 'wb') as f:
                    for chunk in video_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\r[*] Progress: {percent:.1f}%", end='')
                
                print(f"\n[*] Download complete: {filename}")
                return True
                
    except Exception as e:
        print(f"[!] Direct download failed: {e}")
    
    # Save the embed URL to a text file for manual download
    urls_file = f"{download_dir}/video_urls.txt"
    with open(urls_file, 'a', encoding='utf-8') as f:
        f.write(f"Episode {episode_num}: {video_url}\n")
    
    print(f"[*] Video URL saved to {urls_file}")
    print(f"[*] You can download all episodes later using yt-dlp")
    
    return False

def download_episodes(base_url, num_episodes):
    """
    Main function to download multiple episodes.
    """
    print(f"[*] Starting download of {num_episodes} episodes...")
    print("[*] Base pattern: modablaj-the-protector-episode-s01e")
    
    successful_downloads = 0
    
    for episode in range(1, num_episodes + 1):
        print(f"\n{'='*60}")
        print(f"[*] Processing Episode {episode}/{num_episodes}")
        print('='*60)
        
        try:
            # Construct initial URL
            episode_str = f"{episode:02d}"  # 01, 02, etc.
            initial_url = f"{base_url}/modablaj-the-protector-episode-s01e{episode_str}"
            
            # Step 1: Get final URL with dynamic suffix
            final_url = get_final_url(initial_url)
            
            # Step 2: Add ?do=watch parameter
            watch_url = f"{final_url}?do=watch"
            if not final_url.endswith('/'):
                watch_url = f"{final_url}/?do=watch"
            
            print(f"[*] Watch URL: {watch_url}")
            
            # Step 3: Extract video URL from watch page
            video_url = extract_video_url(watch_url)
            
            if not video_url:
                print(f"[!] Failed to extract video URL for episode {episode}")
                continue
            
            # Step 4: Download the video
            if download_video(video_url, episode):
                successful_downloads += 1
            
            # Delay between episodes to avoid overwhelming the server
            if episode < num_episodes:
                print(f"[*] Waiting 5 seconds before next episode...")
                time.sleep(5)
                
        except Exception as e:
            print(f"[!] Error processing episode {episode}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print(f"[*] Download session completed!")
    print(f"[*] Successfully processed: {successful_downloads}/{num_episodes} episodes")
    print('='*60)

def main():
    """
    Main function with user interaction.
    """
    print("="*60)
    print("Smart Video Downloader for 3seq.com")
    print("المحافظ (The Protector) - Season 1 - Dubbed")
    print("="*60)
    
    # Check and install dependencies
    check_and_install_dependencies()
    
    # Ask for number of episodes
    try:
        num_episodes = int(input("\n[*] Enter number of episodes to download (e.g., 10): "))
        if num_episodes <= 0:
            print("[!] Please enter a positive number")
            return
    except ValueError:
        print("[!] Please enter a valid number")
        return
    
    # Base URL
    base_url = "https://x.3seq.com/video"
    
    # Start download process
    download_episodes(base_url, num_episodes)
    
    print("\n[*] Script execution completed!")
    print("[*] Note: If videos weren't downloaded directly,")
    print("[*] check the 'video_urls.txt' file and use yt-dlp to download.")
    print("[*] Install yt-dlp: sudo apt install yt-dlp (on Ubuntu)")

if __name__ == "__main__":
    main()
