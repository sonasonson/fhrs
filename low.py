#!/usr/bin/env python3
"""
Smart script for downloading The Protector series episodes from 3seq website
Handles redirects and random URL codes automatically
"""

import subprocess
import sys
import re
import os
import time
import json
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse, urljoin, parse_qs, urlencode

def install_package(package: str) -> None:
    """Install a Python package if it's not already installed"""
    try:
        __import__(package)
        print(f"[✓] '{package}' is already installed")
    except ImportError:
        print(f"[!] Installing missing package: '{package}'...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"[✓] Successfully installed '{package}'")
        except subprocess.CalledProcessError as e:
            print(f"[X] Failed to install '{package}': {e}")
            sys.exit(1)

def check_system_dependencies() -> None:
    """Check if system has required dependencies"""
    print("[*] Checking system dependencies...")
    
    # Check if Python3 is installed
    try:
        subprocess.run(['python3', '--version'], capture_output=True, check=True)
        print("[✓] Python3 is installed")
    except:
        print("[X] Python3 is not installed. Install with: sudo apt install python3")
        sys.exit(1)
    
    # Check if pip is installed
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, check=True)
        print("[✓] pip is installed")
    except:
        print("[!] pip is not installed. Installing pip...")
        try:
            subprocess.run(['sudo', 'apt', 'install', '-y', 'python3-pip'], check=True)
            print("[✓] pip installed successfully")
        except:
            print("[X] Failed to install pip. Please install manually: sudo apt install python3-pip")
            sys.exit(1)

