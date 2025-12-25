#!/usr/bin/env python3
"""
Enhanced HLS Video Downloader for 3seq website
Handles redirects, random codes, and HLS stream extraction
"""

import subprocess
import sys
import re
import os
import time
import requests
from urllib.parse import urljoin, urlparse, parse_qs
import json

def check_dependencies():
    """Check if required tools are installed"""
    print("[*] Checking dependencies...")
    
    # Check for yt-dlp
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("[✓] yt-dlp is installed")
        return True
    except:
        print("[X] yt-dlp is not installed.")
        print("[*] Please install it with: pip install yt-dlp")
        return False

def get_final_url_with_session(session, initial_url):
    """
    Get the final URL after all redirects with a session
    Returns the final URL and response history
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
    }
    
    try:
        print(f"[*] Requesting: {initial_url}")
        response = session.get(initial_url, headers=headers, allow_redirects=True, timeout=15)
        
        final_url = response.url
        print(f"[✓] Final URL after redirects: {final_url}")
        
        # Check if we got a valid HTML page
        if 'text/html' in response.headers.get('Content-Type', ''):
            print(f"[*] Got HTML page, status: {response.status_code}")
        else:
            print(f"[*] Got content type: {response.headers.get('Content-Type', 'unknown')}")
        
        return final_url, response
        
    except Exception as e:
        print(f"[X] Error getting final URL: {e}")
        return initial_url, None

def extract_random_code_from_url(url):
    """Extract the random code (like -cksi) from the URL"""
    pattern = r'-([a-z0-9]{4})(?:/|$)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def extract_m3u8_from_response(response, final_url):
    """
    Extract m3u8 URL from the response content
    Uses multiple strategies to find HLS streams
    """
    if not response:
        return None
    
    content = response.text
    found_urls = []
    
    print(f"[*] Analyzing page content ({len(content)} characters)...")
    
    # Strategy 1: Look for m3u8 URLs in the HTML
    m3u8_patterns = [
        r'"([^"]+\.m3u8[^"]*)"',
        r"'([^']+\.m3u8[^']*)'",
        r'src\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'url\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'videoUrl\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
    ]
    
    for pattern in m3u8_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if '.m3u8' in match.lower():
                # Convert to absolute URL if relative
                if match.startswith('//'):
                    full_url = 'https:' + match
                elif match.startswith('/'):
                    full_url = urljoin(final_url, match)
                elif not match.startswith('http'):
                    full_url = urljoin(final_url, match)
                else:
                    full_url = match
                
                if full_url not in found_urls:
                    found_urls.append(full_url)
    
    # Strategy 2: Look for video player configurations
    # Common video players like JWPlayer, VideoJS, etc.
    player_patterns = [
        r'{"file":"([^"]+\.m3u8[^"]*)"',
        r"'file'\s*:\s*'([^']+\.m3u8[^']*)'",
        r'playlist\s*:\s*\[[^\]]*"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'sources\s*:\s*\[[^\]]*"src"\s*:\s*"([^"]+\.m3u8[^"]*)"',
    ]
    
    for pattern in player_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if '.m3u8' in match.lower():
                if match.startswith('//'):
                    full_url = 'https:' + match
                elif match.startswith('/'):
                    full_url = urljoin(final_url, match)
                elif not match.startswith('http'):
                    full_url = urljoin(final_url, match)
                else:
                    full_url = match
                
                if full_url not in found_urls:
                    found_urls.append(full_url)
    
    # Strategy 3: Look for ts segments and construct m3u8 URL
    ts_patterns = [
        r'(https?://[^/]+/[^/]+/)[^/]+\.ts',
        r'(https?://[^"\']+/[^"\']+/)[^"\']+\.ts',
    ]
    
    for pattern in ts_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for base_url in matches:
            # Try common m3u8 filenames
            possible_files = ['master.m3u8', 'index.m3u8', 'playlist.m3u8', 'video.m3u8', 'stream.m3u8']
            for m3u8_file in possible_files:
                test_url = urljoin(base_url, m3u8_file)
                if test_url not in found_urls:
                    found_urls.append(test_url)
    
    # Remove duplicates
    found_urls = list(set(found_urls))
    
    if found_urls:
        print(f"[✓] Found {len(found_urls)} potential m3u8 URLs")
        
        # Prioritize URLs that contain quality indicators or look like playlists
        prioritized_urls = []
        other_urls = []
        
        for url in found_urls:
            url_lower = url.lower()
            if any(keyword in url_lower for keyword in ['master', 'index', 'playlist', 'hls', 'stream']):
                prioritized_urls.append(url)
            else:
                other_urls.append(url)
        
        # Combine lists with priority ones first
        sorted_urls = prioritized_urls + other_urls
        
        # Return the first URL to test
        selected_url = sorted_urls[0]
        print(f"[*] Selected URL to test: {selected_url}")
        
        return selected_url
    
    print("[!] No m3u8 URLs found in page content")
    return None

def test_m3u8_url(session, url):
    """Test if an m3u8 URL is accessible and valid"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://x.3seq.com/',
        'Accept': '*/*',
    }
    
    try:
        print(f"[*] Testing m3u8 URL: {url}")
        response = session.head(url, headers=headers, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            print(f"[✓] m3u8 URL is accessible (status: {response.status_code})")
            
            # Also try to get a small part of the content to verify it's m3u8
            get_response = session.get(url, headers=headers, timeout=10, stream=True)
            first_chunk = get_response.iter_content(chunk_size=1024).__next__()
            
            if b'#EXTM3U' in first_chunk or b'.m3u8' in url.lower():
                print(f"[✓] Valid m3u8 content detected")
                return url
            else:
                print(f"[!] URL accessible but doesn't appear to be m3u8 content")
        else:
            print(f"[!] m3u8 URL returned status: {response.status_code}")
            
    except Exception as e:
        print(f"[!] Error testing m3u8 URL: {e}")
    
    return None

def discover_m3u8_url(session, watch_url):
    """
    Main function to discover m3u8 URL
    Tries multiple strategies
    """
    print(f"\n[*] Starting m3u8 discovery for: {watch_url}")
    
    # Strategy 1: Get final URL and extract from page
    final_url, response = get_final_url_with_session(session, watch_url)
    
    if response:
        # Try to extract m3u8 from the page content
        m3u8_url = extract_m3u8_from_response(response, final_url)
        
        if m3u8_url:
            # Test the URL
            tested_url = test_m3u8_url(session, m3u8_url)
            if tested_url:
                return tested_url
    
    # Strategy 2: Try to construct possible m3u8 URLs based on patterns
    print("[*] Trying URL pattern construction...")
    
    # Extract base path and construct possible CDN URLs
    parsed_url = urlparse(final_url)
    path_parts = parsed_url.path.split('/')
    
    # Look for the random code in the path
    random_code = None
    for part in path_parts:
        if len(part) == 4 and re.match(r'^[a-z0-9]{4}$', part):
            random_code = part
            break
    
    # Try different CDN domains and paths
    cdn_domains = [
        'https://s31.cdn-vids.xyz',
        'https://s32.cdn-vids.xyz',
        'https://s33.cdn-vids.xyz',
        'https://s34.cdn-vids.xyz',
        'https://cdn-vids.xyz',
    ]
    
    # If we found a random code, use it in the path
    path_guesses = []
    if random_code:
        path_guesses.append(f'/hls/{random_code}/master.m3u8')
        path_guesses.append(f'/hls/{random_code}/index.m3u8')
        path_guesses.append(f'/stream/{random_code}/playlist.m3u8')
    
    # Also try with the full episode name
    episode_name = path_parts[-1] if path_parts[-1] else path_parts[-2]
    if episode_name:
        path_guesses.append(f'/hls/{episode_name}/master.m3u8')
        path_guesses.append(f'/videos/{episode_name}/index.m3u8')
    
    # Test all combinations
    for cdn in cdn_domains:
        for path in path_guesses:
            test_url = cdn + path
            tested = test_m3u8_url(session, test_url)
            if tested:
                return tested
    
    # Strategy 3: Try to find m3u8 in common subdirectories
    print("[*] Trying common subdirectory patterns...")
    
    # Get the base URL without query parameters
    base_url = final_url.split('?')[0]
    
    common_paths = [
        '/hls/master.m3u8',
        '/hls/index.m3u8',
        '/stream/master.m3u8',
        '/stream/index.m3u8',
        '/video/master.m3u8',
        '/video/index.m3u8',
        '/playlist.m3u8',
        '/master.m3u8',
    ]
    
    for path in common_paths:
        test_url = base_url + path
        tested = test_m3u8_url(session, test_url)
        if tested:
            return tested
    
    print("[X] Could not discover m3u8 URL")
    return None

def download_with_ytdlp(m3u8_url, output_filename, quality='worst'):
    """Download HLS stream using yt-dlp"""
    try:
        print(f"\n[*] Starting download with yt-dlp...")
        print(f"    m3u8 URL: {m3u8_url}")
        print(f"    Output: {output_filename}")
        print(f"    Quality: {quality}")
        
        # Build yt-dlp command
        cmd = [
            'yt-dlp',
            '-f', quality,
            '--merge-output-format', 'mp4',
            '--add-header', 'Referer:https://x.3seq.com/',
            '--add-header', f'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--concurrent-fragments', '4',
            '--retries', '10',
            '--fragment-retries', '10',
            '--socket-timeout', '30',
            '-o', output_filename,
            m3u8_url
        ]
        
        print(f"[*] Running: {' '.join(cmd)}")
        
        # Run yt-dlp
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[✓] Download completed successfully!")
            return True
        else:
            print(f"[X] Download failed")
            if result.stderr:
                print(f"    Error: {result.stderr[:500]}")
            return False
            
    except Exception as e:
        print(f"[X] Error in download: {e}")
        return False

def process_episode(session, base_url, episode_num, quality='worst'):
    """Process a single episode"""
    print(f"\n{'='*70}")
    print(f"[*] PROCESSING EPISODE {episode_num}")
    print(f"{'='*70}")
    
    # Step 1: Generate the initial episode URL
    initial_url = generate_episode_url(base_url, episode_num)
    print(f"[*] Initial URL: {initial_url}")
    
    # Step 2: Construct watch URL (add /?do=watch)
    watch_url = initial_url + ('/?do=watch' if not initial_url.endswith('/') else '?do=watch')
    print(f"[*] Watch URL: {watch_url}")
    
    # Step 3: Discover m3u8 URL
    m3u8_url = discover_m3u8_url(session, watch_url)
    
    if not m3u8_url:
        print(f"[X] Failed to find m3u8 for episode {episode_num}")
        return False
    
    # Step 4: Download with yt-dlp
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
        # Try to find and replace the last number
        numbers = re.findall(r'\d+', base_url)
        if numbers:
            last_num = numbers[-1]
            return base_url[::-1].replace(last_num[::-1], str(episode_num)[::-1], 1)[::-1]
        else:
            return f"{base_url}-{episode_num}"

def main():
    print("="*70)
    print("ENHANCED HLS VIDEO DOWNLOADER FOR 3SEQ")
    print("="*70)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create a session for maintaining cookies and headers
    session = requests.Session()
    
    # Get user input
    print("\n" + "="*70)
    print("CONFIGURATION")
    print("="*70)
    
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
    print("1. Lowest quality (faster)")
    print("2. Best quality")
    print("3. 480p or lower")
    print("4. Manual format")
    
    quality_choice = input("Enter choice [default: 1]: ").strip()
    if quality_choice == '2':
        quality = 'best'
    elif quality_choice == '3':
        quality = 'best[height<=480]'
    elif quality_choice == '4':
        quality = input("Enter yt-dlp format: ").strip()
        if not quality:
            quality = 'worst'
    else:
        quality = 'worst'
    
    print(f"\n[*] Starting download of {num_episodes} episode(s)...")
    print(f"[*] Quality: {quality}")
    
    successful = 0
    failed_episodes = []
    
    for episode_num in range(start_episode, start_episode + num_episodes):
        try:
            if process_episode(session, base_url, episode_num, quality):
                successful += 1
                print(f"[✓] Successfully downloaded episode {episode_num}")
            else:
                failed_episodes.append(episode_num)
                print(f"[X] Failed to download episode {episode_num}")
        except Exception as e:
            print(f"[X] Error processing episode {episode_num}: {e}")
            failed_episodes.append(episode_num)
        
        # Delay between episodes
        if episode_num < start_episode + num_episodes - 1:
            print(f"\n[*] Waiting 3 seconds before next episode...")
            time.sleep(3)
    
    # Summary
    print("\n" + "="*70)
    print("DOWNLOAD SUMMARY")
    print("="*70)
    print(f"Total episodes: {num_episodes}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(failed_episodes)}")
    
    if failed_episodes:
        print(f"Failed episodes: {failed_episodes}")
    
    if successful == 0:
        print("\n[!] All downloads failed.")
        print("[*] Possible reasons:")
        print("    1. Website structure changed")
        print("    2. Need to update yt-dlp: pip install -U yt-dlp")
        print("    3. Videos might require authentication")
        print("    4. Try manual m3u8 discovery using browser Developer Tools")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Download interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        sys.exit(1)
