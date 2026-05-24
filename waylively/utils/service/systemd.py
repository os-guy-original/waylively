import os
import shlex
import shutil
import subprocess

from waylively.utils.service.base import BaseServiceManager
from waylively.utils import config


class SystemdManager(BaseServiceManager):
    """Systemd service manager implementation."""

    SERVICE_NAME = "waylively.service"
    SERVICE_PATH = os.path.expanduser(f"~/.config/systemd/user/{SERVICE_NAME}")
    BIN_NAME = "waylively-daemon"
    APPIMAGE_ENV_VAR = "WAYLIVELY_APPIMAGE"

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("systemctl") is not None

    def _run(self, *args, **kwargs):
        try:
            return subprocess.run(
                ["systemctl", "--user", *args], check=False, text=True, **kwargs
            )
        except (FileNotFoundError, OSError):
            return None

    def _escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _service_exists(self) -> bool:
        return os.path.exists(self.SERVICE_PATH)

    def _ensure_dir(self) -> bool:
        os.makedirs(os.path.dirname(self.SERVICE_PATH), exist_ok=True)
        return True

    def _resolve_exec(self) -> str:
        appimage_path = config.resolve_appimage_path()
        if appimage_path:
            return shlex.join([appimage_path, "--daemon"])

        local_bin = os.path.expanduser(f"~/.local/bin/{self.BIN_NAME}")
        if os.path.exists(local_bin):
            return shlex.join([local_bin])

        installed = shutil.which(self.BIN_NAME)
        if installed:
            return shlex.join([installed])

        dev_bin = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "bin", self.BIN_NAME)
        )
        return shlex.join([dev_bin])

    def generate_service_file(self) -> bool:
        if not self._ensure_dir():
            return False

        appimage_path = config.resolve_appimage_path()
        lines = [
            "[Unit]",
            "Description=Waylively Live Wallpaper Daemon",
            "PartOf=graphical-session.target",
            "After=graphical-session.target",
            "",
            "[Service]",
        ]

        if appimage_path:
            lines.append(f'Environment="{self.APPIMAGE_ENV_VAR}={self._escape(appimage_path)}"')

        lines.extend([
            f"ExecStart={self._resolve_exec()}",
            "Restart=on-failure",
            "RestartSec=2",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ])

        with open(self.SERVICE_PATH, "w") as f:
            f.write("\n".join(lines))

        res = self._run("daemon-reload")
        return bool(res and res.returncode == 0)

    def is_enabled(self) -> bool:
        res = self._run("is-enabled", self.SERVICE_NAME)
        return bool(res and res.returncode == 0 and res.stdout.strip() == "enabled")

    def is_active(self) -> bool:
        res = self._run("is-active", self.SERVICE_NAME)
        return bool(res and res.returncode == 0 and res.stdout.strip() == "active")

    def start(self) -> bool:
        if not self.generate_service_file():
            return False
        res = self._run("start", self.SERVICE_NAME)
        return bool(res and res.returncode == 0)

    def stop(self) -> bool:
        if not self._service_exists():
            return True
        res = self._run("stop", self.SERVICE_NAME)
        return bool(res and res.returncode == 0)

    def enable(self) -> bool:
        if not self.generate_service_file():
            return False
        res = self._run("enable", "--now", self.SERVICE_NAME)
        return bool(res and res.returncode == 0)

    def disable(self) -> bool:
        if not self._service_exists():
            return True
        res = self._run("disable", "--now", self.SERVICE_NAME)
        return bool(res and res.returncode == 0)

    def restart(self) -> bool:
        if not self._service_exists():
            return self.start()
        res = self._run("restart", self.SERVICE_NAME)
        return bool(res and res.returncode == 0)
