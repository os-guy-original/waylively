import os
import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk, Gdk

from waylively.ui.window import WaylivelyWindow

APP_ID = "io.github.os_guy_original.Waylively"

class WaylivelyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.load_css()
        
        # Set the Custom Theme Icon
        assets_path = os.path.join(os.path.dirname(__file__), "assets")
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        if os.path.exists(os.path.join(assets_path, "icon.svg")):
             icon_theme.add_search_path(assets_path)

        icon_name = APP_ID if icon_theme.has_icon(APP_ID) else "icon"
        Gtk.Window.set_default_icon_name(icon_name)
             
        self.win = WaylivelyWindow(application=app)
        self.win.present()

    def load_css(self):
        css_provider = Gtk.CssProvider()
        css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
        if os.path.exists(css_path):
            css_provider.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), 
                css_provider, 
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

def main():
    app = WaylivelyApp(application_id=APP_ID)
    return app.run(sys.argv)
