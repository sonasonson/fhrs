#!/usr/bin/env python3
"""
Ahuak.tv Video Downloader Script with Cloudflare Bypass
Uses undetected-chromedriver to avoid Cloudflare detection
"""

import os
import sys
import time
import json
import shutil
import subprocess
import random
from pathlib import Path
from urllib.parse import urlparse
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException
)
import yt_dlp
import requests
from bs4 import BeautifulSoup

class AhuakTVDownloader:
    def __init__(self):
        self.driver = None
        self.wait_timeout = 30
        self.episode_urls = []
        self.download_dir = Path("downloads")
        self.cookies_file = Path("cookies.json")
        self.setup_directories()
        self.check_and_install_dependencies()
        
    def setup_directories(self):
        """Create necessary directories"""
        self.download_dir.mkdir(exist_ok=True)
        
    def check_and_install_dependencies(self):
        """Check and install required packages"""
        required_packages = [
            'undetected-chromedriver',
            'selenium',
            'yt-dlp',
            'beautifulsoup4',
            'requests',
            'webdriver-manager'
        ]
        
        print("Checking dependencies...")
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"✓ {package} is already installed")
            except ImportError:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        
        # Check for Chrome
        self.check_chrome_installation()
    
    def check_chrome_installation(self):
        """Check if Chrome is installed"""
        try:
            # Try to find Chrome in common locations
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
            ]
            
            chrome_found = False
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_found = True
                    print(f"✓ Chrome/Chromium found at: {path}")
                    break
            
            if not chrome_found:
                # Try using which/where
                if shutil.which("google-chrome"):
                    print("✓ Chrome found via PATH")
                elif shutil.which("chromium"):
                    print("✓ Chromium found via PATH")
                else:
                    print("⚠ Chrome/Chromium not found. Please install Chrome:")
                    print("  Ubuntu/Debian: sudo apt install google-chrome-stable")
                    print("  Fedora: sudo dnf install google-chrome-stable")
                    print("  macOS: brew install --cask google-chrome")
                    print("  Or download from: https://www.google.com/chrome/")
        except Exception as e:
            print(f"⚠ Error checking Chrome: {e}")
    
    def setup_chrome_driver(self):
    """Configure Chrome driver with undetected-chromedriver"""
    print("Setting up Chrome browser (undetected mode)...")
    
    try:
        # استخدم الإعدادات الأساسية فقط
        options = uc.ChromeOptions()
        
        # أضف الوسائط الأساسية فقط
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # إعدادات التحميل
        prefs = {
            "download.default_directory": str(self.download_dir.absolute()),
            "download.prompt_for_download": False,
        }
        options.add_experimental_option("prefs", prefs)
        
        # استخدم إصدار Chrome المثبت على النظام (دعه يكتشفه تلقائيًا)
        print("Initializing undetected Chrome driver...")
        self.driver = uc.Chrome(
            options=options,
            suppress_welcome=True,
            use_subprocess=True
        )
        
        # إخفاء الأتمتة
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        print("✓ Chrome driver initialized successfully")
        return True
        
    except Exception as e:
        print(f"✗ Failed with undetected-chromedriver: {e}")
        print("\nTrying with regular Chrome driver via webdriver-manager...")
        return self.setup_regular_chrome_driver_fixed()

