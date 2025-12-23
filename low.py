#!/usr/bin/env python3
"""
Ahuak.tv Downloader using FlareSolverr (No ChromeDriver needed)
"""

import requests
import re
import sys
import yt_dlp
import json
from pathlib import Path
import time

class AhuakDownloader:
    def __init__(self):
        self.flaresolverr_url = "http://localhost:8191/v1"
        self.download_dir = Path("downloads")
        self.download_dir.mkdir(exist_ok=True)
        
    def check_flaresolverr(self):
        """Check if FlareSolverr is running"""
        try:
            response = requests.get(f"{self.flaresolverr_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_flaresolverr(self):
        """Try to start FlareSolverr if not running"""
        print("FlareSolverr not running. Attempting to start...")
        
        # Check if Docker is installed
        try:
            import subprocess
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print("Docker found. Starting FlareSolverr container...")
                
                # Run FlareSolverr in background
                subprocess.Popen([
                    "docker", "run", "-d",
                    "--name=flaresolverr",
                    "-p", "8191:8191",
                    "-e", "LOG_LEVEL=info",
                    "--restart", "unless-stopped",
                    "ghcr.io/flaresolverr/flaresolverr:latest"
                ])
                
                print("Waiting for FlareSolverr to start (15 seconds)...")
                time.sleep(15)
                return self.check_flaresolverr()
        except Exception as e:
            print(f"Cannot start FlareSolverr automatically: {e}")
        
        print("\n" + "="*60)
        print("MANUAL SETUP REQUIRED:")
        print("="*60)
        print("1. Install Docker: https://docs.docker.com/get-docker/")
        print("2. Run FlareSolverr manually:")
        print("   docker run -d --name=flaresolverr -p 8191:8191 \\")
        print("     -e LOG_LEVEL=info --restart unless-stopped \\")
        print("     ghcr.io/flaresolverr/flaresolverr:latest")
        print("3. Run this script again")
        print("="*60)
        return False
    
    def bypass_cloudflare(self, url, session_name="ahuak_session"):
        """Use FlareSolverr to bypass Cloudflare"""
        
        # First, create or reuse session
        session_payload = {
            "cmd": "sessions.create",
            "session": session_name
        }
        
        try:
            requests.post(self.flaresolverr_url, json=session_payload, timeout=10)
        except:
            pass  # Session might already exist
        
        # Now get the page through Cloudflare
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000,
            "session": session_name,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        }
        
        try:
            print(f"Bypassing Cloudflare for: {url}")
            response = requests.post(self.flaresolverr_url, json=payload, timeout=65)
            result = response.json()
            
            if result.get("status") == "ok":
                print("✓ Cloudflare bypass successful!")
                return result["solution"]
            else:
                print(f"✗ FlareSolverr error: {result.get('message')}")
                return None
                
        except Exception as e:
            print(f"✗ Error connecting to FlareSolverr: {e}")
            return None
    
    def extract_video_url(self, html_content, url):
        """Extract video URL from page HTML"""
        
        # Save HTML for debugging
        debug_file = self.download_dir / "debug_page.html"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✓ Saved page HTML to: {debug_file}")
        
        # Pattern 1: Direct video URLs
        patterns = [
            r'src="(https?://[^"]+\.(mp4|m3u8|webm|flv)[^"]*)"',
            r"src='(https?://[^']+\.(mp4|m3u8|webm|flv)[^']*)'",
            r'file:\s*["\'](https?://[^"\']+)["\']',
            r'videoUrl:\s*["\'](https?://[^"\']+)["\']',
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'video src="([^"]+)"'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                video_url = matches[0][0] if isinstance(matches[0], tuple) else matches[0]
                print(f"✓ Found video URL with pattern: {pattern[:30]}...")
                return video_url
        
        # Pattern 2: Iframe sources
        iframe_pattern = r'<iframe[^>]+src="([^"]+)"'
        iframe_matches = re.findall(iframe_pattern, html_content)
        
        for iframe_url in iframe_matches:
            if any(x in iframe_url for x in ['youtube', 'vimeo', 'dailymotion', 'player']):
                print(f"✓ Found iframe URL: {iframe_url}")
                return iframe_url
        
        # Pattern 3: JSON data in script tags
        script_pattern = r'<script[^>]*>([^<]+)</script>'
        script_matches = re.findall(script_pattern, html_content)
        
        for script in script_matches:
            if 'http' in script and ('mp4' in script or 'm3u8' in script):
                # Try to find URLs in JavaScript
                url_pattern = r'(https?://[^\s"\']+\.(mp4|m3u8)[^\s"\']*)'
                url_matches = re.findall(url_pattern, script)
                if url_matches:
                    video_url = url_matches[0][0] if isinstance(url_matches[0], tuple) else url_matches[0]
                    print(f"✓ Found video URL in script")
                    return video_url
        
        print("✗ Could not find video URL in page")
        print("   Try opening debug_page.html in browser to inspect the page")
        return None
    
    def download_video(self, video_url, episode_num, referer=None):
        """Download video using yt-dlp"""
        
        print(f"\nStarting download for episode {episode_num}...")
        print(f"Video URL: {video_url[:100]}...")
        
        # Prepare yt-dlp options
        ydl_opts = {
            'outtmpl': str(self.download_dir / f'episode_{episode_num:03d}.%(ext)s'),
            'format': 'worst[ext=mp4]/worst',  # Lowest quality
            'quiet': False,
            'no_warnings': False,
            'progress_hooks': [self.progress_hook],
        }
        
        # Add headers if needed
        if referer:
            ydl_opts['http_headers'] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': referer,
                'Accept': '*/*',
            }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                if info:
                    filename = ydl.prepare_filename(info)
                    print(f"\n✓ Successfully downloaded: {filename}")
                    return True
            return False
            
        except Exception as e:
            print(f"✗ Download error: {e}")
            
            # Try alternative: direct download
            return self.direct_download(video_url, episode_num, referer)
    
    def direct_download(self, video_url, episode_num, referer=None):
        """Fallback direct download"""
        print("Trying direct download...")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            
            if referer:
                headers['Referer'] = referer
            
            response = requests.get(video_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            ext = 'mp4'
            if 'webm' in content_type:
                ext = 'webm'
            elif 'x-matroska' in content_type:
                ext = 'mkv'
            elif 'mpegurl' in content_type or '.m3u8' in video_url:
                ext = 'm3u8'
            
            filename = self.download_dir / f'episode_{episode_num:03d}_direct.{ext}'
            
            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"Downloading: {percent:.1f}% ({downloaded/1024/1024:.1f} MB)", end='\r')
            
            print(f"\n✓ Direct download completed: {filename}")
            return True
            
        except Exception as e:
            print(f"✗ Direct download failed: {e}")
            return False
    
    def progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            print(f"Progress: {percent} | Speed: {speed} | ETA: {eta}", end='\r')
        elif d['status'] == 'finished':
            print(f"\n✓ Download completed successfully")
    
    def process_episode(self, episode_url, episode_num):
        """Process a single episode"""
        print(f"\n{'='*60}")
        print(f"EPISODE {episode_num}")
        print(f"{'='*60}")
        
        # Bypass Cloudflare
        solution = self.bypass_cloudflare(episode_url)
        if not solution:
            return False
        
        # Extract HTML and cookies
        html_content = solution.get("response", "")
        cookies = solution.get("cookies", [])
        
        if not html_content:
            print("✗ No HTML content received")
            return False
        
        # Extract video URL
        video_url = self.extract_video_url(html_content, episode_url)
        
        if video_url:
            # Download video
            success = self.download_video(video_url, episode_num, episode_url)
            return success
        else:
            print("✗ Could not extract video URL")
            return False
    
    def run(self):
        """Main function"""
        print("="*60)
        print("AHUAK.TV DOWNLOADER - FLARESOLVERR EDITION")
        print("="*60)
        
        # Check if FlareSolverr is running
        if not self.check_flaresolverr():
            if not self.start_flaresolverr():
                return
        
        # Get user input
        print("\nEnter series information:")
        base_url = input("Series URL (e.g., https://dal.ahwaktv.net/watch.php?vid=...): ").strip()
        
        if not base_url.startswith("http"):
            print("Error: Please enter a valid URL")
            return
        
        try:
            episode_count = int(input("Number of episodes: "))
        except ValueError:
            print("Error: Please enter a number")
            return
        
        # Process episodes
        successful = 0
        
        for i in range(1, episode_count + 1):
            # Construct episode URL
            if "vid=" in base_url:
                # Parse the video ID and increment
                import re
                match = re.search(r'vid=([a-f0-9]+)', base_url)
                if match:
                    base_id = match.group(1)
                    try:
                        # Try to increment hex ID
                        new_id = hex(int(base_id, 16) + (i-1))[2:]
                        episode_url = base_url.replace(base_id, new_id)
                    except:
                        # Fallback: just use the base URL
                        episode_url = base_url
                else:
                    episode_url = base_url
            else:
                episode_url = f"{base_url}/{i}"
            
            print(f"\nProcessing: {episode_url}")
            
            if self.process_episode(episode_url, i):
                successful += 1
            
            # Delay between episodes
            if i < episode_count:
                delay = 5
                print(f"\nWaiting {delay} seconds before next episode...")
                time.sleep(delay)
        
        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total episodes: {episode_count}")
        print(f"Successfully downloaded: {successful}")
        print(f"Download directory: {self.download_dir.absolute()}")
        print(f"\nTo download more episodes, run the script again.")

def main():
    """Entry point"""
    
    # Check dependencies
    try:
        import requests
        import yt_dlp
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "yt-dlp"])
        print("Please run the script again.")
        return
    
    # Run downloader
    downloader = AhuakDownloader()
    downloader.run()

if __name__ == "__main__":
    main()
