#!/usr/bin/env python3
"""
Smart script for downloading The Protector series episodes from 3seq website
Automatically installs required Python packages if missing
"""

import subprocess
import sys
import re
import os
import time
from typing import Optional, List

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

def get_episode_url(base_url: str, episode_num: int) -> str:
    """
    Generate the URL for a specific episode number
    Handles multiple URL patterns (s01e01, episode-1, etc.)
    """
    # Pattern 1: s01e01 format (case insensitive)
    if re.search(r's\d+e\d+', base_url, re.IGNORECASE):
        pattern = re.compile(r'(s\d+e)\d+', re.IGNORECASE)
        return pattern.sub(f'\\g<1>{episode_num:02d}', base_url)
    
    # Pattern 2: episode-1 or episode-01 format
    elif 'episode' in base_url.lower():
        # Find the episode number in the URL
        base_without_ep = re.sub(r'episode[^\d]*\d+', '', base_url, flags=re.IGNORECASE)
        return f"{base_without_ep}episode-{episode_num}"
    
    # Pattern 3: Generic number replacement (last number in URL)
    else:
        # Find all numbers in the URL
        numbers = re.findall(r'\d+', base_url)
        if numbers:
            last_num = numbers[-1]
            # Replace the last occurrence of the number
            parts = base_url.rsplit(last_num, 1)
            return f"{parts[0]}{episode_num}{parts[1]}"
        else:
            # If no number found, append episode number at the end
            return f"{base_url}-{episode_num}"

def extract_video_url(page_url: str, session) -> Optional[str]:
    """
    Extract the low quality video URL from the watch page
    Returns None if no video URL found
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        
        print(f"    Fetching page: {page_url}")
        response = session.get(page_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Import BeautifulSoup here after installation check
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Strategy 1: Look for video sources with "low" in URL or quality
        video_sources = []
        
        # Check <source> tags
        for source in soup.find_all('source'):
            src = source.get('src')
            if src:
                # Check for low quality indicators
                quality = source.get('title', '').lower() + source.get('label', '').lower() + src.lower()
                if 'low' in quality or '360' in quality or '480' in quality:
                    video_sources.append(('source_tag', src, quality))
        
        # Check <video> tags
        for video in soup.find_all('video'):
            src = video.get('src')
            if src:
                quality = video.get('title', '').lower() + src.lower()
                if 'low' in quality or '360' in quality or '480' in quality:
                    video_sources.append(('video_tag', src, quality))
        
        # Check <iframe> tags (might contain video)
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src')
            if src and ('video' in src.lower() or 'player' in src.lower()):
                video_sources.append(('iframe', src, 'iframe'))
        
        # Check <a> tags with video extensions
        for link in soup.find_all('a', href=True):
            href = link['href']
            if any(href.lower().endswith(ext) for ext in ['.mp4', '.m3u8', '.webm', '.avi', '.mkv']):
                video_sources.append(('link', href, 'direct_link'))
        
        # Strategy 2: Look for common video hosting patterns in scripts
        for script in soup.find_all('script'):
            if script.string:
                # Look for MP4 URLs in script content
                mp4_urls = re.findall(r'"(https?://[^"]+\.mp4[^"]*)"', script.string)
                for url in mp4_urls:
                    if 'low' in url.lower() or '360' in url.lower() or '480' in url.lower():
                        video_sources.append(('script', url, 'script_mp4'))
        
        # Select the best video source
        if video_sources:
            # Sort by quality indicators (low quality first)
            def quality_score(source):
                _, _, quality = source
                score = 0
                if 'low' in quality:
                    score -= 10
                if '360' in quality:
                    score -= 5
                if '480' in quality:
                    score -= 3
                if 'high' in quality or '720' in quality or '1080' in quality:
                    score += 5
                return score
            
            video_sources.sort(key=quality_score)
            selected_source = video_sources[0]
            video_url = selected_source[1]
            
            # Convert relative URL to absolute
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            elif video_url.startswith('/'):
                from urllib.parse import urljoin
                video_url = urljoin(page_url, video_url)
            
            print(f"    Found video source: {selected_source[0]} (priority: {selected_source[2]})")
            return video_url
        
        # Strategy 3: Look for common video player patterns
        video_patterns = [
            r'file:\s*["\'](https?://[^"\']+\.(?:mp4|m3u8|webm))["\']',
            r'src:\s*["\'](https?://[^"\']+\.(?:mp4|m3u8|webm))["\']',
            r'videoUrl:\s*["\'](https?://[^"\']+\.(?:mp4|m3u8|webm))["\']',
        ]
        
        for pattern in video_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            for match in matches:
                if 'low' in match.lower() or '360' in match.lower() or '480' in match.lower():
                    print(f"    Found video URL via regex pattern")
                    return match
        
        print("    [!] No video URL found in page")
        return None
        
    except Exception as e:
        print(f"    [X] Error extracting video URL: {e}")
        return None

def download_video(video_url: str, filename: str, session) -> bool:
    """
    Download video from direct URL with progress indicator
    Returns True if successful, False otherwise
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
        }
        
        print(f"    Starting download: {filename}")
        
        # Stream the download to handle large files
        response = session.get(video_url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        # Get file size if available
        total_size = int(response.headers.get('content-length', 0))
        
        # Download in chunks
        downloaded = 0
        chunk_size = 8192
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Show progress if we know total size
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f"\r    Progress: {percent:.1f}% ({mb_downloaded:.1f} MB / {mb_total:.1f} MB)", end='')
        
        print()  # New line after progress bar
        print(f"    [✓] Download completed: {filename}")
        return True
        
    except Exception as e:
        print(f"\n    [X] Download failed: {e}")
        return False

