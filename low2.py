#!/usr/bin/env python3
"""
Enhanced Video Downloader for 3seq.com
Direct 240p download with smart compression during download
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

def install_requirements():
    """Install required packages"""
    print("[*] Checking system requirements...")
    
    packages = ['requests', 'beautifulsoup4']
    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ✗ Installing {pkg}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
    
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("  ✓ yt-dlp")
    except:
        print("  ✗ Installing yt-dlp...")
        subprocess.run(['pip', 'install', 'yt-dlp'], check=True)
    
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("  ✓ ffmpeg")
    except:
        print("  ✗ Installing ffmpeg...")
        subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], check=True)

def discover_final_url(initial_url, max_retries=3):
    """Discover the final URL after dynamic transformation"""
    print(f"[*] Discovering final URL...")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for attempt in range(max_retries):
        try:
            response = session.get(initial_url, timeout=10, allow_redirects=True)
            current_url = response.url
            
            if current_url != initial_url:
                print(f"[*] Redirected to: {current_url}")
                return current_url
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for meta refresh
            meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if meta_refresh and 'url=' in meta_refresh.get('content', ''):
                new_url = meta_refresh['content'].split('url=')[-1]
                if new_url:
                    final_url = urljoin(initial_url, new_url)
                    print(f"[*] Meta refresh to: {final_url}")
                    return final_url
            
            # Look for canonical URL
            canonical = soup.find('link', {'rel': 'canonical'})
            if canonical and canonical.get('href'):
                final_url = canonical['href']
                if final_url != initial_url:
                    print(f"[*] Canonical URL: {final_url}")
                    return final_url
            
            time.sleep(2)
                
        except Exception as e:
            print(f"[!] Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    
    return initial_url

def extract_video_embed_url(page_url):
    """Extract video embed URL from watch page"""
    print(f"[*] Extracting video URL...")
    
    try:
        if '?do=watch' not in page_url:
            if not page_url.endswith('/'):
                page_url += '/'
            watch_url = page_url + '?do=watch'
        else:
            watch_url = page_url
        
        response = requests.get(watch_url, headers=HEADERS, timeout=15)
        
        # Method 1: Direct m3u8
        m3u8_pattern = r'(https?://[^\s"\']+\.m3u8[^\s"\']*)'
        m3u8_matches = re.findall(m3u8_pattern, response.text)
        for match in m3u8_matches:
            if 'cdn-vids.xyz' in match:
                print(f"[*] Found m3u8: {match}")
                return match
        
        # Method 2: Iframe
        soup = BeautifulSoup(response.text, 'html.parser')
        iframe = soup.find('iframe', {'src': re.compile(r'vidsp\.net')})
        if iframe:
            iframe_src = iframe.get('src')
            if iframe_src:
                print(f"[*] Found iframe: {iframe_src}")
                return iframe_src
        
        return None
        
    except Exception as e:
        print(f"[!] Error extracting video: {e}")
        return None

def get_available_qualities(video_url):
    """Check available qualities for the video"""
    print(f"[*] Checking available qualities...")
    
    try:
        # Use yt-dlp to list formats
        cmd = [
            'yt-dlp',
            '--list-formats',
            '--quiet',
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        qualities = []
        lines = result.stdout.split('\n')
        
        for line in lines:
            if 'x' in line and ('mp4' in line.lower() or 'm3u8' in line.lower()):
                # Extract quality info
                if '240' in line:
                    qualities.append('240p')
                elif '360' in line:
                    qualities.append('360p')
                elif '480' in line:
                    qualities.append('480p')
                elif '720' in line:
                    qualities.append('720p')
                elif '1080' in line:
                    qualities.append('1080p')
        
        if qualities:
            print(f"[*] Available qualities: {', '.join(set(qualities))}")
        else:
            print("[*] Could not determine available qualities")
        
        return list(set(qualities))
        
    except Exception as e:
        print(f"[!] Error checking qualities: {e}")
        return []

def download_direct_240p(video_url, output_file):
    """
    Download video and convert to 240p DURING download (piped ffmpeg)
    This is the fastest way to get 240p
    """
    print(f"[*] Downloading and converting to 240p in real-time...")
    
    # Step 1: Download with yt-dlp and pipe to ffmpeg
    # We'll download lowest quality and convert during download
    
    # First, try to find the format ID for lowest quality
    try:
        cmd_list = ['yt-dlp', '-F', '--quiet', video_url]
        result = subprocess.run(cmd_list, capture_output=True, text=True)
        
        format_id = None
        for line in result.stdout.split('\n'):
            if ('worst' in line.lower() or '144' in line or '240' in line or 
                '360' in line or '480' in line):
                parts = line.split()
                if parts and parts[0].isdigit():
                    format_id = parts[0]
                    print(f"[*] Selected format ID: {format_id}")
                    break
        
        if not format_id:
            format_id = 'worst'
            
    except:
        format_id = 'worst'
    
    # Build the piped command
    # yt-dlp downloads -> pipes to -> ffmpeg converts to 240p
    ytdlp_cmd = [
        'yt-dlp',
        '-f', format_id,
        '--quiet',
        '--no-warnings',
        '-o', '-',  # Output to stdout
        video_url
    ]
    
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', 'pipe:0',  # Input from stdin
        '-vf', 'scale=-2:240',
        '-c:v', 'libx264',
        '-preset', 'fast',  # Fast compression
        '-crf', '28',       # Good quality for 240p
        '-c:a', 'aac',
        '-b:a', '64k',
        '-y',
        output_file
    ]
    
    print(f"[*] Executing: yt-dlp | ffmpeg -> {output_file}")
    
    try:
        # Start yt-dlp process
        ytdlp_process = subprocess.Popen(
            ytdlp_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Start ffmpeg process with piped input
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=ytdlp_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for both processes
        ytdlp_process.wait()
        ffmpeg_process.wait()
        
        if ffmpeg_process.returncode == 0 and os.path.exists(output_file):
            size_mb = os.path.getsize(output_file) / (1024*1024)
            print(f"[✓] Download complete: {size_mb:.1f} MB (240p)")
            return True
        else:
            print(f"[!] Piped download failed")
            return False
            
    except Exception as e:
        print(f"[!] Error in piped download: {e}")
        return False

def download_and_compress_separate(video_url, output_file):
    """
    Alternative: Download first, then compress (more reliable)
    """
    print(f"[*] Downloading first, then compressing to 240p...")
    
    temp_file = output_file.replace('.mp4', '_temp.mp4')
    
    # Download lowest available quality
    download_cmd = [
        'yt-dlp',
        '-f', 'worst',
        '--merge-output-format', 'mp4',
        '--quiet',
        '--no-warnings',
        '-o', temp_file,
        video_url
    ]
    
    # Compress to 240p
    compress_cmd = [
        'ffmpeg',
        '-i', temp_file,
        '-vf', 'scale=-2:240',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '28',
        '-c:a', 'aac',
        '-b:a', '64k',
        '-y',
        output_file
    ]
    
    try:
        # Download
        print("[*] Downloading source video...")
        dl_result = subprocess.run(download_cmd, capture_output=True, text=True)
        
        if dl_result.returncode != 0 or not os.path.exists(temp_file):
            print(f"[!] Download failed: {dl_result.stderr[:200]}")
            return False
        
        source_size = os.path.getsize(temp_file) / (1024*1024)
        print(f"[*] Downloaded: {source_size:.1f} MB")
        
        # Compress
        print("[*] Compressing to 240p...")
        comp_result = subprocess.run(compress_cmd, capture_output=True, text=True)
        
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        if comp_result.returncode == 0 and os.path.exists(output_file):
            final_size = os.path.getsize(output_file) / (1024*1024)
            reduction = ((source_size - final_size) / source_size) * 100
            print(f"[✓] Compression complete: {final_size:.1f} MB ({reduction:.1f}% reduction)")
            return True
        else:
            print(f"[!] Compression failed: {comp_result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"[!] Error: {e}")
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False

def process_episode_fast(base_url, series_pattern, episode_num, download_dir):
    """Fast processing with direct 240p output"""
    print(f"\n{'='*60}")
    print(f"[*] PROCESSING EPISODE {episode_num:02d}")
    print('='*60)
    
    try:
        # Build URL
        episode_str = f"{episode_num:02d}"
        if 's01e' in series_pattern:
            initial_url = f"{base_url}/{series_pattern}{episode_str}"
        else:
            initial_url = f"{base_url}/{series_pattern}{episode_num}"
        
        print(f"[*] URL: {initial_url}")
        
        # Get final URL
        final_url = discover_final_url(initial_url)
        
        # Extract video URL
        video_url = extract_video_embed_url(final_url)
        if not video_url:
            print(f"[!] Failed to extract video URL")
            return False
        
        print(f"[*] Video source: {video_url[:80]}...")
        
        # Create output file
        output_file = f"{download_dir}/الحلقة_{episode_str}.mp4"
        
        # Method 1: Try piped download (fastest)
        if download_direct_240p(video_url, output_file):
            return True
        else:
            # Method 2: Try separate download+compress
            print("[*] Falling back to separate download+compress...")
            return download_and_compress_separate(video_url, output_file)
        
    except Exception as e:
        print(f"[!] Error processing episode {episode_num}: {e}")
        return False

def main_fast():
    """Fast downloader with guaranteed 240p output"""
    print("="*60)
    print("FAST 240p VIDEO DOWNLOADER")
    print("Guaranteed 240p output with smart compression")
    print("="*60)
    
    # Install requirements
    install_requirements()
    
    # Get user input
    print("\n[*] Enter download parameters:")
    
    base_url = input("Base URL [https://x.3seq.com/video]: ").strip()
    if not base_url:
        base_url = "https://x.3seq.com/video"
    
    default_pattern = "modablaj-sarmasik-zamani-episode-"
    series = input(f"Series pattern [{default_pattern}]: ").strip()
    if not series:
        series = default_pattern
    
    try:
        start_ep = int(input("Start episode [1]: ").strip() or "1")
        end_ep = int(input("End episode [10]: ").strip() or "10")
    except:
        print("[!] Invalid episode numbers")
        return
    
    # Create download directory
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    series_name = series.split('-')[1] if '-' in series else "series"
    download_dir = f"{series_name}_240p_{timestamp}"
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print("[*] STARTING 240p DOWNLOAD")
    print(f"    Series: {series}")
    print(f"    Episodes: {start_ep} to {end_ep}")
    print(f"    Quality: 240p (guaranteed)")
    print(f"    Output: {download_dir}/")
    print('='*60)
    
    # Process episodes
    successful = 0
    failed = []
    
    for ep in range(start_ep, end_ep + 1):
        if process_episode_fast(base_url, series, ep, download_dir):
            successful += 1
            print(f"[✓] Episode {ep} completed successfully")
        else:
            failed.append(ep)
            print(f"[!] Episode {ep} failed")
        
        # Short delay
        if ep < end_ep:
            time.sleep(2)
    
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
        if total_size > 0:
            print(f"[*] Total size: {total_size:.1f} MB")
            if successful > 0:
                avg_size = total_size / successful
                print(f"[*] Average per episode: {avg_size:.1f} MB")
    except:
        pass
    
    print('='*60)
    
    # Show recommended command for manual download
    if failed:
        print("\n[*] For failed episodes, try manual download:")
        print(f"    yt-dlp -f worst 'VIDEO_URL' --exec 'ffmpeg -i {{}} -vf scale=-2:240 {{}}_240p.mp4'")

def quick_download_single():
    """Quick download for single episode"""
    print("\n[*] Quick single episode download")
    url = input("Enter full episode URL: ").strip()
    
    if not url.startswith('http'):
        print("[!] Invalid URL")
        return
    
    # Extract series name for filename
    series_match = re.search(r'/([^/]+)-episode-', url)
    if series_match:
        series_name = series_match.group(1)
    else:
        series_name = "episode"
    
    output_file = f"{series_name}_240p.mp4"
    
    print(f"\n[*] Downloading to: {output_file}")
    
    # Try direct piped download
    if download_direct_240p(url, output_file):
        size = os.path.getsize(output_file) / (1024*1024)
        print(f"\n[✓] Success! File: {output_file} ({size:.1f} MB)")
    else:
        print(f"\n[!] Failed to download")

if __name__ == "__main__":
    print("="*60)
    print("VIDEO DOWNLOADER - 240p GUARANTEED")
    print("="*60)
    
    print("\nOptions:")
    print("  1. Download multiple episodes")
    print("  2. Quick single episode download")
    print("  3. Exit")
    
    choice = input("\nSelect option [1]: ").strip() or "1"
    
    if choice == "1":
        main_fast()
    elif choice == "2":
        quick_download_single()
    else:
        print("[*] Goodbye!")
