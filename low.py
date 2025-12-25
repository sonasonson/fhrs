#!/usr/bin/env python3
"""
Simple script using yt-dlp to download videos from 3seq website
"""

import subprocess
import sys
import re
import os
import time

def check_ytdlp():
    """Check if yt-dlp is installed"""
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("[✓] yt-dlp is installed")
        return True
    except:
        print("[!] yt-dlp is not installed")
        return False

def install_ytdlp():
    """Install yt-dlp"""
    print("[*] Installing yt-dlp...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)
        print("[✓] yt-dlp installed successfully")
        return True
    except:
        print("[X] Failed to install yt-dlp via pip")
        
        # Try alternative installation methods
        print("[*] Trying alternative installation...")
        try:
            subprocess.run(['curl', '-L', 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp', '-o', '/usr/local/bin/yt-dlp'], check=True)
            subprocess.run(['chmod', 'a+rx', '/usr/local/bin/yt-dlp'], check=True)
            print("[✓] yt-dlp installed successfully")
            return True
        except:
            print("[X] Please install yt-dlp manually:")
            print("    sudo apt update && sudo apt install yt-dlp")
            print("    OR")
            print("    sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp")
            print("    sudo chmod a+rx /usr/local/bin/yt-dlp")
            return False

def get_final_url(initial_url):
    """Get the final URL after redirects using curl"""
    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '-I', initial_url],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Extract the final URL from curl output
        for line in result.stdout.split('\n'):
            if line.startswith('location:') or line.startswith('Location:'):
                location = line.split(':', 1)[1].strip()
                if location.startswith('http'):
                    return location
        
        # If no redirect found, return the original URL
        return initial_url
        
    except Exception as e:
        print(f"    [X] Error getting final URL: {e}")
        return initial_url

def download_with_ytdlp(watch_url, episode_num, quality='worst'):
    """Download video using yt-dlp"""
    filename = f"The_Protector_S01E{episode_num:02d}.%(ext)s"
    
    # Basic yt-dlp command for low quality
    command = [
        'yt-dlp',
        '-f', quality,  # 'worst' for lowest quality, 'best' for highest
        '--merge-output-format', 'mp4',
        '-o', filename,
        '--add-header', 'Referer:https://x.3seq.com/',
        '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        watch_url
    ]
    
    print(f"    Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"    [✓] Download completed for episode {episode_num}")
            return True
        else:
            print(f"    [X] Download failed for episode {episode_num}")
            print(f"    Error: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"    [X] Download timeout for episode {episode_num}")
        return False
    except Exception as e:
        print(f"    [X] Error: {e}")
        return False

def process_episode(base_url, episode_num, quality='worst'):
    """Process a single episode"""
    print(f"\n[*] Processing Episode {episode_num}")
    
    # 1. Generate episode URL
    episode_url = generate_episode_url(base_url, episode_num)
    print(f"    Initial URL: {episode_url}")
    
    # 2. Get final URL with random code (follow redirects)
    final_url = get_final_url(episode_url)
    print(f"    Final URL: {final_url}")
    
    # 3. Add ?do=watch parameter
    if '?do=watch' not in final_url:
        if final_url.endswith('/'):
            watch_url = final_url + '?do=watch'
        else:
            watch_url = final_url + '/?do=watch'
    else:
        watch_url = final_url
    
    print(f"    Watch URL: {watch_url}")
    
    # 4. Download with yt-dlp
    return download_with_ytdlp(watch_url, episode_num, quality)

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
    print("=" * 60)
    print("THE PROTECTOR DOWNLOADER - STREAMING VERSION")
    print("Using yt-dlp for streaming video download")
    print("=" * 60)
    
    # Check and install yt-dlp
    if not check_ytdlp():
        if not install_ytdlp():
            print("\n[X] Cannot proceed without yt-dlp")
            print("[*] Please install yt-dlp manually and try again")
            sys.exit(1)
    
    # Get user input
    print("\n" + "=" * 60)
    print("CONFIGURATION")
    print("=" * 60)
    
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
    
    # Quality selection
    print("\nSelect video quality:")
    print("1. Lowest quality (faster download, smaller file)")
    print("2. Best quality (slower download, larger file)")
    print("3. Manual quality selection")
    
    quality_choice = input("Enter choice [default: 1]: ").strip()
    if quality_choice == '2':
        quality = 'best'
    elif quality_choice == '3':
        quality = input("Enter yt-dlp format code (e.g., 'worst', 'best', 'bestvideo[height<=480]+bestaudio'): ").strip()
        if not quality:
            quality = 'worst'
    else:
        quality = 'worst'
    
    print(f"\nSelected quality: {quality}")
    
    # Create download directory
    download_dir = "the_protector_episodes"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    os.chdir(download_dir)
    
    print("\n" + "=" * 60)
    print("STARTING DOWNLOAD PROCESS")
    print("=" * 60)
    
    successful = 0
    failed = 0
    
    for episode_num in range(start_episode, start_episode + num_episodes):
        if process_episode(base_url, episode_num, quality):
            successful += 1
        else:
            failed += 1
        
        # Delay between episodes
        if episode_num < start_episode + num_episodes - 1:
            print("\n[*] Waiting 3 seconds before next episode...")
            time.sleep(3)
    
    # Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Total episodes: {num_episodes}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Download location: {os.path.abspath('.')}")
    
    if failed > 0:
        print("\n[!] Some episodes failed to download.")
        print("[*] You can try:")
        print("    1. Running the script again for failed episodes")
        print("    2. Using 'best' quality instead of 'worst'")
        print("    3. Checking if the website is accessible")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Download interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[X] Error: {e}")
        sys.exit(1)
