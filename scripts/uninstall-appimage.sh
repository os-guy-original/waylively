#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${HOME}/.local/opt/waylively"
BIN_DIR="${HOME}/.local/bin"
DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
APPIMAGE_PATH="${APP_DIR}/Waylively.AppImage"
DESKTOP_PATH="${DATA_HOME}/applications/io.github.os_guy_original.Waylively.desktop"
ICON_PATH="${DATA_HOME}/icons/hicolor/128x128/apps/io.github.os_guy_original.Waylively.png"
SERVICE_PATH="${CONFIG_HOME}/systemd/user/waylively.service"
WRAPPERS=(
  "${BIN_DIR}/waylively"
  "${BIN_DIR}/waylively-manager"
  "${BIN_DIR}/waylively-daemon"
  "${BIN_DIR}/waylively-engine"
  "${BIN_DIR}/waylively-screenshot"
)
PURGE_DATA=0

for arg in "$@"; do
  case "$arg" in
    --purge-data)
      PURGE_DATA=1
      ;;
    -h|--help)
      echo "Usage: $0 [--purge-data]"
      echo "  --purge-data  Also remove ~/.config/waylively and ~/.local/share/waylively"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user disable --now waylively.service >/dev/null 2>&1 || true
fi

rm -f "$APPIMAGE_PATH" "$DESKTOP_PATH" "$ICON_PATH" "$SERVICE_PATH"
for path in "${WRAPPERS[@]}"; do
  rm -f "$path"
done

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload >/dev/null 2>&1 || true
fi

if command -v update-desktop-database >/dev/null 2>&1 && [ -d "$(dirname "$DESKTOP_PATH")" ]; then
  update-desktop-database "$(dirname "$DESKTOP_PATH")" >/dev/null 2>&1 || true
fi

rmdir "$APP_DIR" 2>/dev/null || true
rmdir "$BIN_DIR" 2>/dev/null || true
rmdir "$(dirname "$ICON_PATH")" 2>/dev/null || true
rmdir "$(dirname "$(dirname "$ICON_PATH")")" 2>/dev/null || true
rmdir "$(dirname "$DESKTOP_PATH")" 2>/dev/null || true
rmdir "$(dirname "$SERVICE_PATH")" 2>/dev/null || true
rmdir "$(dirname "$(dirname "$SERVICE_PATH")")" 2>/dev/null || true

if [ "$PURGE_DATA" -eq 1 ]; then
  rm -rf "${CONFIG_HOME}/waylively" "${DATA_HOME}/waylively"
fi

echo "Waylively AppImage uninstall complete."
if [ "$PURGE_DATA" -eq 1 ]; then
  echo "Removed app files and user data."
else
  echo "Removed app files. User data was kept."
  echo "Re-run with --purge-data to also remove ~/.config/waylively and ~/.local/share/waylively."
fi