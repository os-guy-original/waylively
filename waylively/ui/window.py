import os
import zipfile
import shutil
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, GObject, Gdk

from waylively.utils import config
from waylively.utils import daemon_manager
from waylively.ui.components.card import WallpaperCard


class WallpaperItem(GObject.GObject):
    __gtype_name__ = 'WallpaperItem'
    
    def __init__(self, path, is_default=False):
        super().__init__()
        self.path = path
        self.is_default = is_default


class WaylivelyWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._syncing_daemon_switch = False
        self.set_title("Waylively")
        self.set_default_size(800, 600)

        # Main Layout
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.box)

        self.setup_header()

        # Toast Overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_vexpand(True)
        self.box.append(self.toast_overlay)

        # Scrolled Window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.toast_overlay.set_child(scrolled)

        # Content inside scrolled window
        self.scroll_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scrolled.set_child(self.scroll_content)

        self.wallpaper_store = Gio.ListStore(item_type=WallpaperItem)
        self.selection_model = Gtk.NoSelection.new(self.wallpaper_store)
        
        # Grid View Setup
        self.grid_factory = Gtk.SignalListItemFactory()
        self.grid_factory.connect("setup", self._on_factory_setup)
        self.grid_factory.connect("bind", self._on_grid_bind)
        
        self.grid_view = Gtk.GridView(model=self.selection_model, factory=self.grid_factory)
        self.grid_view.set_max_columns(10)
        self.grid_view.set_min_columns(1)
        self.grid_view.set_margin_top(12)
        self.grid_view.set_margin_bottom(12)
        self.grid_view.set_margin_start(12)
        self.grid_view.set_margin_end(12)
        
        # List View Setup
        self.list_factory = Gtk.SignalListItemFactory()
        self.list_factory.connect("setup", self._on_factory_setup)
        self.list_factory.connect("bind", self._on_list_bind)
        
        self.list_view = Gtk.ListView(model=self.selection_model, factory=self.list_factory)
        self.list_view.set_margin_top(12)
        self.list_view.set_margin_bottom(12)
        self.list_view.set_margin_start(16)
        self.list_view.set_margin_end(16)
        
        # Layout Stack
        self.layout_stack = Gtk.Stack()
        self.layout_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.layout_stack.add_named(self.grid_view, "grid")
        self.layout_stack.add_named(self.list_view, "list")

        self.scroll_content.append(self.layout_stack)

        self.load_wallpapers()

    def _on_factory_setup(self, factory, list_item):
        pass

    def _bind_wallpaper_card(self, list_item, horizontal):
        item = list_item.get_item()
        active_path = config.get_active_wallpaper()
        uninstall_callback = None if item.is_default else self.load_wallpapers
        card = WallpaperCard(
            item.path,
            self.apply_wallpaper,
            on_uninstall_callback=uninstall_callback,
            horizontal=horizontal,
            is_active=bool(active_path and os.path.abspath(item.path) == os.path.abspath(active_path)),
        )
        if horizontal:
            card.set_margin_bottom(12)
        list_item.set_child(card)

    def _on_grid_bind(self, factory, list_item):
        self._bind_wallpaper_card(list_item, horizontal=False)

    def _on_list_bind(self, factory, list_item):
        self._bind_wallpaper_card(list_item, horizontal=True)

    # ── Header & Setup ────────────────────────────────────────────────

    def on_formats_clicked(self, button):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Supported Formats",
            body="• <b>Lively Wallpapers</b> (.zip containing LivelyInfo.json)\n"
                 "• <b>Videos</b> (.mp4, .webm, .mkv, .avi, .mov)\n"
                 "• <b>Animations</b> (.gif)",
        )
        dialog.set_body_use_markup(True)
        dialog.add_response("ok", "Got it")
        dialog.present()

    def setup_header(self):
        self.header = Adw.HeaderBar()
        self.box.append(self.header)

        # Import Button
        imp_btn = Gtk.Button(label="Import")
        imp_btn.set_icon_name("list-add-symbolic")
        imp_btn.connect("clicked", self.on_import_clicked)
        self.header.pack_start(imp_btn)

        # View Toggle
        view_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        view_box.add_css_class("linked")
        view_box.set_valign(Gtk.Align.CENTER)
        
        btn_grid = Gtk.ToggleButton(icon_name="view-grid-symbolic")
        btn_grid.set_active(True)
        btn_grid.connect("toggled", self.on_view_toggled, "grid")
        btn_grid.set_tooltip_text("Grid View")
        
        btn_list = Gtk.ToggleButton(icon_name="view-list-symbolic")
        btn_list.set_group(btn_grid)
        btn_list.connect("toggled", self.on_view_toggled, "list")
        btn_list.set_tooltip_text("List View")
        
        view_box.append(btn_grid)
        view_box.append(btn_list)
        self.header.pack_start(view_box)

        # Formats help button next to Import
        fmt_btn = Gtk.Button(icon_name="help-faq-symbolic")
        fmt_btn.set_tooltip_text("Supported Formats")
        fmt_btn.connect("clicked", self.on_formats_clicked)
        self.header.pack_start(fmt_btn)

        # Daemon Power Toggle
        daemon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        daemon_box.set_valign(Gtk.Align.CENTER)

        daemon_label = Gtk.Label(label="Background Service:")
        daemon_box.append(daemon_label)

        self.daemon_switch = Gtk.Switch()
        self.daemon_switch.set_active(
            daemon_manager.is_service_enabled() or daemon_manager.is_service_active()
        )
        self.daemon_switch.connect("notify::active", self.on_daemon_toggled)
        daemon_box.append(self.daemon_switch)

        self.header.pack_end(daemon_box)

        # Primary Menu (hamburger)
        menu = Gio.Menu()
        menu.append("About Waylively", "win.about")
        
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_btn.set_menu_model(menu)
        menu_btn.set_tooltip_text("Main Menu")
        self.header.pack_end(menu_btn)
        
        # Register the About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_clicked)
        self.add_action(about_action)

    # ── About ─────────────────────────────────────────────────────────

    def on_about_clicked(self, action, param):
        # Register the app icon with the icon theme
        icon_dir = os.path.join(os.path.dirname(__file__), "assets")
        icon_theme = Gtk.IconTheme.get_for_display(self.get_display())
        icon_theme.add_search_path(icon_dir)
        icon_name = "io.github.os_guy_original.Waylively"
        if not icon_theme.has_icon(icon_name):
            icon_name = "icon"

        about = Adw.AboutWindow(
            transient_for=self,
            application_name="Waylively",
            application_icon=icon_name,
            developer_name="Waylively Contributors",
            version="0.1.0-alpha",
            copyright="© 2026 Waylively Contributors",
            license_type=Gtk.License.MIT_X11,
            comments="A native Live Wallpaper manager for Wayland compositors.\n\n"
                     "Supports Lively Wallpaper packages, videos (MP4, WebM, MKV, AVI, MOV), "
                     "GIFs, and HTML5 web wallpapers.",
            website="https://github.com/os-guy-original/waylively",
            issue_url="https://github.com/os-guy-original/waylively/issues",
        )
        about.add_link("Lively Wallpaper (Windows)", "https://www.rocksdanister.com/lively/")
        about.present()

    # ── Daemon ────────────────────────────────────────────────────────

    def _set_daemon_switch_state(self, active):
        self._syncing_daemon_switch = True
        self.daemon_switch.set_active(active)
        self._syncing_daemon_switch = False

    def on_daemon_toggled(self, switch, gparam):
        if self._syncing_daemon_switch:
            return

        if switch.get_active():
            if daemon_manager.enable_service():
                self.toast_overlay.add_toast(Adw.Toast(title="Background Service Enabled"))
            else:
                self._set_daemon_switch_state(False)
                self.toast_overlay.add_toast(Adw.Toast(title="Failed to enable background service"))
        else:
            if daemon_manager.disable_service():
                self.toast_overlay.add_toast(Adw.Toast(title="Background Service Disabled"))
            else:
                self._set_daemon_switch_state(True)
                self.toast_overlay.add_toast(Adw.Toast(title="Failed to disable background service"))

    # ── View Mode ─────────────────────────────────────────────────────

    def on_view_toggled(self, btn, view_name):
        if btn.get_active():
            self.layout_stack.set_visible_child_name(view_name)

    # ── Wallpaper Loading ─────────────────────────────────────────────

    def load_wallpapers(self):
        self.wallpaper_store.remove_all()
        config.ensure_dirs()
        bundled_paths = config.ensure_bundled_wallpapers()
        bundled_names = {os.path.basename(path) for path in bundled_paths}

        for bundled_path in bundled_paths:
            if os.path.exists(bundled_path):
                self.wallpaper_store.append(WallpaperItem(bundled_path, is_default=True))

        # 2) Discover and add User Imported Wallpapers
        if os.path.exists(config.WALLPAPERS_DIR):
            for wp_dir in sorted(os.listdir(config.WALLPAPERS_DIR)):
                if wp_dir in bundled_names:
                    continue
                full_path = os.path.join(config.WALLPAPERS_DIR, wp_dir)
                if os.path.isdir(full_path):
                    self.wallpaper_store.append(WallpaperItem(full_path, is_default=False))

    # ── Import ────────────────────────────────────────────────────────

    def on_import_clicked(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Import Wallpaper")

        filters = Gio.ListStore.new(Gtk.FileFilter)

        f_all = Gtk.FileFilter()
        f_all.set_name("All Supported (ZIP, MP4, WebM, MKV, GIF, AVI, MOV)")
        f_all.add_mime_type("application/zip")
        f_all.add_mime_type("video/mp4")
        f_all.add_mime_type("video/webm")
        f_all.add_mime_type("video/x-matroska")
        f_all.add_mime_type("image/gif")
        f_all.add_mime_type("video/x-msvideo")
        f_all.add_mime_type("video/quicktime")
        filters.append(f_all)

        f_zip = Gtk.FileFilter()
        f_zip.set_name("Lively Zip Archives")
        f_zip.add_mime_type("application/zip")
        filters.append(f_zip)

        f_vid = Gtk.FileFilter()
        f_vid.set_name("Video Files")
        f_vid.add_mime_type("video/mp4")
        f_vid.add_mime_type("video/webm")
        f_vid.add_mime_type("video/x-matroska")
        f_vid.add_mime_type("video/x-msvideo")
        f_vid.add_mime_type("video/quicktime")
        f_vid.add_mime_type("image/gif")
        filters.append(f_vid)

        dialog.set_filters(filters)
        dialog.open(self, None, self.on_file_selected)

    def on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                filepath = file.get_path()
                ext = os.path.splitext(filepath)[1].lower()
                if ext == '.zip':
                    self.import_zip(filepath)
                elif ext in {'.mp4', '.webm', '.mkv', '.avi', '.mov', '.gif'}:
                    self.import_media_file(filepath)
                else:
                    self.toast_overlay.add_toast(Adw.Toast(title=f"Unsupported format: {ext}"))
        except GLib.Error:
            pass

    def import_zip(self, zip_path):
        filename = os.path.basename(zip_path)
        folder_name = os.path.splitext(filename)[0]
        extract_dir = os.path.join(config.WALLPAPERS_DIR, folder_name)

        try:
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            props_target = os.path.join(extract_dir, "LivelyProperties.json")
            if os.path.exists(props_target):
                shutil.copy2(props_target, os.path.join(extract_dir, "LivelyProperties.bak.json"))

            self.toast_overlay.add_toast(Adw.Toast(title=f"Imported {folder_name}"))
            self.load_wallpapers()
        except zipfile.BadZipFile:
            self.toast_overlay.add_toast(Adw.Toast(title="Error: Invalid zip file"))
            shutil.rmtree(extract_dir, ignore_errors=True)

    def import_media_file(self, media_path):
        """Import a single video/GIF file as a wallpaper."""
        import json as _json
        filename = os.path.basename(media_path)
        folder_name = os.path.splitext(filename)[0]
        extract_dir = os.path.join(config.WALLPAPERS_DIR, folder_name)

        try:
            os.makedirs(extract_dir, exist_ok=True)
            dest = os.path.join(extract_dir, filename)
            shutil.copy2(media_path, dest)

            # Generate LivelyInfo.json
            info = {
                "AppVersion": "1.0.0",
                "Title": folder_name,
                "Thumbnail": "",
                "Desc": f"{os.path.splitext(filename)[1].upper().lstrip('.')} Wallpaper",
                "Author": "",
                "License": "",
                "Type": 3,
                "FileName": filename,
            }
            with open(os.path.join(extract_dir, "LivelyInfo.json"), "w") as f:
                _json.dump(info, f, indent=2)

            config.ensure_video_properties(extract_dir)

            self.toast_overlay.add_toast(Adw.Toast(title=f"Imported {folder_name}"))
            self.load_wallpapers()
        except Exception as e:
            self.toast_overlay.add_toast(Adw.Toast(title=f"Error: {e}"))
            shutil.rmtree(extract_dir, ignore_errors=True)

    # ── Apply ─────────────────────────────────────────────────────────

    def apply_wallpaper(self, path, title):
        config.set_active_wallpaper(path)

        service_ready = daemon_manager.is_service_active() or daemon_manager.enable_service()
        self._set_daemon_switch_state(service_ready)

        if service_ready:
            self.toast_overlay.add_toast(Adw.Toast(title=f"Applied {title}"))
        else:
            self.toast_overlay.add_toast(
                Adw.Toast(title=f"Selected {title}, but failed to start the background service")
            )

        self.load_wallpapers()
