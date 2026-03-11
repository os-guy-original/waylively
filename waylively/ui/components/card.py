import os
import json
import shutil
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Pango

from waylively.ui.components.tweak_dialog import WallpaperTweaksWindow
from waylively.utils.thumbnailer import generate_thumbnail
from waylively.utils.config import VIDEO_EXTENSIONS, ensure_video_properties


def detect_format(wallpaper_path):
    """Detect the wallpaper format and return (format_label, entry_file)."""
    info_path = os.path.join(wallpaper_path, "LivelyInfo.json")
    
    # Check LivelyInfo.json first
    if os.path.exists(info_path):
        try:
            with open(info_path, 'r') as f:
                info = json.load(f)
            fname = info.get("FileName", "")
            ext = os.path.splitext(fname)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                return ext.lstrip('.').upper(), fname
            elif ext in ('.html', '.htm'):
                return "Lively", fname
        except Exception:
            pass
    
    # Scan for video files directly in the folder
    for f in os.listdir(wallpaper_path):
        ext = os.path.splitext(f)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            return ext.lstrip('.').upper(), f
    
    # Scan for HTML files
    for f in os.listdir(wallpaper_path):
        if f.endswith('.html') or f.endswith('.htm'):
            return "Lively", f
    
    return "Unknown", None