def create_download_directory() -> str:
    """Create a directory for downloaded episodes"""
    download_dir = "the_protector_episodes"
    
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"[✓] Created download directory: {download_dir}")
    
    return download_dir

def main():
    """Main function to orchestrate the downloading process"""
    print("=" * 60)
    print("THE PROTECTOR SERIES DOWNLOADER")
    print("=" * 60)
    print()
    
    # Step 1: Check system dependencies
    check_system_dependencies()
    
    # Step 2: Install required Python packages
    print("\n[*] Checking Python packages...")
    required_packages = ['requests', 'beautifulsoup4', 'urllib3']
    for package in required_packages:
        install_package(package)
    
    # Now import the packages after installation check
    import requests
    from urllib.parse import urljoin
    
    # Create session for connection pooling
    session = requests.Session()
    
    # Step 3: Get user input
    print("\n" + "=" * 60)
    print("CONFIGURATION")
    print("=" * 60)
    
    # Get base URL
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
    
    # Get starting episode number
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
    download_dir = create_download_directory()
    
    print("\n" + "=" * 60)
    print("STARTING DOWNLOAD PROCESS")
    print("=" * 60)
    
    # Step 4: Download episodes
    successful_downloads = 0
    
    for episode_num in range(start_episode, start_episode + num_episodes):
        print(f"\n[*] Processing Episode {episode_num} of {start_episode + num_episodes - 1}")
        
        # Generate episode URL
        episode_url = get_episode_url(base_url, episode_num)
        
        # Add ?do=watch parameter if not present
        if '?do=watch' not in episode_url:
            episode_url += '?do=watch'
        
        print(f"    Episode URL: {episode_url}")
        
        # Extract video URL
        video_url = extract_video_url(episode_url, session)
        
        if not video_url:
            print(f"    [X] Skipping Episode {episode_num} - No video URL found")
            continue
        
        # Generate filename
        filename = f"The_Protector_S01E{episode_num:02d}.mp4"
        filepath = os.path.join(download_dir, filename)
        
        # Download video
        if download_video(video_url, filepath, session):
            successful_downloads += 1
        
        # Small delay to be respectful to the server
        time.sleep(1)
    
    # Step 5: Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Total episodes processed: {num_episodes}")
    print(f"Successfully downloaded: {successful_downloads}")
    print(f"Failed: {num_episodes - successful_downloads}")
    print(f"Episodes saved in: {os.path.abspath(download_dir)}")
    
    if successful_downloads > 0:
        print("\n[✓] Download process completed successfully!")
    else:
        print("\n[!] No episodes were downloaded. Please check the URLs and try again.")
    
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