def setup_regular_chrome_driver_fixed(self):
    """Fallback using webdriver-manager"""
    try:
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        
        # حل مشكلة DevToolsActivePort
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=9222")
        
        # إعدادات مهمة لمنع التحطم
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # استخدام webdriver-manager لتحديد ChromeDriver تلقائيًا
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        print("✓ Regular Chrome driver initialized via webdriver-manager")
        return True
        
    except Exception as e:
        print(f"✗ All Chrome driver methods failed: {e}")
        print("\n" + "="*60)
        print("FINAL RESOLUTION STEPS:")
        print("="*60)
        print("1. Install Chrome manually from https://www.google.com/chrome/")
        print("2. Add Chrome to your PATH")
        print("3. Run: pip install --force-reinstall undetected-chromedriver==3.5.4")
        print("4. OR: Use the FlareSolverr method mentioned previously")
        return False
    
    def setup_regular_chrome_driver(self):
        """Fallback to regular Chrome driver if undetected fails"""
        try:
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = Options()
            
            # Add stealth arguments
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Add user agent
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Download preferences
            prefs = {
                "download.default_directory": str(self.download_dir.absolute()),
                "download.prompt_for_download": False,
            }
            options.add_experimental_option("prefs", prefs)
            
            # Use webdriver-manager to get the correct ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Hide automation
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✓ Regular Chrome driver initialized")
            
        except Exception as e:
            print(f"✗ Failed to initialize regular Chrome driver: {e}")
            print("\nPlease install Chrome and ChromeDriver manually.")
            print("Or try installing undetected-chromedriver with:")
            print("  pip install undetected-chromedriver==3.5.4")
            exit(1)
    
    def simulate_human_behavior(self):
        """Simulate human-like behavior to avoid detection"""
        try:
            # Random mouse movements
            action = ActionChains(self.driver)
            
            # Move to random positions
            for _ in range(3):
                x = random.randint(0, 800)
                y = random.randint(0, 600)
                action.move_by_offset(x, y).perform()
                time.sleep(0.5)
            
            # Random scrolling
            scroll_amount = random.randint(200, 800)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(1)
            
            # Scroll back
            self.driver.execute_script(f"window.scrollBy(0, -{scroll_amount//2});")
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Note: Could not simulate human behavior: {e}")
    
    def get_user_input(self):
        """Get series URL and episode count from user"""
        print("\n" + "="*50)
        print("AHUAK.TV DOWNLOADER (CLOUDFLARE BYPASS)")
        print("="*50)
        
        series_url = input("\nEnter the series URL (e.g., https://ahuak.tv/series/...): ").strip()
        
        if not series_url.startswith("http"):
            print("Error: Please enter a valid URL starting with http:// or https://")
            exit(1)
        
        try:
            episode_count = int(input("Enter the number of episodes to download: "))
            if episode_count < 1:
                raise ValueError
        except ValueError:
            print("Error: Please enter a valid positive number")
            exit(1)
        
        return series_url, episode_count
    
    def bypass_cloudflare_manually(self, url):
        """Manual Cloudflare bypass with user interaction"""
        print("\n" + "="*50)
        print("CLOUDFLARE DETECTED - MANUAL BYPASS REQUIRED")
        print("="*50)
        
        print(f"\n1. Opening browser to: {url}")
        print("2. If you see a Cloudflare verification page:")
        print("   - Complete the CAPTCHA/verification manually")
        print("   - Wait for the page to load completely")
        print("   - You should see the video page")
        print("3. Return to this terminal and press Enter")
        print("\nThe browser will open in 5 seconds...")
        
        time.sleep(5)
        
        # Open the URL
        self.driver.get(url)
        
        # Wait for user to complete verification
        print("\n⏳ Waiting for you to complete Cloudflare verification...")
        print("Press Enter in this terminal AFTER you've successfully loaded the page.")
        input()
        
        # Additional wait for page to stabilize
        time.sleep(3)
        
        # Check if we're still on Cloudflare
        current_url = self.driver.current_url
        page_source = self.driver.page_source.lower()
        
        if "cloudflare" in page_source or "challenge" in page_source:
            print("⚠ Still detecting Cloudflare. Let's try again...")
            return self.bypass_cloudflare_manually(url)
        
        print("✓ Cloudflare bypass successful!")
        print(f"✓ Current URL: {current_url}")
        
        return True
    
    def save_cookies(self):
        """Save cookies for future use"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            print("✓ Cookies saved for future sessions")
        except Exception as e:
            print(f"✗ Could not save cookies: {e}")
    
    def load_cookies(self, url):
        """Load saved cookies"""
        if not self.cookies_file.exists():
            return False
        
        try:
            # Go to domain first
            parsed_url = urlparse(url)
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            self.driver.get(domain)
            time.sleep(2)
            
            # Load cookies
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    continue
            
            # Refresh to apply cookies
            self.driver.refresh()
            time.sleep(3)
            print("✓ Cookies loaded from previous session")
            return True
        except Exception as e:
            print(f"✗ Could not load cookies: {e}")
            return False
    
    def handle_popups(self):
        """Close any popup windows"""
        try:
            main_window = self.driver.current_window_handle
            
            # Close all other windows
            for handle in self.driver.window_handles:
                if handle != main_window:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
            
            # Switch back to main window
            self.driver.switch_to.window(main_window)
            
            # Try to close modal popups if present
            close_selectors = [
                ".close", "[data-dismiss='modal']", ".modal-close",
                ".btn-close", ".popup-close", "button[aria-label='Close']"
            ]
            
            for selector in close_selectors:
                try:
                    close_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in close_buttons:
                        if btn.is_displayed():
                            try:
                                btn.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(1)
                except:
                    pass
                    
        except Exception as e:
            print(f"Note: Could not handle popups: {e}")
    
    def click_play_button(self):
        """Click on the play video button with multiple strategies"""
        print("\nLooking for play button...")
        
        # Wait a bit for page to load
        time.sleep(3)
        
        # Try multiple strategies
        strategies = [
            self._click_by_id,
            self._click_by_class,
            self._click_by_xpath,
            self._click_by_javascript,
            self._click_by_video_element
        ]
        
        for strategy in strategies:
            if strategy():
                return True
        
        print("✗ Could not find or click play button with any strategy")
        return False
    
    def _click_by_id(self):
        """Try clicking by ID"""
        try:
            play_button = self.driver.find_element(By.ID, "play-video")
            if play_button.is_displayed():
                play_button.click()
                print("✓ Play button clicked by ID")
                time.sleep(2)
                return True
        except:
            return False
    
    def _click_by_class(self):
        """Try clicking by class name"""
        try:
            play_buttons = self.driver.find_elements(By.CLASS_NAME, "play-video")
            for btn in play_buttons:
                if btn.is_displayed():
                    btn.click()
                    print("✓ Play button clicked by class")
                    time.sleep(2)
                    return True
        except:
            pass
        
        # Try other common classes
        classes = ["play-button", "btn-play", "play-btn", "watch-btn"]
        for class_name in classes:
            try:
                elements = self.driver.find_elements(By.CLASS_NAME, class_name)
                for elem in elements:
                    if elem.is_displayed():
                        elem.click()
                        print(f"✓ Play button clicked by class: {class_name}")
                        time.sleep(2)
                        return True
            except:
                continue
        return False
    
    def _click_by_xpath(self):
        """Try clicking by XPath"""
        xpaths = [
            "//button[contains(text(), 'Play')]",
            "//a[contains(text(), 'Play')]",
            "//button[contains(@onclick, 'play')]",
            "//a[contains(@href, 'play')]",
            "//div[contains(@class, 'play')]",
            "//span[contains(text(), 'تشغيل')]",  # Arabic play
            "//button[contains(text(), 'تشغيل')]"
        ]
        
        for xpath in xpaths:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for elem in elements:
                    if elem.is_displayed():
                        elem.click()
                        print(f"✓ Play button clicked by XPath: {xpath[:30]}...")
                        time.sleep(2)
                        return True
            except:
                continue
        return False
    
    def _click_by_javascript(self):
        """Try clicking using JavaScript"""
        scripts = [
            "document.getElementById('play-video').click();",
            "document.querySelector('#play-video').click();",
            "document.querySelector('.play-video').click();",
            "document.querySelector('button.play-button').click();",
            "var els = document.getElementsByClassName('play-video'); if(els.length>0) els[0].click();"
        ]
        
        for script in scripts:
            try:
                self.driver.execute_script(script)
                print("✓ Play button clicked via JavaScript")
                time.sleep(2)
                return True
            except:
                continue
        return False
    
    def _click_by_video_element(self):
        """Try to find and click video element directly"""
        try:
            video_elements = self.driver.find_elements(By.TAG_NAME, "video")
            for video in video_elements:
                if video.is_displayed():
                    # Try to play the video
                    self.driver.execute_script("arguments[0].play();", video)
                    print("✓ Video element played directly")
                    time.sleep(2)
                    return True
        except:
            pass
        return False
    
    def find_best_server(self):
        """Find and select the best available server for download"""
        print("\nScanning for available servers...")
        time.sleep(5)
        
        # First, handle any popups
        self.handle_popups()
        
        # Look for server selection
        server_found = False
        
        # Strategy 1: Look for server dropdown/buttons
        server_patterns = [
            ("select", "server"),  # dropdown with server in name
            ("div", "server"),     # div containing server
            ("ul", "server"),      # server list
            ("button", "server"),  # server button
            ("a", "server"),       # server link
            ("span", "360"),       # quality indicator
            ("span", "480"),
            ("span", "low"),
            ("span", "sd")
        ]
        
        for tag, pattern in server_patterns:
            try:
                elements = self.driver.find_elements(By.XPATH, f"//{tag}[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern}')] | //{tag}[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern}')]")
                
                for element in elements:
                    if element.is_displayed():
                        text = element.text.lower()
                        if 'server' in text or '360' in text or '480' in text or 'low' in text or 'sd' in text:
                            print(f"✓ Found server element: {text[:50]}...")
                            element.click()
                            server_found = True
                            time.sleep(3)
                            break
                if server_found:
                    break
            except:
                continue
        
        # Strategy 2: Look for quality options
        if not server_found:
            quality_terms = ["360p", "480p", "low", "sd", "mobile", "جودة منخفضة"]
            for term in quality_terms:
                try:
                    elements = self.driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{term}')]")
                    for element in elements:
                        if element.is_displayed():
                            print(f"✓ Found quality option: {term}")
                            element.click()
                            server_found = True
                            time.sleep(3)
                            break
                    if server_found:
                        break
                except:
                    continue
        
        # Strategy 3: Try to find and click any playable element
        if not server_found:
            print("No specific server found, trying to extract video directly...")
        
        return self.extract_video_url()
    
    def extract_video_url(self):
        """Extract video URL from the page with multiple strategies"""
        print("\nExtracting video URL...")
        
        # Wait for video to load
        time.sleep(5)
        
        strategies = [
            self._extract_from_video_tag,
            self._extract_from_iframe,
            self._extract_from_source,
            self._extract_from_scripts,
            self._extract_from_network_requests
        ]
        
        for strategy in strategies:
            video_url = strategy()
            if video_url:
                print(f"✓ Video URL found: {video_url[:80]}...")
                return video_url
        
        print("✗ Could not extract video URL")
        return None
    
    def _extract_from_video_tag(self):
        """Extract from video tag"""
        try:
            video_elements = self.driver.find_elements(By.TAG_NAME, "video")
            for video in video_elements:
                src = video.get_attribute("src")
                if src and ("http" in src or ".mp4" in src or ".m3u8" in src):
                    return src
                
                # Check source children
                sources = video.find_elements(By.TAG_NAME, "source")
                for source in sources:
                    src = source.get_attribute("src")
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
                if src and ("youtube" in src or "vimeo" in src or "dailymotion" in src):
                    return src
        except:
            pass
        return None
    
    def _extract_from_source(self):
        """Extract from page source"""
        try:
            page_source = self.driver.page_source
            
            # Look for common video patterns
            import re
            
            patterns = [
                r'src=["\'](https?://[^"\']+\.(mp4|m3u8|webm|flv|avi))["\']',
                r'file:\s*["\'](https?://[^"\']+)["\']',
                r'videoUrl:\s*["\'](https?://[^"\']+)["\']',
                r'url["\']?\s*:\s*["\'](https?://[^"\']+)["\']',
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://[^\s"\']+\.mp4[^\s"\']*)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                if matches:
                    if isinstance(matches[0], tuple):
                        url = matches[0][0]
                    else:
                        url = matches[0]
                    
                    # Filter out common non-video URLs
                    if not any(x in url for x in [".js", ".css", ".png", ".jpg", ".gif"]):
                        return url
        except:
            pass
        return None
    
    def _extract_from_scripts(self):
        """Extract from JavaScript variables"""
        try:
            scripts = [
                "return window.videoUrl;",
                "return window.videoSrc;",
                "return window.video_url;",
                "return document.videoUrl;",
                "return player.src;",
                "return player.getAttribute('src');"
            ]
            
            for script in scripts:
                try:
                    result = self.driver.execute_script(script)
                    if result and "http" in result:
                        return result
                except:
                    continue
        except:
            pass
        return None
    
    def _extract_from_network_requests(self):
        """Try to capture network requests (limited in Selenium)"""
        try:
            # This is a simplified approach
            logs = self.driver.get_log("performance")
            
            video_urls = []
            for entry in logs:
                message = json.loads(entry["message"])["message"]
                if "Network.responseReceived" in message.get("method", ""):
                    try:
                        url = message["params"]["response"]["url"]
                        if any(ext in url for ext in [".mp4", ".m3u8", ".webm", ".flv"]):
                            video_urls.append(url)
                    except:
                        continue
            
            if video_urls:
                return video_urls[0]
        except:
            pass
        return None
    
    def download_video(self, video_url, episode_num):
        """Download video using yt-dlp"""
        if not video_url:
            print(f"✗ No video URL found for episode {episode_num}")
            return False
        
        print(f"\nStarting download for episode {episode_num}...")
        
        # Configure yt-dlp options for streaming sites
        ydl_opts = {
            'outtmpl': str(self.download_dir / f'episode_{episode_num:03d}.%(ext)s'),
            'format': 'worst[ext=mp4]/worst',  # Lowest quality
            'quiet': False,
            'no_warnings': False,
            'progress_hooks': [self.download_progress_hook],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://ahuak.tv/',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://ahuak.tv',
                'Sec-Fetch-Dest': 'video',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site'
            },
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_insecure': True
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                if info:
                    filename = ydl.prepare_filename(info)
                    print(f"✓ Successfully downloaded: {filename}")
                    return True
                else:
                    print(f"✗ Failed to download episode {episode_num}")
                    return False
        except Exception as e:
            print(f"✗ Download error: {e}")
            
            # Try alternative method
            return self.alternative_download(video_url, episode_num)
    
    def alternative_download(self, video_url, episode_num):
        """Alternative download method using requests"""
        print("Trying alternative download method...")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://ahuak.tv/',
                'Accept': '*/*',
                'Accept-Encoding': 'identity',
                'Range': 'bytes=0-'
            }
            
            response = requests.get(video_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get file extension from URL or content-type
            ext = 'mp4'
            content_type = response.headers.get('content-type', '')
            if 'webm' in content_type:
                ext = 'webm'
            elif 'x-matroska' in content_type:
                ext = 'mkv'
            elif '.m3u8' in video_url:
                ext = 'mp4'  # HLS stream
            
            filename = self.download_dir / f'episode_{episode_num:03d}_alt.{ext}'
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"Downloading: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='\r')
            
            print(f"\n✓ Alternative download completed: {filename}")
            return True
            
        except Exception as e:
            print(f"✗ Alternative download failed: {e}")
            return False
    
    def download_progress_hook(self, d):
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
        print(f"PROCESSING EPISODE {episode_num}")
        print(f"{'='*60}")
        
        try:
            print(f"Opening: {episode_url}")
            
            # Try to load cookies first
            if episode_num == 1:
                cookies_loaded = self.load_cookies(episode_url)
                if not cookies_loaded:
                    print("No previous cookies found, starting fresh session")
            
            # Navigate to episode URL
            self.driver.get(episode_url)
            
            # Check for Cloudflare on first episode
            if episode_num == 1:
                time.sleep(5)
                page_source = self.driver.page_source.lower()
                
                if "cloudflare" in page_source or "challenge" in page_source:
                    print("Cloudflare detected! Manual bypass required...")
                    self.bypass_cloudflare_manually(episode_url)
                    # Save cookies after successful bypass
                    self.save_cookies()
            
            # Wait for page to load
            time.sleep(3)
            
            # Click play button
            print("\nAttempting to play video...")
            if not self.click_play_button():
                print("Warning: Could not click play button, trying direct extraction...")
            
            # Handle popups
            self.handle_popups()
            
            # Find server and extract video URL
            video_url = self.find_best_server()
            
            if video_url:
                # Download video
                success = self.download_video(video_url, episode_num)
                if success:
                    print(f"✓ Episode {episode_num} completed successfully")
                    return True
                else:
                    print(f"✗ Failed to download episode {episode_num}")
                    return False
            else:
                print(f"✗ Could not find video source for episode {episode_num}")
                # Try to extract directly from page
                video_url = self.extract_video_url()
                if video_url:
                    return self.download_video(video_url, episode_num)
                return False
                
        except Exception as e:
            print(f"✗ Error processing episode {episode_num}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            print("\nClosing browser...")
            try:
                self.driver.quit()
            except:
                pass
        
        print("\nCleanup completed")
    
    def run(self):
        """Main execution method"""
        try:
            # Get user input
            series_url, episode_count = self.get_user_input()
            
            # Setup Chrome driver
            self.setup_chrome_driver()
            
            # Process each episode
            successful_downloads = 0
            
            for i in range(1, episode_count + 1):
                # Construct episode URL
                if "?ep=" in series_url or "&ep=" in series_url:
                    # Replace episode number in existing parameter
                    if "ep=" in series_url:
                        import re
                        episode_url = re.sub(r'ep=\d+', f'ep={i}', series_url)
                    else:
                        episode_url = f"{series_url}?ep={i}"
                elif "/episode/" in series_url:
                    # Replace episode number in path
                    import re
                    episode_url = re.sub(r'/episode/\d+', f'/episode/{i}', series_url)
                else:
                    # Simple numbering
                    episode_url = f"{series_url}/{i}" if not series_url.endswith('/') else f"{series_url}{i}"
                
                # Process episode
                if self.process_episode(episode_url, i):
                    successful_downloads += 1
                
                # Delay between episodes to avoid rate limiting
                if i < episode_count:
                    delay = random.randint(5, 15)
                    print(f"\nWaiting {delay} seconds before next episode...")
                    time.sleep(delay)
            
            # Summary
            print(f"\n{'='*60}")
            print("DOWNLOAD SUMMARY")
            print(f"{'='*60}")
            print(f"Total episodes requested: {episode_count}")
            print(f"Successfully downloaded: {successful_downloads}")
            print(f"Failed: {episode_count - successful_downloads}")
            print(f"Download directory: {self.download_dir.absolute()}")
            print(f"\nCookies saved for future use: {self.cookies_file}")
            
        except KeyboardInterrupt:
            print("\n\n⚠ Download interrupted by user")
        except Exception as e:
            print(f"\n✗ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

def main():
    """Main function"""
    print("="*60)
    print("AHUAK.TV DOWNLOADER - CLOUDFLARE BYPASS EDITION")
    print("="*60)
    print("\nFeatures:")
    print("- Uses undetected Chrome to bypass Cloudflare")
    print("- Manual Cloudflare verification when needed")
    print("- Saves cookies for future sessions")
    print("- Multiple fallback strategies for video extraction")
    print("- Low quality download to save bandwidth")
    print("="*60)
    print("\nInstructions:")
    print("1. Enter the series URL")
    print("2. Enter number of episodes")
    print("3. If Cloudflare appears, complete verification manually")
    print("4. The script will handle the rest")
    print("="*60)
    
    # Create and run downloader
    downloader = AhuakTVDownloader()
    downloader.run()

if __name__ == "__main__":
    main()

