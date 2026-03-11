import os
import sys
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, GLib


def take_screenshot(html_path, output_path):
    window = Gtk.OffscreenWindow()
    window.set_default_size(1280, 720)

    webview = WebKit2.WebView()
    settings = webview.get_settings()
    settings.set_enable_webgl(True)
    settings.set_enable_javascript(True)
    window.add(webview)
    webview.load_uri("file://" + os.path.abspath(html_path))

    def on_load_changed(view, event):
        if event == WebKit2.LoadEvent.FINISHED:
            GLib.timeout_add(1500, do_snapshot)

    def do_snapshot():
        webview.get_snapshot(
            WebKit2.SnapshotRegion.VISIBLE,
            WebKit2.SnapshotOptions.NONE,
            None,
            on_snapshot_ready,
        )
        return False

    def on_snapshot_ready(view, result):
        try:
            surface = view.get_snapshot_finish(result)
            if surface:
                surface.write_to_png(output_path)
        except Exception as e:
            print(f"Failed snapshot: {e}")
        finally:
            Gtk.main_quit()

    webview.connect("load-changed", on_load_changed)
    window.show_all()
    GLib.timeout_add_seconds(10, Gtk.main_quit)
    Gtk.main()


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("Usage: waylively-screenshot <html_path> <output_path>", file=sys.stderr)
        return 1
    take_screenshot(args[0], args[1])
    return 0