class WallpaperCard(Gtk.Box):
    def __init__(self, path, on_apply_callback, on_uninstall_callback=None, horizontal=False, is_active=False, **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL if horizontal else Gtk.Orientation.VERTICAL, spacing=16 if horizontal else 0, **kwargs)
        self.path = path
        self.on_apply_callback = on_apply_callback
        self.on_uninstall_callback = on_uninstall_callback
        self.horizontal = horizontal
        self.is_active = is_active
        
        self.title_text = os.path.basename(path)
        self.desc_text = "Lively Wallpaper"
        self.thumbnail_path = None
        self.has_tweaks = False
        self.format_label = "Unknown"
        self.entry_file = None
        self.info_dict = {}
        
        self.add_css_class("card")
        self.set_halign(Gtk.Align.FILL if horizontal else Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.START)
        
        self.parse_info()
        self.build_ui()
        
    def parse_info(self):
        self.format_label, self.entry_file = detect_format(self.path)
        
        info_path = os.path.join(self.path, "LivelyInfo.json")
        if os.path.exists(info_path):
            try:
                with open(info_path, 'r') as f:
                    self.info_dict = json.load(f)
                    self.title_text = self.info_dict.get("Title", self.title_text)
                    self.desc_text = self.info_dict.get("Desc", self.desc_text)
                    
                    if self.info_dict.get("Thumbnail"):
                         t_path = os.path.join(self.path, self.info_dict["Thumbnail"])
                         if os.path.isfile(t_path):
                             self.thumbnail_path = t_path
            except Exception:
                pass
                
        props_path = os.path.join(self.path, "LivelyProperties.json")
        if os.path.exists(props_path) or ensure_video_properties(self.path):
            self.has_tweaks = True

        if not self.thumbnail_path:
            auto_thumb = generate_thumbnail(self.path)
            if auto_thumb:
                self.thumbnail_path = auto_thumb

    def build_ui(self):
        if not self.horizontal:
            self.set_size_request(280, 340)
            self.set_hexpand(False)
            self.set_overflow(Gtk.Overflow.HIDDEN)
            # Enforce exact width via CSS
            css = Gtk.CssProvider()
            css.load_from_data(b"box { max-width: 280px; }")
            self.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            
        thumb_width = 240 if self.horizontal else 280
        thumb_height = 135 if self.horizontal else 157
        
        # ── Thumbnail area with format badge overlay ──
        thumb_overlay = Gtk.Overlay()
        thumb_overlay.set_size_request(thumb_width, thumb_height)
        
        if self.thumbnail_path:
            picture = Gtk.Picture.new_for_filename(self.thumbnail_path)
            picture.set_size_request(thumb_width, thumb_height)
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            # Add inline CSS for border radius correctly
            css_provider = Gtk.CssProvider()
            if self.horizontal:
                css_provider.load_from_data(b"""
                    picture {
                        border-top-left-radius: 12px;
                        border-bottom-left-radius: 12px;
                    }
                """)
            else:
                css_provider.load_from_data(b"""
                    picture {
                        border-top-left-radius: 12px;
                        border-top-right-radius: 12px;
                    }
                """)
            picture.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            thumb_overlay.set_child(picture)
        else:
            placeholder = Gtk.Box()
            placeholder.set_size_request(thumb_width, thumb_height)
            thumb_overlay.set_child(placeholder)
        
        # Format badge (top-left right-triangle)
        da = Gtk.DrawingArea()
        badge_size = 48 if self.horizontal else 56
        da.set_size_request(badge_size, badge_size)
        da.set_halign(Gtk.Align.START)
        da.set_valign(Gtk.Align.START)
        
        badge_colors = {
            "MP4": "#e05d44",
            "WEBM": "#44cc11",
            "MKV": "#007ec6",
            "GIF": "#fe7d37",
            "AVI": "#9f78c4",
            "MOV": "#dfb317",
            "LIVELY": "#3584e4",
        }
        hex_color = badge_colors.get(self.format_label.upper(), "#555555")
        color_r = int(hex_color[1:3], 16) / 255.0
        color_g = int(hex_color[3:5], 16) / 255.0
        color_b = int(hex_color[5:7], 16) / 255.0
        short_labels = {
            "MP4": "MP4",
            "WEBM": "WBM",
            "MKV": "MKV",
            "GIF": "GIF",
            "AVI": "AVI",
            "MOV": "MOV",
            "LIVELY": "LV",
        }
        label_text = short_labels.get(self.format_label.upper(), self.format_label.upper()[:3])
        horizontal_layout = self.horizontal # Copy for scope

        def draw_triangle(area, cr, width, height):
            import math
            cr.set_source_rgba(color_r, color_g, color_b, 0.95)
            cr.new_path()
            if horizontal_layout:
                cr.move_to(0, 48)
                cr.line_to(0, 12)
                cr.arc(12, 12, 12, math.pi, 1.5 * math.pi)
                cr.line_to(48, 0)
            else:
                cr.move_to(0, 56)
                cr.line_to(0, 10)
                cr.arc(10, 10, 10, math.pi, 1.5 * math.pi)
                cr.line_to(56, 0)
            cr.fill()
            
            cr.set_source_rgb(1, 1, 1)
            cr.set_font_size(9 if horizontal_layout else 10)
            cr.select_font_face("sans-serif", 0, 1) # normal, bold
            
            cr.save()
            if horizontal_layout:
                cr.translate(12, 18)
            else:
                cr.translate(16, 22)
            cr.rotate(-math.pi / 4)
            offset = -8 if len(label_text) > 2 else -2
            cr.move_to(offset, 0)
            cr.show_text(label_text)
            cr.restore()

        da.set_draw_func(draw_triangle)
        thumb_overlay.add_overlay(da)

        if self.is_active:
            active_badge = Gtk.DrawingArea()
            active_badge.set_size_request(badge_size, badge_size)
            active_badge.set_halign(Gtk.Align.END)
            active_badge.set_valign(Gtk.Align.START)

            def draw_active_triangle(area, cr, width, height):
                cr.set_source_rgba(0.20, 0.73, 0.36, 0.96)
                cr.new_path()
                cr.move_to(0, 0)
                cr.line_to(width, 0)
                cr.line_to(width, height)
                cr.close_path()
                cr.fill()

                cr.set_source_rgb(1, 1, 1)
                cr.set_line_width(2.0 if horizontal_layout else 2.3)
                cr.set_line_cap(1)
                cr.set_line_join(1)
                if horizontal_layout:
                    cr.move_to(width * 0.56, height * 0.38)
                    cr.line_to(width * 0.66, height * 0.50)
                    cr.line_to(width * 0.82, height * 0.28)
                else:
                    cr.move_to(width * 0.58, height * 0.40)
                    cr.line_to(width * 0.68, height * 0.52)
                    cr.line_to(width * 0.84, height * 0.30)
                cr.stroke()

            active_badge.set_draw_func(draw_active_triangle)
            thumb_overlay.add_overlay(active_badge)

        self.append(thumb_overlay)
        
        # ── Text Details ──
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4 if self.horizontal else 2)
        if self.horizontal:
            text_box.set_margin_top(12)
            text_box.set_margin_bottom(12)
            text_box.set_margin_end(16)
            text_box.set_hexpand(True)
        else:
            text_box.set_margin_top(8)
            text_box.set_margin_start(12)
            text_box.set_margin_end(12)
            text_box.set_size_request(-1, 52)  # Fixed height for description area
        
        lbl_title = Gtk.Label(label=self.title_text, halign=Gtk.Align.START)
        lbl_title.set_ellipsize(Pango.EllipsizeMode.END)
        lbl_title.set_max_width_chars(32 if self.horizontal else 24)
        lbl_title.add_css_class("title-4")
        
        lbl_desc = Gtk.Label(label=self.desc_text, halign=Gtk.Align.START)
        lbl_desc.add_css_class("dim-label")
        if self.horizontal:
            lbl_desc.set_wrap(True)
            lbl_desc.set_wrap_mode(Pango.WrapMode.WORD)
            lbl_desc.set_lines(2)
            lbl_desc.set_ellipsize(Pango.EllipsizeMode.END)
        else:
            lbl_desc.set_wrap(False)
            lbl_desc.set_ellipsize(Pango.EllipsizeMode.END)
            lbl_desc.set_max_width_chars(30)
        
        text_box.append(lbl_title)
        text_box.append(lbl_desc)
        
        if not self.horizontal:
            self.append(text_box)
        
        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        if self.horizontal:
            text_box.append(spacer)
        else:
            self.append(spacer)
        
        # ── Bottom controls ──
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6 if self.horizontal else 4)
        if not self.horizontal:
            bottom_box.set_margin_top(12)
            bottom_box.set_margin_bottom(12)
            bottom_box.set_margin_start(12)
            bottom_box.set_margin_end(12)
        
        btn_info = Gtk.Button(icon_name="dialog-information-symbolic")
        btn_info.add_css_class("flat")
        btn_info.set_tooltip_text("Wallpaper Information")
        btn_info.connect("clicked", self.on_info_clicked)
        bottom_box.append(btn_info)
        
        if self.has_tweaks:
            btn_tweaks = Gtk.Button(icon_name="emblem-system-symbolic")
            btn_tweaks.add_css_class("flat")
            btn_tweaks.set_tooltip_text("Tweak settings")
            btn_tweaks.connect("clicked", self.on_tweaks_clicked)
            bottom_box.append(btn_tweaks)
            
        h_spacer = Gtk.Box()
        h_spacer.set_hexpand(True)
        bottom_box.append(h_spacer)
        
        if self.on_uninstall_callback is not None:
            btn_uninstall = Gtk.Button(icon_name="user-trash-symbolic")
            if not self.horizontal:
                btn_uninstall.set_margin_end(4)
            btn_uninstall.add_css_class("flat")
            btn_uninstall.set_tooltip_text("Uninstall wallpaper")
            btn_uninstall.connect("clicked", self.on_uninstall_clicked)
            bottom_box.append(btn_uninstall)
        
        btn_apply = Gtk.Button(label="Apply")
        btn_apply.add_css_class("suggested-action")
        btn_apply.connect("clicked", lambda x: self.on_apply_callback(self.path, self.title_text))
        bottom_box.append(btn_apply)
        
        if self.horizontal:
            text_box.append(bottom_box)
            self.append(text_box)
        else:
            self.append(bottom_box)
        
    def _has_lively_metadata(self):
        """Check if the wallpaper has real Lively metadata (not auto-generated stubs)."""
        author = self.info_dict.get("Author", "")
        return bool(author and author.strip())

    def on_info_clicked(self, button):
        if not self._has_lively_metadata():
            # Show basic file properties for plain media files
            entry = os.path.join(self.path, self.entry_file) if self.entry_file else None
            try:
                size_bytes = os.path.getsize(entry) if entry and os.path.isfile(entry) else 0
                if size_bytes >= 1024 * 1024:
                    size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
                elif size_bytes >= 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes} B"
            except Exception:
                size_str = "Unknown"
            markup = (f"<b>Format:</b> {self.format_label.upper()}\n"
                      f"<b>File:</b> {self.entry_file or 'Unknown'}\n"
                      f"<b>Size:</b> {size_str}\n"
                      f"<b>Location:</b> {self.path}")
            contact = None
        else:
            # Show rich Lively metadata
            author = self.info_dict.get("Author", "Unknown")
            license_txt = self.info_dict.get("License", "Unknown")
            contact = self.info_dict.get("Contact", "") or None
            
            markup = f"<b>Author:</b> {author}\n<b>License:</b> {license_txt}"
            if contact:
                markup += f"\n<b>Contact:</b> {contact}"
            markup += f"\n<b>Location:</b> {self.path}"
            
        dialog = Adw.MessageDialog(
            heading=self.title_text,
            body=markup,
        )
        dialog.set_body_use_markup(True)
        
        root = self.get_root()
        if isinstance(root, Gtk.Window):
            dialog.set_transient_for(root)
            
        is_link = False
        if contact and isinstance(contact, str):
            is_link = contact.startswith("http://") or contact.startswith("https://")
            
        if is_link:
            dialog.add_response("open", "Open Link")
            dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
            
        dialog.add_response("ok", "Close")
        
        def on_response(dlg, response):
            if response == "open" and contact:
                import webbrowser
                webbrowser.open_new_tab(contact)
                
        dialog.connect("response", on_response)
        dialog.present()

    def on_tweaks_clicked(self, button):
        win = WallpaperTweaksWindow(self.path, self.title_text)
        root = self.get_root()
        if isinstance(root, Gtk.Window):
            win.set_transient_for(root)
        win.present()

    def on_uninstall_clicked(self, button):
        dialog = Adw.MessageDialog(
            heading=f"Uninstall '{self.title_text}'?",
            body="This will permanently delete the wallpaper files.",
        )
        root = self.get_root()
        if isinstance(root, Gtk.Window):
            dialog.set_transient_for(root)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("uninstall", "Uninstall")
        dialog.set_response_appearance("uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_uninstall_confirmed)
        dialog.present()

    def _on_uninstall_confirmed(self, dialog, response):
        if response == "uninstall":
            try:
                shutil.rmtree(self.path, ignore_errors=True)
            except Exception:
                pass
            if self.on_uninstall_callback:
                self.on_uninstall_callback()
        
    def get_widget(self):
        return self
