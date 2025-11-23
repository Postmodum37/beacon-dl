import subprocess
import sys
from pathlib import Path
import yt_dlp
from rich.console import Console

from .config import settings
from .utils import sanitize_filename, map_language_to_iso
from .auth import get_auth_args

console = Console()

class BeaconDownloader:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'verbose': True,
            'no_warnings': True,
            'user_agent': settings.user_agent,
            'http_headers': {
                'User-Agent': settings.user_agent,
            },
            # We handle output template manually
        }

    def process_url(self, url: str):
        console.print(f"==> Fetching video metadata for {url}...")

        # Resolve auth args once, passing the URL for Playwright to navigate to
        auth_args = get_auth_args(target_url=url)
        
        # Update base options with auth
        if auth_args:
            if auth_args[0] == "--cookies":
                self.ydl_opts['cookiefile'] = auth_args[1]
            elif auth_args[0] == "--cookies-from-browser":
                browser_arg = auth_args[1]
                if ":" in browser_arg:
                    browser_name, profile_path = browser_arg.split(":", 1)
                    self.ydl_opts['cookiesfrombrowser'] = (browser_name, profile_path, None, None)
                else:
                    self.ydl_opts['cookiesfrombrowser'] = (browser_arg, None, None, None)

        # 1. Fetch Metadata
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            console.print(f"[red]Error fetching metadata: {e}[/red]")
            sys.exit(1)

        # 2. Extract Info
        video_id = info.get('id')
        video_title = info.get('title')
        show_name = info.get('series') or info.get('uploader') or "Critical Role"
        show_name = sanitize_filename(show_name)
        
        console.print(f"Show: {show_name}")
        console.print(f"Video: {video_title}")
        console.print(f"ID: {video_id}")
        
        # 3. Determine Output Filename
        output_name = self._generate_filename(info, show_name, video_title)
        output_file = f"{output_name}.{settings.container_format}"
        
        console.print(f"Output: {output_file}")
        
        if Path(output_file).exists():
            console.print(f"[green]✓ Video already downloaded: {output_file}[/green]")
            return

        # 4. Download Video
        temp_dir = Path("temp_dl")
        temp_dir.mkdir(exist_ok=True)
        temp_video = temp_dir / "video.mp4"
        
        console.print(f"==> Downloading video ({settings.preferred_resolution})...")
        
        # Configure download options
        dl_opts = self.ydl_opts.copy()
        dl_opts.update({
            'format': f"bestvideo[height<={settings.preferred_resolution[:-1]}]+bestaudio/best[height<={settings.preferred_resolution[:-1]}]",
            'outtmpl': str(temp_video),
            'merge_output_format': 'mp4',
        })
        
        try:
            with yt_dlp.YoutubeDL(dl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            console.print(f"[red]Error downloading video: {e}[/red]")
            sys.exit(1)

        # 5. Download Subtitles
        console.print("==> Downloading subtitles...")
        temp_subs_prefix = temp_dir / "subs"
        
        sub_opts = self.ydl_opts.copy()
        sub_opts.update({
            'skip_download': True,
            'writesubtitles': True,
            'allsubtitles': True,
            'outtmpl': str(temp_subs_prefix),
        })

        with yt_dlp.YoutubeDL(sub_opts) as ydl:
            ydl.download([url])

        # 6. Merge with FFmpeg
        console.print(f"==> Merging into {output_file}...")
        self._merge_files(temp_video, temp_dir, output_file)
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        console.print(f"[green]✓ Download complete: {output_file}[/green]")

    def _generate_filename(self, info: dict, show_name: str, video_title: str) -> str:
        # Logic to match bash script's filename generation
        import re
        
        is_episodic = False
        season = ""
        episode = ""
        episode_title = ""
        
        # Regex patterns from bash script
        # "C4 E006 | Title"
        m1 = re.match(r'C(\d+)\s+E(\d+)\s+\|\s+(.*)', video_title)
        # "S04E06 - Title"
        m2 = re.match(r'S(\d+)E(\d+)\s*[-:]\s*(.*)', video_title)
        # "S04E06 Title"
        m3 = re.match(r'S(\d+)E(\d+)\s+(.*)', video_title)
        # "4x06 - Title"
        m4 = re.match(r'(\d+)x(\d+)\s*[-:]\s*(.*)', video_title)
        
        if m1:
            is_episodic = True
            season, episode, episode_title = m1.groups()
        elif m2:
            is_episodic = True
            season, episode, episode_title = m2.groups()
        elif m3:
            is_episodic = True
            season, episode, episode_title = m3.groups()
        elif m4:
            is_episodic = True
            season, episode, episode_title = m4.groups()
            
        # Technical specs
        height = info.get('height')
        resolution = f"{height}p" if height else settings.preferred_resolution
        
        vcodec_val = info.get('vcodec', '')
        if 'avc' in vcodec_val:
            video_codec = "H.264"
        elif 'hevc' in vcodec_val:
            video_codec = "H.265"
        elif 'vp9' in vcodec_val:
            video_codec = "VP9"
        else:
            video_codec = settings.default_video_codec
        
        acodec_val = info.get('acodec', '')
        if 'mp4a' in acodec_val:
            audio_codec = "AAC"
        elif 'opus' in acodec_val:
            audio_codec = "Opus"
        elif 'vorbis' in acodec_val:
            audio_codec = "Vorbis"
        elif 'ac3' in acodec_val:
            audio_codec = "AC3"
        elif 'eac3' in acodec_val:
            audio_codec = "EAC3"
        else:
            audio_codec = settings.default_audio_codec
        
        channels = info.get('audio_channels')
        audio_channels = f"{channels}.0" if channels and str(channels).isdigit() else settings.default_audio_channels
        
        if is_episodic:
            season_padded = f"{int(season):02d}"
            episode_padded = f"{int(episode):02d}"
            title_formatted = sanitize_filename(episode_title)
            return f"{show_name}.S{season_padded}E{episode_padded}.{title_formatted}.{resolution}.{settings.source_type}.{audio_codec}{audio_channels}.{video_codec}-{settings.release_group}"
        else:
            title_formatted = sanitize_filename(video_title)
            # Check if title starts with show name
            escaped_show = re.escape(show_name)
            if re.match(rf"^{escaped_show}\.", title_formatted):
                return f"{title_formatted}.{resolution}.{settings.source_type}.{audio_codec}{audio_channels}.{video_codec}-{settings.release_group}"
            else:
                return f"{show_name}.{title_formatted}.{resolution}.{settings.source_type}.{audio_codec}{audio_channels}.{video_codec}-{settings.release_group}"

    def _merge_files(self, video_path: Path, temp_dir: Path, output_path: str):
        # Find subtitles
        subs = list(temp_dir.glob("subs.*.vtt"))
        
        cmd = ['ffmpeg', '-i', str(video_path)]
        
        for sub in subs:
            cmd.extend(['-i', str(sub)])
            
        cmd.extend(['-map', '0:v', '-map', '0:a'])
        
        for i, sub in enumerate(subs):
            cmd.extend(['-map', str(i+1)])
            
        cmd.extend(['-c:v', 'copy', '-c:a', 'copy', '-c:s', 'srt'])
        
        # Metadata
        for i, sub in enumerate(subs):
            # Extract lang
            # temp_subs.en.vtt or temp_subs.en.English.vtt
            parts = sub.name.split('.')
            if len(parts) >= 4:
                lang_name = parts[-2] # English
            elif len(parts) >= 3:
                lang_name = parts[-2] # en
            else:
                lang_name = "und"
                
            iso_code = map_language_to_iso(lang_name)
            cmd.extend([f'-metadata:s:s:{i}', f'language={iso_code}'])
            
        cmd.extend([output_path, '-y', '-hide_banner', '-loglevel', 'warning'])
        
        subprocess.run(cmd, check=True)
