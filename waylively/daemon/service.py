import os
import shutil
import subprocess
import sys
import time
from waylively.utils import config


def _resolve_engine_command(path):
    appimage_path = config.resolve_appimage_path()
    if appimage_path:
        return [appimage_path, "--engine", path]

    local_bin = os.path.expanduser("~/.local/bin/waylively-engine")
    if os.path.exists(local_bin):
        return [local_bin, path]

    dev_engine = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "bin",
        "waylively-engine",
    )
    if os.path.exists(dev_engine):
        return [dev_engine, path]

    installed = shutil.which("waylively-engine")
    if installed:
        return [installed, path]

    return [sys.executable, "-m", "waylively.engine.renderer", path]

class WaylivelyDaemon:
    def __init__(self):
        self.current_process = None
        self.current_wallpaper = None

    def start_engine(self, path):
        if self.current_process:
            self.stop_engine()
        print(f"Daemon: Starting engine for {path}")
        self.current_process = subprocess.Popen(_resolve_engine_command(path))
        self.current_wallpaper = path

    def stop_engine(self):
        if self.current_process:
            print("Daemon: Stopping current engine")
            self.current_process.terminate()
            self.current_process.wait(timeout=5)
            self.current_process = None
            self.current_wallpaper = None

    def run(self):
        print("Waylively Daemon Started. Watching for changes...")
        config.ensure_dirs()
        
        while True:
            active_wp = config.get_active_wallpaper()
            if active_wp and active_wp != self.current_wallpaper:
                self.start_engine(active_wp)
            elif not active_wp and self.current_process:
                self.stop_engine()
                
            time.sleep(2)

def main():
    daemon = WaylivelyDaemon()
    try:
        daemon.run()
    except KeyboardInterrupt:
        daemon.stop_engine()
        print("Daemon exiting.")

if __name__ == "__main__":
    main()
