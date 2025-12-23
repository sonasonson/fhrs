#!/usr/bin/env python3
"""
Ahuak.tv Downloader - Simple Version (No Docker Required)
"""

import os
import sys
import time
import re
import requests
import json
from pathlib import Path

# Install required packages if missing
try:
    import yt_dlp
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "selenium", "webdriver-manager", "yt-dlp", "requests"])
    print("Please run the script again.")
    sys.exit(1)

class SimpleAhuakDownloader:
    def __init__(self):
        self.driver = None
        self.download_dir = Path("downloads")
        self.download_dir.mkdir(exist_ok=True)
        self.cookies_file = Path("ahuak_cookies.json")
        
    def setup_browser(self):
        """Setup Chrome browser manually"""
        print("Setting up Chrome browser...")
        
        options = Options()
        
        # إعدادات أساسية
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        
        # إعدادات المستخدم لجعل المتصفح يبدو طبيعياً
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # إعدادات التحميل
        prefs = {
            "download.default_directory": str(self.download_dir.absolute()),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_setting_values.automatic_downloads": 1,
        }
        options.add_experimental_option("prefs", prefs)
        
        # استخدم webdriver-manager لتثبيت ChromeDriver تلقائياً
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # إخفاء أثر السيلينيوم
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✓ Chrome browser ready")
            return True
        except Exception as e:
            print(f"✗ Failed to setup browser: {e}")
            return False
    
    def manual_cloudflare_bypass(self, url):
        """Open browser for manual Cloudflare bypass"""
        print("\n" + "="*60)
        print("MANUAL CLOUDFLARE BYPASS REQUIRED")
        print("="*60)
        
        print(f"\n1. Opening browser to: {url}")
        print("2. If you see Cloudflare verification:")
        print("   - Complete the CAPTCHA/check manually")
        print("   - Wait for page to load completely")
        print("   - You should see the video player")
        print("3. Return here and press Enter")
        print("\nOpening browser in 3 seconds...")
        
        time.sleep(3)
        
        # Open the URL
        self.driver.get(url)
        
        # Wait for user
        input("\nPress Enter AFTER you've completed Cloudflare verification and the video page is loaded...")
        
        # Wait a bit more
        time.sleep(5)
        
        # Check if still on Cloudflare
        page_source = self.driver.page_source.lower()
        if "cloudflare" in page_source or "challenge" in page_source:
            print("⚠ Still on Cloudflare page. Let's try again...")
            return self.manual_cloudflare_bypass(url)
        
        print("✓ Cloudflare bypassed!")
        
        # Save cookies for next time
        self.save_cookies(url)
        
        return True
    
    def save_cookies(self, url):
        """Save cookies for future use"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump({"url": url, "cookies": cookies}, f)
            print("✓ Cookies saved for next time")
        except Exception as e:
            print(f"Note: Could not save cookies: {e}")
    
    def load_cookies(self, url):
        """Load saved cookies"""
        if not self.cookies_file.exists():
            return False
        
        try:
            with open(self.cookies_file, 'r') as f:
                data = json.load(f)
            
            # Only use cookies if for same domain
            saved_url = data.get("url", "")
            if url in saved_url or saved_url in url:
                self.driver.get(url.split('?')[0] if '?' in url else url)
                time.sleep(2)
                
                for cookie in data.get("cookies", []):
                    try:
                        self.driver.add_cookie(cookie)
                    except:
                        continue
                
                self.driver.refresh()
                time.sleep(3)
                print("✓ Loaded saved cookies")
                return True
        except Exception as e:
            print(f"✗ Could not load cookies: {e}")
        
        return False
    
    def find_and_play_video(self):
        """Try to find and play the video"""
        print("\nLooking for video...")
        
        strategies = [
            self._click_play_button,
            self._search_video_in_page,
            self._check_video_elements,
        ]
        
        for strategy in strategies:
            if strategy():
                return True
        
        return False
    
    def _click_play_button(self):
        """Try to click play button"""
        try:
            # Various play button selectors
            selectors = [
                "#play-video",
                ".play-button",
                "button[onclick*='play']",
                "a[href*='play']",
                "//button[contains(text(), 'Play')]",
                "//button[contains(text(), 'تشغيل')]",
            ]
            
            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        element = self.driver.find_element(By.XPATH, selector)
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if element.is_displayed():
                        self.driver.execute_script("arguments[0].click();", element)
                        print(f"✓ Clicked play button: {selector}")
                        time.sleep(3)
                        return True
                except:
                    continue
        except Exception as e:
            print(f"Could not click play button: {e}")
        
        return False
    
    def _search_video_in_page(self):
        """Search for video in page source"""
        try:
            page_source = self.driver.page_source
            
            # Look for video URLs in source
            patterns = [
                r'src="(https?://[^"]+\.(mp4|m3u8)[^"]*)"',
                r'file:\s*["\'](https?://[^"\']+)["\']',
                r'videoUrl:\s*["\'](https?://[^"\']+)["\']',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                if matches:
                    print(f"✓ Found video URL in page source")
                    return True
        except Exception as e:
            print(f"Error searching page: {e}")
        
        return False
    
    def _check_video_elements(self):
        """Check for video elements on page"""
        try:
            # Look for video tags
            video_elements = self.driver.find_elements(By.TAG_NAME, "video")
            if video_elements:
                print(f"✓ Found {len(video_elements)} video element(s)")
                return True
            
            # Look for iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src") or ""
                if "youtube" in src or "player" in src:
                    print(f"✓ Found video iframe: {src[:50]}...")
                    return True
        except Exception as e:
            print(f"Error checking video elements: {e}")
        
        return False
    
    def extract_video_url(self):
        """Extract video URL from current page"""
        print("\nExtracting video URL...")
        
        try:
            # Wait for page to settle
            time.sleep(5)
            
            # Get current page source
            page_source = self.driver.page_source
            
            # Try different extraction methods
            methods = [
                self._extract_from_video_tag,
                self._extract_from_iframe,
                self._extract_from_page_source,
                self._extract_from_network,
            ]
            
            for method in methods:
                video_url = method()
                if video_url:
                    return video_url
            
            return None
            
        except Exception as e:
            print(f"Error extracting video URL: {e}")
            return None
    
    def _extract_from_video_tag(self):
        """Extract from video tag"""
        try:
            videos = self.driver.find_elements(By.TAG_NAME, "video")
            for video in videos:
                src = video.get_attribute("src")
                if src and ("http" in src or ".mp4" in src):
                    return src
        except:
            pass
        return None
    
    def _extract_from_iframe(self):
        """Extract from iframe"""
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src")
                if src and ("youtube" in src or "vimeo" in src):
                    return src
        except:
            pass
        return None
    
    def _extract_from_page_source(self):
        """Extract from page source"""
        try:
            page_source = self.driver.page_source
            
            patterns = [
                r'src="(https?://[^"]+\.(mp4|m3u8|webm)[^"]*)"',
                r'file:\s*["\'](https?://[^"\']+)["\']',
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                if matches:
                    url = matches[0][0] if isinstance(matches[0], tuple) else matches[0]
                    if not any(x in url for x in [".js", ".css", ".png"]):
                        return url
        except:
            pass
        return None
    
    def _extract_from_network(self):
        """Try to get video URL from network requests"""
        try:
            # Get performance logs (requires Chrome options)
            logs = self.driver.get_log("performance")
            
            for entry in logs:
                try:
                    message = json.loads(entry["message"])["message"]
                    if "Network.responseReceived" in message.get("method", ""):
                        url = message["params"]["response"]["url"]
                        if any(ext in url for ext in [".mp4", ".m3u8", ".webm"]):
                            return url
                except:
                    continue
        except:
            pass
        return None
    
    def download_with_ytdlp(self, video_url, episode_num):
        """Download using yt-dlp"""
        print(f"\nDownloading episode {episode_num}...")
        
        ydl_opts = {
            'outtmpl': str(self.download_dir / f'episode_{episode_num:03d}.%(ext)s'),
            'format': 'worst[ext=mp4]/worst',
            'quiet': False,
            'no_warnings': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.driver.current_url,
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                if info:
                    print(f"✓ Downloaded episode {episode_num}")
                    return True
            return False
        except Exception as e:
            print(f"✗ Download failed: {e}")
            return False
    
    def process_episode(self, url, episode_num):
        """Process a single episode"""
        print(f"\n{'='*60}")
        print(f"EPISODE {episode_num}")
        print(f"{'='*60}")
        
        # Try to load cookies first
        cookies_loaded = self.load_cookies(url)
        
        # Navigate to URL
        print(f"Opening: {url}")
        if not cookies_loaded:
            self.driver.get(url)
        
        # Check for Cloudflare
        page_source = self.driver.page_source.lower()
        if "cloudflare" in page_source:
            print("Cloudflare detected!")
            self.manual_cloudflare_bypass(url)
        
        # Try to find and play video
        self.find_and_play_video()
        
        # Extract video URL
        video_url = self.extract_video_url()
        
        if video_url:
            print(f"✓ Video URL found: {video_url[:80]}...")
            return self.download_with_ytdlp(video_url, episode_num)
        else:
            print("✗ Could not find video URL")
            
            # Save page for debugging
            debug_file = self.download_dir / f"debug_ep{episode_num}.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"Saved page to: {debug_file}")
            
            return False
    
    def run(self):
        """Main function"""
        print("="*60)
        print("SIMPLE AHUAK.TV DOWNLOADER")
        print("="*60)
        
        # Setup browser
        if not self.setup_browser():
            print("Failed to setup browser. Make sure Chrome is installed.")
            return
        
        try:
            # Get URLs
            print("\nEnter the base URL (like: https://dal.ahwaktv.net/watch.php?vid=3b9bfa404)")
            base_url = input("URL: ").strip()
            
            try:
                num_episodes = int(input("Number of episodes: "))
            except ValueError:
                print("Invalid number")
                return
            
            # Process episodes
            successful = 0
            
            for i in range(1, num_episodes + 1):
                # Build episode URL
                if "vid=" in base_url:
                    # Try to increment hex ID
                    import re
                    match = re.search(r'vid=([a-f0-9]+)', base_url)
                    if match:
                        base_id = match.group(1)
                        try:
                            new_id = hex(int(base_id, 16) + (i-1))[2:]
                            episode_url = base_url.replace(base_id, new_id)
                        except:
                            episode_url = base_url
                    else:
                        episode_url = base_url
                else:
                    episode_url = f"{base_url}/{i}"
                
                print(f"\nProcessing: {episode_url}")
                
                if self.process_episode(episode_url, i):
                    successful += 1
                
                # Delay between episodes
                if i < num_episodes:
                    delay = 10
                    print(f"\nWaiting {delay} seconds...")
                    time.sleep(delay)
            
            # Summary
            print(f"\n{'='*60}")
            print("SUMMARY")
            print(f"{'='*60}")
            print(f"Successfully downloaded: {successful}/{num_episodes}")
            print(f"Files saved in: {self.download_dir.absolute()}")
            
        except KeyboardInterrupt:
            print("\n\nStopped by user")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            if self.driver:
                print("\nClosing browser...")
                self.driver.quit()

def main():
    """Entry point"""
    downloader = SimpleAhuakDownloader()
    downloader.run()

if __name__ == "__main__":
    main()
