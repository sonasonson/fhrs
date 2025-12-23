#!/usr/bin/env python3
"""
Ahuak.tv Video Downloader Script
Automates downloading video episodes from Ahuak.tv with Firefox browser
"""

import os
import sys
import time
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
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
            'selenium',
            'yt-dlp',
            'beautifulsoup4',
            'requests'
        ]
        
        print("Checking dependencies...")
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"✓ {package} is already installed")
            except ImportError:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        
        # Check for geckodriver
        self.check_geckodriver()
    
    def check_geckodriver(self):
        """Check if geckodriver is available"""
        try:
            # Try to find geckodriver in PATH
            geckodriver_path = shutil.which('geckodriver')
            if not geckodriver_path:
                print("Geckodriver not found in PATH. Please install it:")
                print("Ubuntu/Debian: sudo apt-get install firefox-geckodriver")
                print("macOS: brew install geckodriver")
                print("Or download from: https://github.com/mozilla/geckodriver/releases")
                print("After installation, add it to your PATH")
                exit(1)
            print(f"✓ Geckodriver found at: {geckodriver_path}")
        except Exception as e:
            print(f"Error checking geckodriver: {e}")
            exit(1)
    
    def setup_firefox_driver(self):
        """Configure Firefox driver with appropriate options"""
        print("Setting up Firefox browser...")
        
        firefox_options = Options()
        
        # Set preferences for better automation
        firefox_options.set_preference("browser.download.folderList", 2)
        firefox_options.set_preference("browser.download.dir", str(self.download_dir.absolute()))
        firefox_options.set_preference("browser.download.useDownloadDir", True)
        firefox_options.set_preference("browser.download.viewableInternally.enabledTypes", "")
        firefox_options.set_preference("browser.download.manager.showWhenStarting", False)
        firefox_options.set_preference("browser.download.manager.useWindow", False)
        firefox_options.set_preference("browser.download.manager.focusWhenStarting", False)
        firefox_options.set_preference("browser.helperApps.neverAsk.saveToDisk", 
                                      "video/mp4,video/webm,application/octet-stream")
        
        # Disable notifications and popups
        firefox_options.set_preference("dom.webnotifications.enabled", False)
        firefox_options.set_preference("dom.popup_maximum", 0)
        
        # Enable headless mode (optional - disable for debugging)
        # firefox_options.add_argument("--headless")
        
        try:
            service = Service()
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            self.driver.maximize_window()
            print("✓ Firefox driver initialized successfully")
        except Exception as e:
            print(f"✗ Failed to initialize Firefox driver: {e}")
            print("\nPlease ensure:")
            print("1. Firefox is installed")
            print("2. Geckodriver is in PATH")
            print("3. No other Firefox instances are running")
            exit(1)
    
    def get_user_input(self):
        """Get series URL and episode count from user"""
        print("\n" + "="*50)
        print("AHUAK.TV DOWNLOADER")
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
    
    def wait_for_cloudflare(self):
        """Wait for user to manually bypass Cloudflare protection"""
        print("\n" + "="*50)
        print("CLOUDFLARE BYPASS REQUIRED")
        print("="*50)
        print("\nIf you see a Cloudflare verification page:")
        print("1. Complete the CAPTCHA/verification manually")
        print("2. Wait for the page to load completely")
        print("3. Return to this terminal")
        print("\nThe script will automatically continue in 30 seconds...")
        print("\nPress Enter when you've completed the Cloudflare verification...")
        
        input()
        
        # Additional wait time
        time.sleep(5)
        print("✓ Continuing with script...")
    
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
            try:
                close_buttons = self.driver.find_elements(By.CLASS_NAME, "close")
                for btn in close_buttons:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(1)
            except:
                pass
                
        except Exception as e:
            print(f"Note: Could not handle popups: {e}")
    
    def click_play_button(self):
        """Click on the play video button"""
        print("\nLooking for play button...")
        
        try:
            # Wait for page to load
            time.sleep(3)
            
            # Try multiple selectors for play button
            selectors = [
                "#play-video",
                ".play-button",
                "button[onclick*='play']",
                "a[href*='play']",
                "//button[contains(text(), 'Play')]",
                "//a[contains(text(), 'Play')]"
            ]
            
            play_button = None
            
            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        play_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        play_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if play_button and play_button.is_displayed():
                        break
                except:
                    continue
            
            if play_button and play_button.is_displayed():
                # Scroll to element
                self.driver.execute_script("arguments[0].scrollIntoView(true);", play_button)
                time.sleep(1)
                
                # Click using JavaScript to avoid interception
                self.driver.execute_script("arguments[0].click();", play_button)
                print("✓ Play button clicked")
                time.sleep(3)
                
                # Handle popups after clicking play
                self.handle_popups()
                return True
            else:
                print("✗ Play button not found or not visible")
                return False
                
        except Exception as e:
            print(f"✗ Error clicking play button: {e}")
            return False
    
    def find_best_server(self):
        """Find and select the best available server for download"""
        print("\nScanning for available servers...")
        time.sleep(5)
        
        # List of server patterns to look for (prioritized)
        server_patterns = [
            "low", "360p", "480p", "sd", "mobile", 
            "server1", "server 1", "سيرفر 1"
        ]
        
        try:
            # Get page source to parse
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Look for server selection elements
            server_elements = []
            
            # Common server selection patterns
            server_selectors = [
                "select[id*='server']",
                "div[class*='server']",
                "ul[class*='server']",
                "div[id*='server']",
                ".server-list",
                "#servers",
                ".server-select"
            ]
            
            for selector in server_selectors:
                elements = soup.select(selector)
                if elements:
                    server_elements.extend(elements)
            
            if not server_elements:
                print("No server selection found. Trying to find video source directly...")
                return self.extract_video_url()
            
            print(f"Found {len(server_elements)} server selection elements")
            
            # Try to find low quality server
            for element in server_elements:
                element_text = element.get_text().lower()
                
                for pattern in server_patterns:
                    if pattern in element_text:
                        print(f"✓ Found server matching '{pattern}'")
                        
                        # Try to click the server element
                        try:
                            server_id = None
                            for attr in ['id', 'class', 'data-server']:
                                if attr in element.attrs:
                                    server_id = element[attr]
                                    break
                            
                            if server_id:
                                # Find and click using Selenium
                                clickable = self.driver.find_element(
                                    By.CSS_SELECTOR, 
                                    f"[id*='{server_id}'], [class*='{server_id}']"
                                )
                                clickable.click()
                                time.sleep(3)
                                return self.extract_video_url()
                        except:
                            continue
            
            # If no specific server found, try the first one
            print("No specific low-quality server found. Trying first available server...")
            try:
                first_server = self.driver.find_element(By.CSS_SELECTOR, 
                                                      "select option, .server-item, [data-server]")
                first_server.click()
                time.sleep(3)
                return self.extract_video_url()
            except:
                return self.extract_video_url()
                
        except Exception as e:
            print(f"Error finding server: {e}")
            return self.extract_video_url()
    
    def extract_video_url(self):
        """Extract video URL from the page"""
        print("\nExtracting video URL...")
        
        try:
            # Wait for video player to load
            time.sleep(5)
            
            # Try to find video element
            video_element = None
            video_selectors = [
                "video",
                "iframe[src*='video']",
                "iframe[src*='player']",
                "video source",
                "[data-video-url]",
                "#video-player",
                ".video-player"
            ]
            
            for selector in video_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            video_element = elem
                            break
                except:
                    continue
            
            if video_element:
                # Get video URL from different attributes
                url_attributes = ['src', 'data-src', 'data-video-url', 'href']
                
                for attr in url_attributes:
                    video_url = video_element.get_attribute(attr)
                    if video_url and ('http' in video_url or '.m3u8' in video_url):
                        print(f"✓ Found video URL: {video_url[:50]}...")
                        return video_url
                
                # If no URL found in attributes, try to get from page source
                page_source = self.driver.page_source
                
                # Look for common video URL patterns
                import re
                patterns = [
                    r'https?://[^\s"\'<>]+\.(mp4|m3u8|webm|flv)[^\s"\']*',
                    r'src:\s*["\'](https?://[^"\']+\.(mp4|m3u8|webm|flv))["\']',
                    r'file:\s*["\'](https?://[^"\']+)["\']',
                    r'videoUrl:\s*["\'](https?://[^"\']+)["\']'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, page_source, re.IGNORECASE)
                    if matches:
                        if isinstance(matches[0], tuple):
                            video_url = matches[0][0]
                        else:
                            video_url = matches[0]
                        print(f"✓ Found video URL in source: {video_url[:50]}...")
                        return video_url
            
            print("✗ Could not extract video URL directly")
            return None
            
        except Exception as e:
            print(f"✗ Error extracting video URL: {e}")
            return None
    
    def download_video(self, video_url, episode_num):
        """Download video using yt-dlp"""
        if not video_url:
            print(f"✗ No video URL found for episode {episode_num}")
            return False
        
        print(f"\nStarting download for episode {episode_num}...")
        print(f"URL: {video_url}")
        
        # Configure yt-dlp options
        ydl_opts = {
            'outtmpl': str(self.download_dir / f'episode_{episode_num:03d}.%(ext)s'),
            'format': 'worst',  # Low quality
            'quiet': False,
            'no_warnings': False,
            'progress_hooks': [self.download_progress_hook],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://ahuak.tv/',
                'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/octet-stream;q=0.8,*/*;q=0.5'
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                if info:
                    print(f"✓ Successfully downloaded episode {episode_num}")
                    return True
                else:
                    print(f"✗ Failed to download episode {episode_num}")
                    return False
        except Exception as e:
            print(f"✗ Download error for episode {episode_num}: {e}")
            
            # Fallback: Try direct download if yt-dlp fails
            return self.direct_download(video_url, episode_num)
    
    def direct_download(self, video_url, episode_num):
        """Fallback direct download method"""
        print(f"Trying direct download for episode {episode_num}...")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://ahuak.tv/'
            }
            
            response = requests.get(video_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            ext = 'mp4'
            if 'webm' in content_type:
                ext = 'webm'
            elif 'x-matroska' in content_type:
                ext = 'mkv'
            
            filename = self.download_dir / f'episode_{episode_num:03d}_direct.{ext}'
            
            with open(filename, 'wb') as f:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"Downloading: {percent:.1f}%", end='\r')
            
            print(f"\n✓ Direct download completed: {filename}")
            return True
            
        except Exception as e:
            print(f"✗ Direct download failed: {e}")
            return False
    
    def download_progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            print(f"Progress: {percent} | Speed: {speed} | ETA: {eta}", end='\r')
        elif d['status'] == 'finished':
            print(f"\n✓ Download completed")
    
    def process_episode(self, episode_url, episode_num):
        """Process a single episode"""
        print(f"\n{'='*50}")
        print(f"PROCESSING EPISODE {episode_num}")
        print(f"{'='*50}")
        
        try:
            # Navigate to episode URL
            print(f"Opening: {episode_url}")
            self.driver.get(episode_url)
            
            # Handle Cloudflare on first episode only
            if episode_num == 1:
                self.wait_for_cloudflare()
            
            # Wait for page to load
            time.sleep(5)
            
            # Click play button
            if not self.click_play_button():
                print("Trying alternative method...")
                # Try direct video extraction
                video_url = self.extract_video_url()
            else:
                # Find and select server
                video_url = self.find_best_server()
            
            # Download video
            if video_url:
                success = self.download_video(video_url, episode_num)
                if success:
                    print(f"✓ Episode {episode_num} completed successfully")
                    return True
                else:
                    print(f"✗ Failed to download episode {episode_num}")
                    return False
            else:
                print(f"✗ Could not find video source for episode {episode_num}")
                return False
                
        except Exception as e:
            print(f"✗ Error processing episode {episode_num}: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            print("\nClosing browser...")
            self.driver.quit()
        
        # Remove cookies file
        if self.cookies_file.exists():
            self.cookies_file.unlink()
        
        print("\nCleanup completed")
    
    def run(self):
        """Main execution method"""
        try:
            # Get user input
            series_url, episode_count = self.get_user_input()
            
            # Setup Firefox driver
            self.setup_firefox_driver()
            
            # Process each episode
            successful_downloads = 0
            
            for i in range(1, episode_count + 1):
                # Construct episode URL (modify based on site structure)
                if "?ep=" in series_url or "episode=" in series_url:
                    # URL already contains episode parameter
                    episode_url = series_url.replace("episode=", f"episode={i}")
                else:
                    # Add episode parameter
                    episode_url = f"{series_url}?ep={i}"
                
                # Process episode
                if self.process_episode(episode_url, i):
                    successful_downloads += 1
            
            # Summary
            print(f"\n{'='*50}")
            print("DOWNLOAD SUMMARY")
            print(f"{'='*50}")
            print(f"Total episodes: {episode_count}")
            print(f"Successfully downloaded: {successful_downloads}")
            print(f"Failed: {episode_count - successful_downloads}")
            print(f"Download directory: {self.download_dir.absolute()}")
            
        except KeyboardInterrupt:
            print("\n\nDownload interrupted by user")
        except Exception as e:
            print(f"\nFatal error: {e}")
        finally:
            self.cleanup()

def main():
    """Main function"""
    print("Ahuak.tv Downloader Script")
    print("=" * 50)
    print("Requirements:")
    print("- Firefox browser installed")
    print("- Geckodriver in PATH")
    print("- Internet connection")
    print("=" * 50)
    
    # Create and run downloader
    downloader = AhuakTVDownloader()
    downloader.run()

if __name__ == "__main__":
    main()