def get_final_url_with_redirect(session, initial_url: str) -> Tuple[str, Dict[str, Any]]:
    """
    Follow redirects to get the final URL with random code
    Returns the final URL and response information
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Referer': 'https://www.google.com/',
    }
    
    try:
        print(f"    Following redirects from: {initial_url}")
        
        # Allow redirects and get final URL
        response = session.get(initial_url, headers=headers, allow_redirects=True, timeout=30)
        response.raise_for_status()
        
        final_url = response.url
        print(f"    Final redirected URL: {final_url}")
        
        # Parse the URL to extract components
        parsed_url = urlparse(final_url)
        path_parts = parsed_url.path.split('/')
        
        # Extract the random code from the URL (like -26rf, -pjh0)
        random_code = None
        for part in path_parts:
            if part and '-' in part and re.search(r'[a-z0-9]{4}$', part):
                random_code = part.split('-')[-1]
                break
        
        return final_url, {
            'response': response,
            'random_code': random_code,
            'parsed_url': parsed_url
        }
        
    except Exception as e:
        print(f"    [X] Error following redirects: {e}")
        return initial_url, {'error': str(e)}

def analyze_page_content(response_text: str) -> Dict[str, Any]:
    """
    Analyze the page content for video sources and player configurations
    """
    from bs4 import BeautifulSoup
    
    analysis = {
        'video_sources': [],
        'scripts': [],
        'iframes': [],
        'video_tags': [],
        'player_configs': [],
        'm3u8_links': [],
        'mp4_links': []
    }
    
    try:
        soup = BeautifulSoup(response_text, 'html.parser')
        
        # Find all video sources
        for source in soup.find_all('source'):
            src = source.get('src')
            if src:
                analysis['video_sources'].append({
                    'src': src,
                    'type': source.get('type', ''),
                    'quality': source.get('title', source.get('label', ''))
                })
        
        # Find all video tags
        for video in soup.find_all('video'):
            src = video.get('src')
            if src:
                analysis['video_tags'].append({
                    'src': src,
                    'poster': video.get('poster', ''),
                    'attributes': dict(video.attrs)
                })
        
        # Find all iframes
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src')
            if src:
                analysis['iframes'].append(src)
        
        # Find all script tags that might contain video config
        for script in soup.find_all('script'):
            if script.string:
                script_content = script.string
                analysis['scripts'].append(script_content[:500] + '...' if len(script_content) > 500 else script_content)
                
                # Look for common video player configurations
                patterns = [
                    r'file\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|webm))["\']',
                    r'src\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|webm))["\']',
                    r'videoUrl\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|webm))["\']',
                    r'url\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|webm))["\']',
                    r'source\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|webm))["\']',
                    r'"(?:file|src|url|source)"\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|webm))["\']'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, script_content, re.IGNORECASE)
                    for match in matches:
                        analysis['player_configs'].append(match)
        
        # Find direct links in the page
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            if href.lower().endswith('.m3u8'):
                analysis['m3u8_links'].append(href)
            elif href.lower().endswith('.mp4'):
                analysis['mp4_links'].append(href)
        
        # Also search in the entire HTML for video links
        html_text = str(soup)
        m3u8_patterns = re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html_text, re.IGNORECASE)
        mp4_patterns = re.findall(r'https?://[^\s"\']+\.mp4[^\s"\']*', html_text, re.IGNORECASE)
        
        analysis['m3u8_links'].extend(m3u8_patterns)
        analysis['mp4_links'].extend(mp4_patterns)
        
        # Remove duplicates
        analysis['m3u8_links'] = list(set(analysis['m3u8_links']))
        analysis['mp4_links'] = list(set(analysis['mp4_links']))
        
        return analysis
        
    except Exception as e:
        print(f"    [X] Error analyzing page: {e}")
        return analysis

def extract_video_url_from_page(session, page_url: str) -> Optional[str]:
    """
    Extract video URL from the watch page after redirect
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://x.3seq.com/',
        }
        
        print(f"    Fetching watch page: {page_url}")
        response = session.get(page_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Analyze the page content
        analysis = analyze_page_content(response.text)
        
        # Strategy 1: Check for direct MP4 links (prefer low quality)
        low_quality_mp4 = []
        medium_quality_mp4 = []
        high_quality_mp4 = []
        
        for mp4_link in analysis['mp4_links']:
            if any(q in mp4_link.lower() for q in ['360', '480', 'low', 'small', 'sd']):
                low_quality_mp4.append(mp4_link)
            elif any(q in mp4_link.lower() for q in ['720', 'medium', 'hd']):
                medium_quality_mp4.append(mp4_link)
            elif any(q in mp4_link.lower() for q in ['1080', 'high', 'full']):
                high_quality_mp4.append(mp4_link)
            else:
                medium_quality_mp4.append(mp4_link)
        
        # Prefer low quality first
        if low_quality_mp4:
            print(f"    Found {len(low_quality_mp4)} low quality MP4 links")
            return low_quality_mp4[0]
        
        # Strategy 2: Check video sources from <source> tags
        low_quality_sources = []
        for source in analysis['video_sources']:
            quality = source['quality'].lower() + source['src'].lower()
            if any(q in quality for q in ['360', '480', 'low', 'small', 'sd']):
                low_quality_sources.append(source['src'])
        
        if low_quality_sources:
            print(f"    Found {len(low_quality_sources)} low quality video sources")
            return low_quality_sources[0]
        
        # Strategy 3: Check video tags
        if analysis['video_tags']:
            print(f"    Found {len(analysis['video_tags'])} video tags")
            return analysis['video_tags'][0]['src']
        
        # Strategy 4: Check player configurations from scripts
        if analysis['player_configs']:
            print(f"    Found {len(analysis['player_configs'])} player configurations")
            # Look for low quality in configs
            for config in analysis['player_configs']:
                if any(q in config.lower() for q in ['360', '480', 'low']):
                    return config
            return analysis['player_configs'][0]
        
        # Strategy 5: Check M3U8 links (streaming playlist)
        if analysis['m3u8_links']:
            print(f"    Found {len(analysis['m3u8_links'])} M3U8 links")
            # Try to find lowest quality M3U8
            for m3u8 in analysis['m3u8_links']:
                if any(q in m3u8.lower() for q in ['360', '480', 'low']):
                    return m3u8
            return analysis['m3u8_links'][0]
        
        # Strategy 6: Fallback to any MP4 link
        if medium_quality_mp4:
            print(f"    Found {len(medium_quality_mp4)} medium quality MP4 links")
            return medium_quality_mp4[0]
        
        if high_quality_mp4:
            print(f"    Found {len(high_quality_mp4)} high quality MP4 links")
            return high_quality_mp4[0]
        
        # Strategy 7: Search for common video patterns in the entire page
        video_patterns = [
            r'"(?:video|file|source|src|url)_?(?:url|src|file)?"\s*:\s*"([^"]+\.(?:mp4|m3u8|webm)[^"]*)"',
            r'video\s*:\s*{[^}]*src\s*:\s*"([^"]+)"',
            r'<video[^>]+src="([^"]+)"',
            r'src="(https?://[^"]+\.(?:mp4|m3u8|webm)[^"]*)"'
        ]
        
        for pattern in video_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            for match in matches:
                if 'low' in match.lower() or '360' in match.lower() or '480' in match.lower():
                    print(f"    Found video URL via pattern matching")
                    return match
        
        print(f"    [!] No video URL found after analyzing {len(response.text)} characters of HTML")
        print(f"    [!] Found {len(analysis['video_sources'])} video sources, {len(analysis['mp4_links'])} MP4 links")
        
        # Debug: Save HTML for manual inspection
        debug_filename = f"debug_page_{int(time.time())}.html"
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(response.text[:50000])  # First 50k chars
        print(f"    [D] Saved debug HTML to {debug_filename}")
        
        return None
        
    except Exception as e:
        print(f"    [X] Error extracting video URL: {e}")
        return None

def process_episode(session, base_url: str, episode_num: int) -> Optional[str]:
    """
    Process a single episode: follow redirects, get watch page, extract video
    Returns the video URL if found
    """
    print(f"\n    [*] Processing Episode {episode_num}")
    
    # Step 1: Generate the initial episode URL
    episode_url = generate_episode_url(base_url, episode_num)
    print(f"    Initial URL: {episode_url}")
    
    # Step 2: Follow redirects to get the final URL with random code
    final_url, redirect_info = get_final_url_with_redirect(session, episode_url)
    
    if 'error' in redirect_info:
        return None
    
    # Step 3: Construct the watch URL
    parsed_url = urlparse(final_url)
    watch_path = parsed_url.path
    
    # Ensure the path ends with /
    if not watch_path.endswith('/'):
        watch_path += '/'
    
    # Add ?do=watch parameter
    watch_url = f"{parsed_url.scheme}://{parsed_url.netloc}{watch_path}?do=watch"
    print(f"    Watch URL: {watch_url}")
    
    # Step 4: Extract video URL from watch page
    video_url = extract_video_url_from_page(session, watch_url)
    
    return video_url

def generate_episode_url(base_url: str, episode_num: int) -> str:
    """
    Generate the URL for a specific episode number
    Handles multiple URL patterns
    """
    # If base_url already has a pattern like -26rf, remove it
    base_url = re.sub(r'-[a-z0-9]{4}(?=/|$)', '', base_url)
    
    # Pattern 1: s01e01 format (case insensitive)
    if re.search(r's\d+e\d+', base_url, re.IGNORECASE):
        pattern = re.compile(r'(s\d+e)\d+', re.IGNORECASE)
        return pattern.sub(f'\\g<1>{episode_num:02d}', base_url)
    
    # Pattern 2: episode-1 or episode-01 format
    elif 'episode' in base_url.lower():
        # Remove any existing episode number
        base_without_num = re.sub(r'episode[^\d]*\d+', 'episode', base_url, flags=re.IGNORECASE)
        return f"{base_without_num}{episode_num}"
    
    # Pattern 3: Try to find and replace the last number
    else:
        # Find all numbers in the URL
        numbers = re.findall(r'\d+', base_url)
        if numbers:
            last_num = numbers[-1]
            # Replace the last occurrence
            return base_url[::-1].replace(last_num[::-1], str(episode_num)[::-1], 1)[::-1]
        else:
            # Append episode number
            return f"{base_url}-{episode_num}"

def download_video(session, video_url: str, filename: str) -> bool:
    """
    Download video from URL with progress indication
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
            'Referer': 'https://x.3seq.com/',
        }
        
        print(f"    Starting download: {filename}")
        
        response = session.get(video_url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        downloaded = 0
        chunk_size = 8192
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f"\r    Progress: {percent:.1f}% ({mb_downloaded:.1f} MB / {mb_total:.1f} MB)", end='')
        
        print(f"\n    [✓] Download completed: {filename}")
        return True
        
    except Exception as e:
        print(f"\n    [X] Download failed: {e}")
        return False

def main():
    print("=" * 70)
    print("THE PROTECTOR SERIES DOWNLOADER (Enhanced Redirect Handling)")
    print("=" * 70)
    
    # Check dependencies and install packages
    check_system_dependencies()
    
    print("\n[*] Checking Python packages...")
    required_packages = ['requests', 'beautifulsoup4', 'urllib3']
    for package in required_packages:
        install_package(package)
    
    import requests
    
    # Create session
    session = requests.Session()
    
    print("\n" + "=" * 70)
    print("CONFIGURATION")
    print("=" * 70)
    
    # Get user input
    default_url = "https://x.3seq.com/video/modablaj-the-protector-episode-s01e01"
    base_url = input(f"Enter first episode URL [default: {default_url}]: ").strip()
    if not base_url:
        base_url = default_url
    
    # Get number of episodes
    while True:
        try:
            num_episodes = input("Enter number of episodes to download: ").strip()
            if num_episodes:
                num_episodes = int(num_episodes)
                if num_episodes > 0:
                    break
                else:
                    print("[!] Please enter a positive number")
            else:
                num_episodes = 1
                break
        except ValueError:
            print("[!] Please enter a valid number")
    
    # Get starting episode
    while True:
        try:
            start_episode = input(f"Enter starting episode number [default: 1]: ").strip()
            if start_episode:
                start_episode = int(start_episode)
                if start_episode > 0:
                    break
                else:
                    print("[!] Please enter a positive number")
            else:
                start_episode = 1
                break
        except ValueError:
            print("[!] Please enter a valid number")
    
    # Create download directory
    download_dir = "the_protector_episodes"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"[✓] Created download directory: {download_dir}")
    
    print("\n" + "=" * 70)
    print("STARTING DOWNLOAD PROCESS")
    print("=" * 70)
    
    successful_downloads = 0
    
    for episode_num in range(start_episode, start_episode + num_episodes):
        print(f"\n[*] Episode {episode_num} of {start_episode + num_episodes - 1}")
        
        video_url = process_episode(session, base_url, episode_num)
        
        if video_url:
            filename = f"The_Protector_S01E{episode_num:02d}.mp4"
            filepath = os.path.join(download_dir, filename)
            
            if download_video(session, video_url, filepath):
                successful_downloads += 1
        else:
            print(f"    [X] Failed to process Episode {episode_num}")
        
        # Delay between episodes
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    print(f"Total episodes attempted: {num_episodes}")
    print(f"Successfully downloaded: {successful_downloads}")
    print(f"Failed: {num_episodes - successful_downloads}")
    print(f"Download location: {os.path.abspath(download_dir)}")
    
    session.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Download interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        sys.exit(1)
