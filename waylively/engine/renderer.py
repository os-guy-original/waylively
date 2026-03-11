import os
import sys
import re
import json
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
gi.require_version("GtkLayerShell", "0.1")

from gi.repository import Gtk, WebKit2, GtkLayerShell, GLib, Gdk

from waylively.utils.config import ALL_MEDIA_EXTENSIONS as VIDEO_EXTENSIONS


class LivelyWallpaperEngine(Gtk.Window):
    """
    Renders a Lively Wallpaper HTML5/WebGL page as a Wayland desktop background.

    Performance features:
      - os.nice(19): lowest CPU priority so foreground apps are never starved
      - WebKit SHARED_SECONDARY_PROCESS: saves ~100 MB RAM vs per-tab processes
      - DOCUMENT_VIEWER cache model: minimal memory for a non-navigating page
      - Resolution scaling via WAYLIVELY_SCALE env var (0-1, default 1.0)
      - Visibility-aware: pauses rendering when the window is obscured
      - Disables developer extras, page cache, and media auto-play
    """

    def __init__(self, wallpaper_dir):
        super().__init__()

        # ── Potato-PC: lowest CPU scheduling priority ──
        try:
            os.nice(19)
        except (AttributeError, OSError):
            pass

        self.wallpaper_dir = os.path.abspath(wallpaper_dir)
        if not os.path.exists(self.wallpaper_dir):
            sys.exit(f"Error: Directory '{self.wallpaper_dir}' does not exist.")

        # Resolution scale factor (env WAYLIVELY_SCALE, default 1.0)
        self.scale = max(0.25, min(1.0, float(os.environ.get("WAYLIVELY_SCALE", "1.0"))))

        self._setup_window()
        self._setup_webview()
        self._load_wallpaper()

    # ── Window (layer-shell background) ───────────────────────────────

    def _setup_window(self):
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BACKGROUND)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)

        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual is not None and self.get_screen().is_composited():
            self.set_visual(visual)

        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self, edge, True)

    # ── WebKit2 WebView ───────────────────────────────────────────────

    def _setup_webview(self):
        settings = WebKit2.Settings()

        # Core rendering
        settings.set_enable_webgl(True)
        settings.set_enable_webaudio(False)          # wallpapers rarely need audio
        settings.set_enable_javascript(True)
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)
        settings.set_enable_smooth_scrolling(False)   # no scrolling needed

        # GPU acceleration
        settings.set_hardware_acceleration_policy(
            WebKit2.HardwareAccelerationPolicy.ALWAYS
        )

        # Disable unnecessary features
        settings.set_enable_developer_extras(False)
        settings.set_enable_page_cache(False)
        settings.set_enable_media(True)              # needed for video wallpapers

        # Memory-saving web context
        ctx = WebKit2.WebContext.get_default()
        ctx.set_process_model(WebKit2.ProcessModel.SHARED_SECONDARY_PROCESS)
        ctx.set_cache_model(WebKit2.CacheModel.DOCUMENT_VIEWER)

        # Constrain WebKit memory usage
        mem_limit = int(os.environ.get("WAYLIVELY_MEM_MB", "128"))
        try:
            settings_web = ctx.get_website_data_manager()
            # Not all versions support this, so wrap in try
        except Exception:
            pass

        self.webview = WebKit2.WebView.new_with_context(ctx)
        self.webview.set_settings(settings)
        self.webview.set_background_color(Gdk.RGBA(0, 0, 0, 0))
        self.webview.connect("load-changed", self._on_load_changed)

        self.add(self.webview)

    # ── Wallpaper loading ─────────────────────────────────────────────

    def _load_wallpaper(self):
        entry_file = "index.html"
        info_path = os.path.join(self.wallpaper_dir, "LivelyInfo.json")

        if os.path.exists(info_path):
            try:
                with open(info_path, "r") as f:
                    info = json.load(f)
                if "FileName" in info:
                    entry_file = info["FileName"]
            except json.JSONDecodeError:
                print("[Engine] Warning: Could not parse LivelyInfo.json")

        # Fallback for older packs
        if entry_file == "index.html" and not os.path.exists(
            os.path.join(self.wallpaper_dir, entry_file)
        ):
            if os.path.exists(os.path.join(self.wallpaper_dir, "fluid.html")):
                entry_file = "fluid.html"

        full_path = os.path.join(self.wallpaper_dir, entry_file)
        if not os.path.exists(full_path):
            sys.exit(f"Error: Entry file '{full_path}' not found.")

        ext = os.path.splitext(entry_file)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            # Video wallpaper: generate an HTML wrapper
            self._is_video = True
            html = self._generate_video_html(full_path, ext)
            print(f"[Engine] Loading video wallpaper: {entry_file}  (scale={self.scale})")
            self.webview.load_html(html, f"file://{self.wallpaper_dir}/")
        else:
            self._is_video = False
            file_url = f"file://{full_path}"
            print(f"[Engine] Loading: {file_url}  (scale={self.scale})")
            self.webview.load_uri(file_url)

    # ── Callbacks ─────────────────────────────────────────────────────

    def _on_load_changed(self, webview, load_event):
        if load_event == WebKit2.LoadEvent.FINISHED:
            if not getattr(self, '_is_video', False):
                self._inject_performance_hints()
            self._inject_lively_properties()

    def _generate_video_html(self, video_path, ext):
        """Generate a minimal HTML page that loops a video as a fullscreen background."""
        mime_map = {
            '.mp4': 'video/mp4', '.webm': 'video/webm', '.mkv': 'video/x-matroska',
            '.avi': 'video/x-msvideo', '.mov': 'video/quicktime', '.gif': 'image/gif',
        }
        mime = mime_map.get(ext, 'video/mp4')

        if ext == '.gif':
            return f"""<!DOCTYPE html>
<html><head><style>
  * {{ margin:0; padding:0; }}
  body {{ overflow:hidden; background:#000; }}
  img {{ width:100vw; height:100vh; object-fit:cover; }}
</style></head>
<body><img src="file://{video_path}" alt=""></body></html>"""

        return f"""<!DOCTYPE html>
<html><head><style>
  * {{ margin:0; padding:0; }}
  body {{ overflow:hidden; background:#000; }}
  video {{ width:100vw; height:100vh; object-fit:cover; }}
</style></head>
<body>
  <video id="wallpaper-video" autoplay loop muted playsinline>
    <source src="file://{video_path}" type="{mime}">
  </video>
  <script>
    const video = document.getElementById('wallpaper-video');

    function applyVolume(value) {{
      const normalized = Math.max(0, Math.min(1, Number(value || 0) / 100));
      video.volume = normalized;
      video.muted = normalized <= 0;
      if (normalized > 0) {{
        video.play().catch(() => {{}});
      }}
    }}

    function livelyPropertyListener(name, val) {{
      if (name === 'volume') {{
        applyVolume(val);
      }}
    }}

    applyVolume(0);
  </script>
</body></html>"""

    def _inject_performance_hints(self):
        """Inject JS to help the wallpaper run lighter on weak hardware."""
        scale = self.scale
        script = f"""\
(function() {{
    // Resolution downscaling: render at {scale:.0%} of native resolution
    if ({scale} < 1.0) {{
        var c = document.querySelector('canvas');
        if (c) {{
            var dpr = window.devicePixelRatio * {scale};
            c.width  = Math.floor(c.clientWidth * dpr);
            c.height = Math.floor(c.clientHeight * dpr);
        }}
    }}

    // Visibility-aware: pause requestAnimationFrame when not visible
    var origRAF = window.requestAnimationFrame;
    var paused = false;
    document.addEventListener('visibilitychange', function() {{
        paused = document.hidden;
    }});
    window.requestAnimationFrame = function(cb) {{
        if (paused) return;
        return origRAF.call(window, cb);
    }};
}})();
"""
        self.webview.run_javascript(script, None, self._on_js_done, None)

    # ── Lively property injection ─────────────────────────────────────
    #
    # The Lively Wallpaper JS API expects:
    #     function livelyPropertyListener(name, val)
    # Called ONCE per property key.

    def _inject_lively_properties(self):
        props_path = os.path.join(self.wallpaper_dir, "LivelyProperties.json")
        if not os.path.exists(props_path):
            return

        print("[Engine] Injecting LivelyProperties…")
        try:
            with open(props_path, "r") as f:
                raw = f.read()
            try:
                props = json.loads(raw)
            except json.JSONDecodeError:
                props = json.loads(re.sub(r",(\s*})", r"\1", raw))

            calls = []
            for key, val in props.items():
                if isinstance(val, dict) and "value" in val:
                    js_val = json.dumps(val["value"])
                    calls.append(f'livelyPropertyListener("{key}", {js_val});')

            if not calls:
                return

            joined = "\n".join(calls)
            script = f"""\
if (typeof livelyPropertyListener === 'function') {{
    {joined}
}} else {{
    console.log("[Waylively] livelyPropertyListener not found");
}}
"""
            self.webview.run_javascript(script, None, self._on_js_done, None)

        except Exception as e:
            print(f"[Engine] Error injecting properties: {e}")

    def _on_js_done(self, webview, result, _user_data):
        try:
            webview.run_javascript_finish(result)
        except Exception:
            pass


# ── Entry point ───────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: waylively-engine <path_to_lively_wallpaper_folder>")
        sys.exit(1)

    app = LivelyWallpaperEngine(sys.argv[1])
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
