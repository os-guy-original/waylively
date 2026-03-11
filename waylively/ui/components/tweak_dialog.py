import os
import json
import re
import copy
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Gio

from waylively.utils import config
from waylively.utils import daemon_manager


class WallpaperTweaksWindow(Adw.Window):
    """
    Dynamically builds UI controls from LivelyProperties.json.
    
    Supports: slider, checkbox, color, text, font, folderDropdown (file picker).
    Features a Discord-style floating change bar and bottom Reset button.
    """

    def __init__(self, wallpaper_path, wallpaper_title, **kwargs):
        super().__init__(**kwargs)
        self.wallpaper_path = config.resolve_writable_wallpaper_path(wallpaper_path)
        self.wallpaper_title = wallpaper_title
        self.props_path = os.path.join(self.wallpaper_path, "LivelyProperties.json")
        self.backup_path = os.path.join(self.wallpaper_path, "LivelyProperties.bak.json")

        self.set_title(f"Tweaks — {wallpaper_title}")
        self.set_default_size(520, 640)

        self.properties = {}
        self.saved_properties = {}
        self.pending_changes = 0

        self._load_properties()
        self.saved_properties = copy.deepcopy(self.properties)

        self._build_ui()

    # ── Data I/O ──────────────────────────────────────────────────────

    def _load_properties(self):
        config.ensure_video_properties(self.wallpaper_path)
        if not os.path.exists(self.props_path):
            return
        try:
            with open(self.props_path, 'r') as f:
                raw = f.read()
            try:
                self.properties = json.loads(raw)
            except json.JSONDecodeError:
                fixed = re.sub(r',(\s*})', r'\1', raw)
                self.properties = json.loads(fixed)
        except Exception as e:
            print(f"[Tweaks] Error loading properties: {e}")

    def _save_properties(self):
        try:
            with open(self.props_path, 'w') as f:
                json.dump(self.properties, f, indent=2)
            self.saved_properties = copy.deepcopy(self.properties)
            self.pending_changes = 0
            self._update_change_bar()

            if config.get_active_wallpaper() == self.wallpaper_path:
                if daemon_manager.is_service_active() or daemon_manager.is_service_enabled():
                    daemon_manager.restart_service()

            self._show_toast("Settings saved ✓")
        except Exception as e:
            self._show_toast(f"Error saving: {e}")

    def _revert_properties(self):
        self.properties = copy.deepcopy(self.saved_properties)
        self.pending_changes = 0
        self._update_change_bar()
        self._rebuild_controls()
        self._show_toast("Reverted to last saved state")

    def _reset_to_defaults(self):
        if not os.path.exists(self.backup_path):
            self._show_toast("No defaults backup found")
            return
        try:
            with open(self.backup_path, 'r') as f:
                raw = f.read()
            try:
                self.properties = json.loads(raw)
            except json.JSONDecodeError:
                self.properties = json.loads(re.sub(r',(\s*})', r'\1', raw))
            self.pending_changes = self._count_diffs()
            self._update_change_bar()
            self._rebuild_controls()
            self._show_toast("Reset to defaults — click Save to apply")
        except Exception as e:
            self._show_toast(f"Error resetting: {e}")

    def _mark_changed(self):
        self.pending_changes = self._count_diffs()
        self._update_change_bar()

    def _count_diffs(self):
        count = 0
        for key in self.properties:
            prop = self.properties[key]
            saved = self.saved_properties.get(key, {})
            if isinstance(prop, dict) and isinstance(saved, dict):
                if prop.get("value") != saved.get("value"):
                    count += 1
        return count

    def _show_toast(self, msg):
        self.toast_overlay.add_toast(Adw.Toast(title=msg))

    # ── UI Building ───────────────────────────────────────────────────

    def _build_ui(self):
        # Root layout
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root_box)

        # Header bar
        header = Adw.HeaderBar()
        root_box.append(header)

        # Toast overlay wrapping everything
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_vexpand(True)
        root_box.append(self.toast_overlay)

        # Overlay for the floating change bar
        self.overlay = Gtk.Overlay()
        self.toast_overlay.set_child(self.overlay)

        # Scrolled content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.overlay.set_child(scrolled)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scrolled.set_child(self.content_box)

        # Controls list
        self.controls_group = Adw.PreferencesGroup()
        self.controls_group.set_title("Wallpaper Settings")
        self.controls_group.set_margin_top(12)
        self.controls_group.set_margin_start(12)
        self.controls_group.set_margin_end(12)
        self.content_box.append(self.controls_group)

        self._populate_controls()

        # ── Reset to Defaults button at the BOTTOM ──
        reset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        reset_box.set_halign(Gtk.Align.CENTER)
        reset_box.set_margin_top(24)
        reset_box.set_margin_bottom(24)

        btn_reset = Gtk.Button(label="Reset to Defaults")
        btn_reset.add_css_class("destructive-action")
        btn_reset.connect("clicked", lambda _: self._reset_to_defaults())
        reset_box.append(btn_reset)
        self.content_box.append(reset_box)

        # ── Discord-style floating change bar ──
        self.change_bar = Gtk.Revealer()
        self.change_bar.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.change_bar.set_transition_duration(200)
        self.change_bar.set_valign(Gtk.Align.END)
        self.change_bar.set_halign(Gtk.Align.CENTER)
        self.change_bar.set_margin_bottom(16)
        self.change_bar.set_reveal_child(False)

        bar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar_box.add_css_class("card")
        bar_box.set_margin_start(12)
        bar_box.set_margin_end(12)
        bar_box.set_margin_top(8)
        bar_box.set_margin_bottom(8)

        # Inner padding
        bar_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar_inner.set_margin_start(16)
        bar_inner.set_margin_end(16)
        bar_inner.set_margin_top(10)
        bar_inner.set_margin_bottom(10)

        self.change_label = Gtk.Label(label="0 unsaved changes")
        self.change_label.set_hexpand(True)
        self.change_label.set_halign(Gtk.Align.START)
        bar_inner.append(self.change_label)

        btn_revert = Gtk.Button(label="Revert")
        btn_revert.connect("clicked", lambda _: self._revert_properties())
        bar_inner.append(btn_revert)

        btn_save = Gtk.Button(label="Save")
        btn_save.add_css_class("suggested-action")
        btn_save.connect("clicked", lambda _: self._save_properties())
        bar_inner.append(btn_save)

        bar_box.append(bar_inner)
        self.change_bar.set_child(bar_box)
        self.overlay.add_overlay(self.change_bar)

    def _update_change_bar(self):
        if self.pending_changes > 0:
            n = self.pending_changes
            self.change_label.set_label(
                f"{n} unsaved change{'s' if n != 1 else ''}"
            )
            self.change_bar.set_reveal_child(True)
        else:
            self.change_bar.set_reveal_child(False)

    def _rebuild_controls(self):
        self.content_box.remove(self.controls_group)
        # Remove old reset box and re-add after new controls
        # Simplest: rebuild the whole content_box children
        # We need to keep the reset box, so let's just rebuild controls_group
        new_group = Adw.PreferencesGroup()
        new_group.set_title("Wallpaper Settings")
        new_group.set_margin_top(12)
        new_group.set_margin_start(12)
        new_group.set_margin_end(12)

        self.controls_group = new_group
        self.content_box.prepend(self.controls_group)
        self._populate_controls()

    def _populate_controls(self):
        if not self.properties:
            row = Adw.ActionRow()
            row.set_title("No tweakable properties found.")
            self.controls_group.add(row)
            return

        for key, prop in self.properties.items():
            if not isinstance(prop, dict) or "type" not in prop:
                continue

            p_type = prop["type"].lower()
            text = prop.get("text", key)
            val = prop.get("value")

            row = Adw.ActionRow()
            row.set_title(text)

            if p_type == "slider":
                scale = Gtk.Scale.new_with_range(
                    Gtk.Orientation.HORIZONTAL,
                    prop.get("min", 0),
                    prop.get("max", 100),
                    prop.get("step", 1),
                )
                scale.set_value(float(val) if val is not None else 0)
                scale.set_hexpand(True)
                scale.set_size_request(200, -1)
                scale.set_valign(Gtk.Align.CENTER)

                def on_slider(widget, k=key):
                    self.properties[k]["value"] = widget.get_value()
                    self._mark_changed()
                scale.connect("value-changed", on_slider)
                row.add_suffix(scale)

            elif p_type == "checkbox":
                switch = Gtk.Switch()
                switch.set_active(bool(val))
                switch.set_valign(Gtk.Align.CENTER)

                def on_switch(widget, gparam, k=key):
                    self.properties[k]["value"] = widget.get_active()
                    self._mark_changed()
                switch.connect("notify::active", on_switch)
                row.add_suffix(switch)

            elif p_type == "color":
                rgba = Gdk.RGBA()
                if val and isinstance(val, str):
                    rgba.parse(val)
                else:
                    rgba.parse("#000000")

                cb = Gtk.ColorButton()
                cb.set_rgba(rgba)
                cb.set_valign(Gtk.Align.CENTER)

                def on_color(widget, k=key):
                    c = widget.get_rgba()
                    self.properties[k]["value"] = (
                        f"#{int(c.red*255):02x}{int(c.green*255):02x}{int(c.blue*255):02x}"
                    )
                    self._mark_changed()
                cb.connect("color-set", on_color)
                row.add_suffix(cb)

            elif p_type == "text":
                entry = Gtk.Entry()
                entry.set_text(str(val) if val is not None else "")
                entry.set_hexpand(True)
                entry.set_size_request(220, -1)
                entry.set_valign(Gtk.Align.CENTER)

                def on_text(widget, k=key):
                    self.properties[k]["value"] = widget.get_text()
                    self._mark_changed()
                entry.connect("changed", on_text)
                row.add_suffix(entry)

            elif p_type == "font":
                font_btn = Gtk.FontButton()
                font_btn.set_use_font(True)
                if val:
                    font_btn.set_font(str(val))
                font_btn.set_valign(Gtk.Align.CENTER)

                def on_font(widget, k=key):
                    self.properties[k]["value"] = widget.get_font()
                    self._mark_changed()
                font_btn.connect("font-set", on_font)
                row.add_suffix(font_btn)

            elif p_type == "folderdropdown" or (
                isinstance(val, str) and (os.sep in str(val) or val.endswith("/"))
            ):
                # File/folder picker
                path_label = Gtk.Label(label=str(val) if val else "Not set")
                path_label.set_ellipsize(2)  # MIDDLE
                path_label.set_max_width_chars(20)
                path_label.set_valign(Gtk.Align.CENTER)

                browse_btn = Gtk.Button(icon_name="folder-open-symbolic")
                browse_btn.set_valign(Gtk.Align.CENTER)

                def on_browse(widget, k=key, lbl=path_label):
                    dialog = Gtk.FileDialog()
                    dialog.set_title(f"Select path for {k}")
                    dialog.select_folder(self, None, self._on_folder_selected, k, lbl)
                browse_btn.connect("clicked", on_browse)

                suffix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                suffix_box.append(path_label)
                suffix_box.append(browse_btn)
                row.add_suffix(suffix_box)

            elif p_type == "dropdown":
                items = prop.get("items", [])
                if items:
                    string_list = Gtk.StringList()
                    for item in items:
                        string_list.append(str(item))
                    dropdown = Gtk.DropDown(model=string_list)
                    if val is not None:
                        try:
                            dropdown.set_selected(int(val))
                        except (ValueError, TypeError):
                            pass
                    dropdown.set_valign(Gtk.Align.CENTER)

                    def on_dropdown(widget, gparam, k=key):
                        self.properties[k]["value"] = widget.get_selected()
                        self._mark_changed()
                    dropdown.connect("notify::selected", on_dropdown)
                    row.add_suffix(dropdown)
                else:
                    lbl = Gtk.Label(label=str(val))
                    lbl.set_valign(Gtk.Align.CENTER)
                    row.add_suffix(lbl)

            else:
                lbl = Gtk.Label(label=str(val))
                lbl.set_valign(Gtk.Align.CENTER)
                row.add_suffix(lbl)

            self.controls_group.add(row)

    def _on_folder_selected(self, dialog, result, key, label):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self.properties[key]["value"] = path
                label.set_label(path)
                self._mark_changed()
        except Exception:
            pass
