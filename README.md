<p align="center">
  <img src="waylively/ui/assets/icon.png" alt="Waylively icon" width="128">
</p>

# 🌊 Waylively

**Native Live Wallpapers for Wayland**

> ⚠️ **Early alpha** — tested on Hyprland. Other wlroots compositors should work but are untested.

> This project is **not** affiliated with [Lively Wallpaper](https://github.com/rocksdanister/lively).

## What it does

Renders live wallpapers (HTML5, videos, GIFs) as your Wayland desktop background using `gtk-layer-shell`.

**Supports:** Lively `.zip` packages · MP4 · WebM · MKV · AVI · MOV · GIF

---

## Install

### AppImage (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/os-guy-original/waylively/main/scripts/install-appimage.sh | bash
```

This installs the latest AppImage to `~/.local/opt/waylively/`, adds launch wrappers in
`~/.local/bin/`, creates a desktop entry, and installs a user systemd unit at
`~/.config/systemd/user/waylively.service`.

After install, launch `waylively-manager` and use the **Background Service** toggle,
or enable it directly with `systemctl --user enable --now waylively.service`.

### Build AppImage manually

From the repository root, or from anywhere via the script path:

```bash
bash scripts/build-appimage.sh
```

This writes the AppImage to `dist/` and downloads `appimagetool` into `.cache/appimage/`
on first use.

### Manual (Arch Linux)

```bash
# Install dependencies
sudo pacman -S python-gobject gtk4 libadwaita gtk3 webkit2gtk-4.1 gtk-layer-shell ffmpeg

# Clone and run
git clone https://github.com/os-guy-original/waylively.git
cd waylively
./bin/waylively
```

### pip (system-wide)

```bash
pip install .
waylively-manager
```

---

## Usage

1. Launch the manager → toggle **Background Service** on
2. **Import** a `.zip` wallpaper or video/GIF file
3. **Apply** any card to set it as your wallpaper
4. **⚙️ Tweak** shader properties (if the wallpaper supports it)

## Dependencies

| Package | For |
|---|---|
| `python-gobject` | Python GTK bindings |
| `gtk4`, `libadwaita` | Manager UI |
| `gtk3`, `webkit2gtk-4.1` | Wallpaper renderer |
| `gtk-layer-shell` | Wayland background layer |
| `ffmpeg` | Video thumbnails |

## License

[MIT](LICENSE)
