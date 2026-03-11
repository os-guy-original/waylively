"""
Auto-thumbnail generation for wallpapers.

- Video (MP4, WebM, MKV, AVI, MOV): extract first frame via ffmpeg
- GIF: copy the GIF itself as the thumbnail (GTK Picture shows it animated)
- Lively (HTML): no-op here (would need a headless WebKit render — future work)
"""

import os
import subprocess
import shutil
import sys

from waylively.utils.config import VIDEO_EXTENSIONS, GIF_EXTENSION, resolve_appimage_path

THUMB_FILENAME = "thumbnail_auto.png"


def _resolve_screenshot_command(html_path, output_path):
    appimage_path = resolve_appimage_path()
    if appimage_path:
        return [appimage_path, "--screenshot", html_path, output_path]

    local_bin = os.path.expanduser("~/.local/bin/waylively-screenshot")
    if os.path.exists(local_bin):
        return [local_bin, html_path, output_path]

    installed = shutil.which("waylively-screenshot")
    if installed:
        return [installed, html_path, output_path]

    dev_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "bin",
        "waylively-screenshot",
    )
    return [sys.executable, dev_script, html_path, output_path]


def generate_thumbnail(wallpaper_dir):
    """
    Scan `wallpaper_dir` for a media entry file and create a thumbnail.

    Returns the path to the generated thumbnail, or None.
    """
    thumb_path = os.path.join(wallpaper_dir, THUMB_FILENAME)
    if os.path.exists(thumb_path):
        return thumb_path

    # Find the entry file
    entry = _find_entry_file(wallpaper_dir)
    if entry is None:
        return None

    ext = os.path.splitext(entry)[1].lower()
    full_entry = os.path.join(wallpaper_dir, entry)

    if ext in VIDEO_EXTENSIONS:
        return _thumb_from_video(full_entry, thumb_path)
    elif ext == GIF_EXTENSION:
        return _thumb_from_gif(full_entry, wallpaper_dir)
    elif ext in {'.html', '.htm'}:
        return _thumb_from_html(full_entry, thumb_path)
    else:
        return None


def _find_entry_file(wallpaper_dir):
    """Locate the media entry file from LivelyInfo.json or by scanning."""
    import json
    info_path = os.path.join(wallpaper_dir, "LivelyInfo.json")
    if os.path.exists(info_path):
        try:
            with open(info_path) as f:
                info = json.load(f)
            fname = info.get("FileName")
            if fname and os.path.exists(os.path.join(wallpaper_dir, fname)):
                return fname
        except Exception:
            pass

    # Scan for media files
    for f in sorted(os.listdir(wallpaper_dir)):
        ext = os.path.splitext(f)[1].lower()
        if ext in VIDEO_EXTENSIONS or ext == GIF_EXTENSION:
            return f
    return None


def _thumb_from_video(video_path, output_path):
    """Extract the first frame of a video using ffmpeg."""
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", "1",
                "-i", video_path,
                "-vframes", "1",
                "-vf", "scale=480:-1",
                "-q:v", "2",
                output_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _thumb_from_gif(gif_path, wallpaper_dir):
    """
    For GIFs we copy the GIF itself as the thumbnail so GTK Picture
    renders it animated in the card.
    """
    thumb_path = os.path.join(wallpaper_dir, "thumbnail_auto.gif")
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        shutil.copy2(gif_path, thumb_path)
        return thumb_path
    except Exception:
        return None

def _thumb_from_html(html_path, output_path):
    """
    For HTML wallpapers, we use a headless GTK3/WebKit2 script wrapped via xvfb-run
    to take an actual rendered screenshot.
    """
    if shutil.which("xvfb-run"):
        try:
            env = os.environ.copy()
            env["GDK_BACKEND"] = "x11"
            env["WEBKIT_DISABLE_SANDBOX"] = "1"
            env["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
            subprocess.run(
                ["dbus-run-session", "xvfb-run", "--auto-servernum", *_resolve_screenshot_command(html_path, output_path)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=12,
            )
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
        except Exception:
            pass
            
    return None
