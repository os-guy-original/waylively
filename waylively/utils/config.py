import os
import json
import shutil

HOME_DIR = os.path.expanduser("~")
CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", os.path.join(HOME_DIR, ".config"))
DATA_HOME = os.environ.get("XDG_DATA_HOME", os.path.join(HOME_DIR, ".local", "share"))
APPIMAGE_ENV_VARS = ("WAYLIVELY_APPIMAGE", "APPIMAGE")

CONFIG_DIR = os.path.join(CONFIG_HOME, "waylively")
DATA_DIR = os.path.join(DATA_HOME, "waylively")
WALLPAPERS_DIR = os.path.join(DATA_DIR, "wallpapers")
ACTIVE_CONF = os.path.join(CONFIG_DIR, "active.json")
DEFAULT_WALLPAPER_NAME = "waylively-default"
LANTERN_WALLPAPER_NAME = "waylively-lantern"
ORBITS_WALLPAPER_NAME = "waylively-orbits"
STARFIELD_WALLPAPER_NAME = "waylively-starfield"

# Shared format constants
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mkv', '.avi', '.mov'}
GIF_EXTENSION = '.gif'
ALL_MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | {GIF_EXTENSION}
DEFAULT_WALLPAPER_PROPERTIES = {
    "glowIntensity": {
        "type": "slider",
        "value": 0.15,
        "min": 0.0,
        "max": 0.5,
        "step": 0.01,
        "text": "Mouse Glow Intensity",
    },
    "glowRadius": {
        "type": "slider",
        "value": 200,
        "min": 50,
        "max": 500,
        "step": 10,
        "text": "Glow Radius",
    },
    "particleCount": {
        "type": "slider",
        "value": 120,
        "min": 20,
        "max": 300,
        "step": 10,
        "text": "Max Particles",
    },
    "showLogo": {
        "type": "checkbox",
        "value": True,
        "text": "Show Logo",
    },
    "showName": {
        "type": "checkbox",
        "value": True,
        "text": "Show Name",
    },
    "showSlogan": {
        "type": "checkbox",
        "value": True,
        "text": "Show Slogan",
    },
}

LANTERN_WALLPAPER_PROPERTIES = {
    "displayText": {
        "type": "text",
        "value": "LIVELY",
        "text": "Displayed Text",
    },
    "fontSpec": {
        "type": "font",
        "value": "Inter Bold 28",
        "text": "Font",
    },
    "textColor": {
        "type": "color",
        "value": "#a8b6dc",
        "text": "Text Color",
    },
    "backgroundColor": {
        "type": "color",
        "value": "#07090f",
        "text": "Background Color",
    },
    "wordSpacing": {
        "type": "slider",
        "value": 56,
        "min": 12,
        "max": 220,
        "step": 2,
        "text": "Word Spacing",
    },
    "rowShift": {
        "type": "slider",
        "value": 54,
        "min": -320,
        "max": 320,
        "step": 2,
        "text": "Row Shift",
    },
    "rowGap": {
        "type": "slider",
        "value": 28,
        "min": 4,
        "max": 140,
        "step": 2,
        "text": "Row Gap",
    },
    "glowRadius": {
        "type": "slider",
        "value": 240,
        "min": 80,
        "max": 480,
        "step": 4,
        "text": "Glow Radius",
    },
    "glowStrength": {
        "type": "slider",
        "value": 1,
        "min": 0,
        "max": 2,
        "step": 0.05,
        "text": "Glow Strength",
    },
    "patternMode": {
        "type": "dropdown",
        "value": 1,
        "items": ["Uniform", "Alternating", "Wave"],
        "text": "Row Pattern",
    },
    "alternateRowOpacity": {
        "type": "slider",
        "value": 0.22,
        "min": 0,
        "max": 0.85,
        "step": 0.05,
        "text": "Alternate Row Dimness",
    },
}

BUNDLED_WALLPAPERS = (
    {
        "id": DEFAULT_WALLPAPER_NAME,
        "source": "default_wallpaper",
        "properties": DEFAULT_WALLPAPER_PROPERTIES,
    },
    {
        "id": LANTERN_WALLPAPER_NAME,
        "source": "lantern_wallpaper",
        "properties": LANTERN_WALLPAPER_PROPERTIES,
    },
    {
        "id": ORBITS_WALLPAPER_NAME,
        "source": "orbits_wallpaper",
        "properties": None,
    },
    {
        "id": STARFIELD_WALLPAPER_NAME,
        "source": "starfield_wallpaper",
        "properties": None,
    },
)


def _get_bundled_wallpaper_spec(wallpaper_id):
    for spec in BUNDLED_WALLPAPERS:
        if spec["id"] == wallpaper_id:
            return spec
    return None


def get_bundled_wallpaper_dir(wallpaper_id):
    spec = _get_bundled_wallpaper_spec(wallpaper_id)
    if not spec:
        return None
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "ui", "assets", spec["source"])
    )


def get_bundled_default_wallpaper_dir():
    return get_bundled_wallpaper_dir(DEFAULT_WALLPAPER_NAME)


