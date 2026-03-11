import os
import shlex
import shutil
import subprocess

from waylively.utils import config

SERVICE_NAME = "waylively.service"
SERVICE_FILE_PATH = os.path.expanduser(f"~/.config/systemd/user/{SERVICE_NAME}")
BIN_NAME = "waylively-daemon"
APPIMAGE_ENV_VAR = "WAYLIVELY_APPIMAGE"


def _run_command(cmd, **kwargs):
    try:
        return subprocess.run(cmd, check=False, text=True, **kwargs)
    except (FileNotFoundError, OSError):
        return None


def _systemctl(*args):
    return _run_command(["systemctl", "--user", *args], capture_output=True)


def _systemd_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _service_file_exists() -> bool:
    return os.path.exists(SERVICE_FILE_PATH)


def ensure_systemd_dir() -> bool:
    os.makedirs(os.path.dirname(SERVICE_FILE_PATH), exist_ok=True)
    return True


def _resolve_daemon_exec() -> str:
    appimage_path = config.resolve_appimage_path()
    if appimage_path:
        return shlex.join([appimage_path, "--daemon"])

    local_bin = os.path.expanduser(f"~/.local/bin/{BIN_NAME}")
    if os.path.exists(local_bin):
        return shlex.join([local_bin])

    installed = shutil.which(BIN_NAME)
    if installed:
        return shlex.join([installed])

    dev_bin = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "bin", BIN_NAME)
    )
    return shlex.join([dev_bin])


def generate_service_file() -> bool:
    if not ensure_systemd_dir():
        return False

    appimage_path = config.resolve_appimage_path()
    service_lines = [
        "[Unit]",
        "Description=Waylively Live Wallpaper Daemon",
        "PartOf=graphical-session.target",
        "After=graphical-session.target",
        "",
        "[Service]",
    ]

    if appimage_path:
        service_lines.append(
            f'Environment="{APPIMAGE_ENV_VAR}={_systemd_escape(appimage_path)}"'
        )

    service_lines.extend(
        [
            f"ExecStart={_resolve_daemon_exec()}",
            "Restart=on-failure",
            "RestartSec=2",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )

    with open(SERVICE_FILE_PATH, "w") as f:
        f.write("\n".join(service_lines))

    reload_res = _systemctl("daemon-reload")
    return bool(reload_res and reload_res.returncode == 0)


def is_service_enabled() -> bool:
    res = _systemctl("is-enabled", SERVICE_NAME)
    return bool(res and res.returncode == 0 and res.stdout.strip() == "enabled")


def is_service_active() -> bool:
    res = _systemctl("is-active", SERVICE_NAME)
    return bool(res and res.returncode == 0 and res.stdout.strip() == "active")


def start_service() -> bool:
    if not generate_service_file():
        return False
    res = _systemctl("start", SERVICE_NAME)
    return bool(res and res.returncode == 0)


def stop_service() -> bool:
    if not _service_file_exists():
        return True
    res = _systemctl("stop", SERVICE_NAME)
    return bool(res and res.returncode == 0)


def enable_service() -> bool:
    if not generate_service_file():
        return False
    res = _systemctl("enable", "--now", SERVICE_NAME)
    return bool(res and res.returncode == 0)


def disable_service() -> bool:
    if not _service_file_exists():
        return True
    res = _systemctl("disable", "--now", SERVICE_NAME)
    return bool(res and res.returncode == 0)


def restart_service() -> bool:
    if not _service_file_exists():
        return start_service()
    res = _systemctl("restart", SERVICE_NAME)
    return bool(res and res.returncode == 0)
