import os
import shlex
import shutil
import subprocess
import warnings

from waylively.utils.service.base import BaseServiceManager
from waylively.utils import config


class OpenRCManager(BaseServiceManager):
    """OpenRC service manager using XDG autostart (user session)."""

    SERVICE_NAME = "waylively"
    AUTOSTART_PATH = os.path.expanduser("~/.config/autostart/waylively.desktop")
    BIN_NAME = "waylively-daemon"
    APPIMAGE_ENV_VAR = "WAYLIVELY_APPIMAGE"

    @classmethod
    def is_available(cls) -> bool:
        return os.path.exists("/sbin/openrc-run") or shutil.which("rc-service") is not None

    def _run(self, *args, **kwargs):
        try:
            return subprocess.run(list(args), check=False, text=True, **kwargs)
        except (FileNotFoundError, OSError):
            return None

    def _service_exists(self) -> bool:
        return os.path.exists(self.AUTOSTART_PATH)

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

    def _generate_desktop_content(self) -> str:
        """Generate XDG autostart desktop file."""
        exec_cmd = self._resolve_exec()
        appimage_path = config.resolve_appimage_path()

        env_prefix = ""
        if appimage_path:
            env_prefix = f"env {self.APPIMAGE_ENV_VAR}={shlex.quote(appimage_path)} "

        return f'''[Desktop Entry]
Type=Application
Name=Waylively Wallpaper Daemon
Comment=Live Wallpaper Daemon for Wayland
Exec={env_prefix}{exec_cmd}
Icon=waylively
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
'''

    def generate_service_file(self) -> bool:
        content = self._generate_desktop_content()
        os.makedirs(os.path.dirname(self.AUTOSTART_PATH), exist_ok=True)
        try:
            with open(self.AUTOSTART_PATH, "w") as f:
                f.write(content)
            return True
        except (PermissionError, OSError) as e:
            warnings.warn(f"Failed to write autostart file: {e}", RuntimeWarning)
            return False

    def is_enabled(self) -> bool:
        if not os.path.exists(self.AUTOSTART_PATH):
            return False
        try:
            with open(self.AUTOSTART_PATH) as f:
                return "X-GNOME-Autostart-enabled=true" in f.read()
        except OSError:
            return False

    def is_active(self) -> bool:
        res = self._run("pgrep", "-f", "Waylively.AppImage", capture_output=True)
        return bool(res and res.returncode == 0)

    def start(self) -> bool:
        if not self._service_exists():
            if not self.generate_service_file():
                return False
        exec_cmd = self._resolve_exec()
        appimage_path = config.resolve_appimage_path()

        env = os.environ.copy()
        if appimage_path:
            env[self.APPIMAGE_ENV_VAR] = appimage_path

        try:
            subprocess.Popen(
                shlex.split(exec_cmd),
                env=env,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except (FileNotFoundError, OSError) as e:
            warnings.warn(f"Failed to start daemon: {e}", RuntimeWarning)
            return False

    def stop(self) -> bool:
        # Kill both the AppImage and extracted waylively processes
        self._run("pkill", "-f", "Waylively.AppImage")
        self._run("pkill", "-f", "waylively.*--daemon")
        self._run("pkill", "-f", "waylively.*--engine")
        return True

    def enable(self) -> bool:
        if not self.generate_service_file():
            return False
        return self.start()

    def disable(self) -> bool:
        self.stop()
        if os.path.exists(self.AUTOSTART_PATH):
            try:
                os.unlink(self.AUTOSTART_PATH)
            except OSError:
                pass
        return True

    def restart(self) -> bool:
        self.stop()
        return self.start()