def get_default_wallpaper_dir(wallpaper_id=DEFAULT_WALLPAPER_NAME):
    return os.path.join(WALLPAPERS_DIR, wallpaper_id)


def _write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def _read_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def resolve_appimage_path() -> str | None:
    for env_name in APPIMAGE_ENV_VARS:
        value = os.environ.get(env_name)
        if value and os.path.exists(value):
            return os.path.abspath(value)
    return None


def ensure_bundled_wallpaper(wallpaper_id=DEFAULT_WALLPAPER_NAME):
    ensure_dirs()
    spec = _get_bundled_wallpaper_spec(wallpaper_id)
    if not spec:
        return None

    source_dir = get_bundled_wallpaper_dir(wallpaper_id)
    target_dir = get_default_wallpaper_dir(wallpaper_id)
    default_properties = spec.get("properties")

    if not os.path.isdir(source_dir):
        return None

    if not os.path.exists(target_dir):
        shutil.copytree(source_dir, target_dir)
    else:
        for root, _, files in os.walk(source_dir):
            rel_root = os.path.relpath(root, source_dir)
            target_root = target_dir if rel_root == "." else os.path.join(target_dir, rel_root)
            os.makedirs(target_root, exist_ok=True)
            for filename in files:
                src_path = os.path.join(root, filename)
                dst_path = os.path.join(target_root, filename)
                rel_path = filename if rel_root == "." else os.path.join(rel_root, filename)
                if rel_path == "LivelyProperties.json":
                    continue
                shutil.copy2(src_path, dst_path)

    if default_properties:
        props_path = os.path.join(target_dir, "LivelyProperties.json")
        backup_path = os.path.join(target_dir, "LivelyProperties.bak.json")

        if not os.path.exists(props_path):
            _write_json(props_path, default_properties)
        else:
            try:
                current_props = _read_json(props_path)
                merged_props = dict(default_properties)
                for key, default_prop in default_properties.items():
                    if key in current_props and isinstance(current_props[key], dict):
                        merged_props[key] = {**default_prop, **current_props[key]}
                for key, value in current_props.items():
                    if key not in merged_props:
                        merged_props[key] = value
                _write_json(props_path, merged_props)
            except Exception:
                _write_json(props_path, default_properties)
        _write_json(backup_path, default_properties)

    return target_dir


def ensure_default_wallpaper():
    return ensure_bundled_wallpaper(DEFAULT_WALLPAPER_NAME)


def ensure_bundled_wallpapers():
    ensured = []
    for spec in BUNDLED_WALLPAPERS:
        path = ensure_bundled_wallpaper(spec["id"])
        if path:
            ensured.append(path)
    return ensured


def resolve_writable_wallpaper_path(path):
    if not path:
        return path

    abs_path = os.path.abspath(path)
    for spec in BUNDLED_WALLPAPERS:
        bundled_dir = get_bundled_wallpaper_dir(spec["id"])
        if bundled_dir and abs_path == bundled_dir:
            return ensure_bundled_wallpaper(spec["id"])
    return abs_path


def get_wallpaper_entry_file(wallpaper_dir):
    if not os.path.isdir(wallpaper_dir):
        return None

    info_path = os.path.join(wallpaper_dir, "LivelyInfo.json")

    if os.path.exists(info_path):
        try:
            with open(info_path, 'r') as f:
                info = json.load(f)
            file_name = info.get("FileName")
            if file_name:
                return file_name
        except Exception:
            pass

    for filename in sorted(os.listdir(wallpaper_dir)):
        if os.path.splitext(filename)[1].lower() in ALL_MEDIA_EXTENSIONS | {'.html', '.htm'}:
            return filename

    return None


def is_video_wallpaper(wallpaper_dir):
    entry_file = get_wallpaper_entry_file(wallpaper_dir)
    if not entry_file:
        return False
    return os.path.splitext(entry_file)[1].lower() in VIDEO_EXTENSIONS


def ensure_video_properties(wallpaper_dir):
    if not is_video_wallpaper(wallpaper_dir):
        return False

    props_path = os.path.join(wallpaper_dir, "LivelyProperties.json")
    backup_path = os.path.join(wallpaper_dir, "LivelyProperties.bak.json")
    default_props = {
        "volume": {
            "type": "slider",
            "value": 0,
            "min": 0,
            "max": 100,
            "step": 1,
            "text": "Volume",
        }
    }

    if not os.path.exists(props_path):
        with open(props_path, 'w') as f:
            json.dump(default_props, f, indent=2)

    if not os.path.exists(backup_path):
        with open(backup_path, 'w') as f:
            json.dump(default_props, f, indent=2)

    return True

def ensure_dirs():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(WALLPAPERS_DIR, exist_ok=True)

def get_active_wallpaper():
    if not os.path.exists(ACTIVE_CONF):
        return None
    try:
        with open(ACTIVE_CONF, 'r') as f:
            data = json.load(f)
            return resolve_writable_wallpaper_path(data.get("path"))
    except Exception:
        return None

def set_active_wallpaper(path):
    ensure_dirs()
    resolved_path = resolve_writable_wallpaper_path(path)
    with open(ACTIVE_CONF, 'w') as f:
        json.dump({"path": resolved_path}, f)
