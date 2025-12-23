#!/usr/bin/env python3
"""
Jhanak Downloader - Optimized for speed with LOWEST quality
"""

import yt_dlp
import requests
import time
import os
import sys
import subprocess
from urllib.parse import urlparse
import re

class JhanakFastDownloader:
    def __init__(self, start_ep=240, end_ep=340, quality='lowest'):
        self.start_ep = start_ep
        self.end_ep = end_ep
        self.quality = quality
        self.base_url_template = "https://www.goryh.one/مسلسل-جاناك-الحلقة-{}-مترجمة/"
        
        # Check for required dependencies
        self.check_dependencies()
        
        # Setup session
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.goryh.one/',
        }
        
        # OPTIMIZED YT-DLP SETTINGS FOR SPEED - LOWEST QUALITY
        self.ydl_opts = {
            'outtmpl': 'Jhanak_Episodes/Episode_%(episode_number)03d.%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            'retries': 20,  # More retries for reliability
            'fragment_retries': 20,
            'skip_unavailable_fragments': True,
            'continuedl': True,
            'noprogress': False,
            'sleep_interval': 2,
            'max_sleep_interval': 5,
            
            # CRITICAL: Force ffmpeg for decryption (much faster)
            'external_downloader': 'ffmpeg',
            'external_downloader_args': {
                'ffmpeg_i': ['-protocol_whitelist', 'file,http,https,tcp,tls,crypto']
            },
            
            # QUALITY SETTINGS - Force LOWEST quality
            'format': 'worst',  # This selects the worst quality available
            'format_sort': ['size', 'tbr', 'res'],  # Sort by smallest size
            
            # SPEED OPTIMIZATIONS
            'concurrent_fragment_downloads': 8,  # Download multiple fragments at once
            'throttledratelimit': 0,  # No limit
            'buffer_size': 4096 * 1024,  # Larger buffer
            
            # FIX for 99.5% stuck issue
            'http_chunk_size': 10485760,  # 10MB chunks
            'continuedl': True,
            'no_part': True,  # Don't use .part files
            
            # HEADERS for better compatibility
            'http_headers': self.headers,
            
            # POSTPROCESSOR - merge with ffmpeg
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            
            # EXTRACTOR SETTINGS
            'extractor_args': {
                'hlsnative': {
                    'prefer_native': True,
                },
                'generic': {
                    'no-check-certificate': True,
                }
            },
            
            # VERBOSE for debugging
            'verbose': False,
        }
    
    def check_dependencies(self):
        """Check and install required dependencies"""
        print("Checking dependencies...")
        
        # Check ffmpeg
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            print("✅ ffmpeg is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ ffmpeg is NOT installed - decryption will be VERY slow")
            print("   Install ffmpeg for MUCH faster downloads:")
            print("   Windows: Download from https://ffmpeg.org/download.html")
            print("   Linux: sudo apt install ffmpeg")
            print("   Mac: brew install ffmpeg")
            print("\n   Or install via pip: pip install ffmpeg-python")
        
        # Check pycryptodomex
        try:
            import Cryptodome
            print("✅ pycryptodomex is installed")
        except ImportError:
            print("⚠️  pycryptodomex not installed - installing now...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodomex"])
                print("✅ Installed pycryptodomex")
            except:
                print("❌ Failed to install pycryptodomex")
                print("   Manual install: pip install pycryptodomex")
    
    def extract_video_url(self, page_url):
        """Extract video URL from page"""
        try:
            print(f"🔍 Analyzing: {page_url}")
            response = self.session.get(page_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                return None
            
            content = response.text
            
            # Look for m3u8 URLs first (HLS streams)
            patterns = [
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                r'src=["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'file["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'(https?://[^\s"\']*vidlo\.us[^\s"\']*)',
                r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Make URL complete
                    if match.startswith('//'):
                        video_url = 'https:' + match
                    elif match.startswith('/'):
                        parsed = urlparse(page_url)
                        video_url = f"{parsed.scheme}://{parsed.netloc}{match}"
                    else:
                        video_url = match
                    
                    print(f"✅ Found: {video_url[:80]}...")
                    return video_url
            
            print("❌ No video URL found")
            return None
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def download_episode_fast(self, episode_num):
        """Download episode with optimized settings"""
        print(f"\n{'='*60}")
        print(f"🎬 DOWNLOADING EPISODE {episode_num} - LOWEST QUALITY")
        print(f"{'='*60}")
        
        # Get page URL
        page_url = self.base_url_template.format(episode_num)
        
        # Extract video URL
        video_url = self.extract_video_url(page_url)
        
        if not video_url:
            print(f"❌ No video URL for episode {episode_num}")
            return False
        
        # Create episode-specific options
        episode_opts = self.ydl_opts.copy()
        episode_opts['outtmpl'] = f'Jhanak_Episodes/Episode_{episode_num:03d}.%(ext)s'
        
        # Different settings for m3u8 vs direct mp4
        if '.m3u8' in video_url.lower():
            print(f"📦 HLS stream detected - using optimized settings")
            episode_opts.update({
                'hls_prefer_native': True,
                'hls_use_mpegts': False,
                'external_downloader': 'ffmpeg',
                'external_downloader_args': {
                    'ffmpeg_i': ['-protocol_whitelist', 'file,http,https,tcp,tls,crypto']
                },
                # Force LOWEST quality for HLS
                'format': 'worst',
            })
        else:
            print(f"📦 Direct video detected")
            # For direct videos, use worst quality
            episode_opts.update({
                'format': 'worst',
            })
        
        try:
            print(f"⏬ Starting download...")
            start_time = time.time()
            
            with yt_dlp.YoutubeDL(episode_opts) as ydl:
                # Add progress hook for better feedback
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        percent = d.get('_percent_str', '0.0%').strip()
                        speed = d.get('_speed_str', 'N/A')
                        eta = d.get('_eta_str', 'N/A')
                        print(f"\r📥 Progress: {percent} at {speed} - ETA: {eta}", end='', flush=True)
                    elif d['status'] == 'finished':
                        print(f"\r✅ Download complete! Finalizing...")
                
                episode_opts['progress_hooks'] = [progress_hook]
                
                # Download
                info = ydl.extract_info(video_url, download=True)
                
                if info:
                    download_time = time.time() - start_time
                    
                    # Get actual downloaded file info
                    files = os.listdir('Jhanak_Episodes')
                    episode_files = [f for f in files if f.startswith(f'Episode_{episode_num:03d}')]
                    
                    if episode_files:
                        file_path = f'Jhanak_Episodes/{episode_files[0]}'
                        file_size = os.path.getsize(file_path) / (1024*1024)  # MB
                        
                        print(f"\n{'='*40}")
                        print(f"✅ SUCCESS: Episode {episode_num}")
                        print(f"📁 File: {episode_files[0]}")
                        print(f"📊 Size: {file_size:.2f} MB")
                        print(f"⏱️  Time: {download_time:.1f} seconds")
                        if download_time > 0:
                            print(f"⚡ Speed: {file_size/download_time:.2f} MB/s")
                        print(f"{'='*40}")
                        
                        return True
                    else:
                        print(f"❌ Downloaded but file not found")
                        return False
                else:
                    print(f"❌ Download failed")
                    return False
                    
        except Exception as e:
            print(f"\n❌ Error downloading: {e}")
            return False
    
    def download_all(self):
        """Download all episodes in range"""
        print(f"\n🚀 Starting batch download: Episodes {self.start_ep} to {self.end_ep}")
        print(f"🎯 Target quality: LOWEST (Smallest file size)")
        
        # Create folder
        os.makedirs('Jhanak_Episodes', exist_ok=True)
        
        successful = []
        failed = []
        
        for episode_num in range(self.start_ep, self.end_ep + 1):
            print(f"\n📊 Progress: Episode {episode_num} of {self.end_ep}")
            print(f"   Successful: {len(successful)}, Failed: {len(failed)}")
            
            # Check if already downloaded
            existing_files = [f for f in os.listdir('Jhanak_Episodes') 
                            if f.startswith(f'Episode_{episode_num:03d}')]
            if existing_files:
                print(f"⏩ Already exists: {existing_files[0]}")
                successful.append(episode_num)
                continue
            
            # Download episode
            result = self.download_episode_fast(episode_num)
            
            if result:
                successful.append(episode_num)
            else:
                failed.append(episode_num)
            
            # Wait between episodes (shorter wait for speed)
            wait_time = 3
            if len(failed) > 0 and len(failed) % 3 == 0:
                wait_time = 10  # Longer wait after failures
            
            if episode_num < self.end_ep:
                print(f"⏳ Waiting {wait_time}s before next episode...")
                time.sleep(wait_time)
        
        # Summary
        print(f"\n{'='*60}")
        print("📊 FINAL SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Successful: {len(successful)} episodes")
        print(f"❌ Failed: {len(failed)} episodes")
        
        if successful:
            print(f"📋 Downloaded: {sorted(successful)}")
        
        if failed:
            print(f"📋 Failed: {sorted(failed)}")
            print(f"\n💡 Suggestions for failed episodes:")
            print("   1. Try manual download with yt-dlp command:")
            print(f"      yt-dlp --format 'worst' 'URL_HERE'")
            print("   2. Try different time (server might be busy)")
            print("   3. Check if episode actually exists on site")
        
        return successful, failed

# SIMPLE COMMAND-LINE INTERFACE
def main():
    print("\n" + "="*60)
    print("JHANAK FAST DOWNLOADER - LOWEST QUALITY OPTIMIZED")
    print("="*60)
    
    print("\nQuick setup:")
    print("1. First, install ffmpeg for FAST decryption")
    print("2. Choose download option below")
    
    print("\nOptions:")
    print("1. Test single episode (recommended)")
    print("2. Download range 240-340")
    print("3. Custom range")
    print("4. Install dependencies")
    print("5. Exit")
    
    choice = input("\nSelect (1-5): ").strip()
    
    if choice == '1':
        ep = input("Episode number to test: ").strip()
        try:
            downloader = JhanakFastDownloader(int(ep), int(ep))
            downloader.download_episode_fast(int(ep))
        except ValueError:
            print("Invalid episode number")
    
    elif choice == '2':
        downloader = JhanakFastDownloader(240, 340)
        downloader.download_all()
    
    elif choice == '3':
        try:
            start = int(input("Start episode: "))
            end = int(input("End episode: "))
            downloader = JhanakFastDownloader(start, end)
            downloader.download_all()
        except ValueError:
            print("Invalid numbers")
    
    elif choice == '4':
        print("\nInstalling dependencies...")
        os.system(f"{sys.executable} -m pip install yt-dlp requests pycryptodomex")
        print("\nFor ffmpeg:")
        print("Windows: Download from https://ffmpeg.org/download.html")
        print("Linux: sudo apt install ffmpeg")
        print("Mac: brew install ffmpeg")
        print("\nOr install ffmpeg-python: pip install ffmpeg-python")
    
    elif choice == '5':
        print("Exiting...")
        return
    
    else:
        print("Invalid choice")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    # Auto-install basic requirements
    try:
        import yt_dlp
        import requests
    except ImportError:
        print("Installing basic requirements...")
        os.system(f"{sys.executable} -m pip install yt-dlp requests")
        print("Please run the script again.")
        sys.exit(1)
    
    main()