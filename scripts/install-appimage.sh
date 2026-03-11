#!/usr/bin/env bash
set -euo pipefail

REPO="${WAYLIVELY_REPO:-os-guy-original/waylively}"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"
ICON_URL="https://raw.githubusercontent.com/${REPO}/main/waylively/ui/assets/icon.png"

APP_DIR="${HOME}/.local/opt/waylively"
BIN_DIR="${HOME}/.local/bin"
DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
APPIMAGE_PATH="${APP_DIR}/Waylively.AppImage"
DESKTOP_PATH="${DATA_HOME}/applications/io.github.os_guy_original.Waylively.desktop"
ICON_PATH="${DATA_HOME}/icons/hicolor/128x128/apps/io.github.os_guy_original.Waylively.png"
SERVICE_PATH="${CONFIG_HOME}/systemd/user/waylively.service"

release_json="$(curl -fsSL "$API_URL")"
appimage_url="$(printf '%s\n' "$release_json" | grep -o 'https://[^\"]*\.AppImage' | grep -E '(x86_64|amd64)' | head -n1 || true)"
if [[ -z "$appimage_url" ]]; then
  appimage_url="$(printf '%s\n' "$release_json" | grep -o 'https://[^\"]*\.AppImage' | head -n1 || true)"
fi

if [[ -z "$appimage_url" ]]; then
  echo "No AppImage asset found in the latest GitHub release for ${REPO}." >&2
  exit 1
fi

mkdir -p "$APP_DIR" "$BIN_DIR" \
  "$(dirname "$DESKTOP_PATH")" \
  "$(dirname "$ICON_PATH")" \
  "$(dirname "$SERVICE_PATH")"

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT
curl -fL "$appimage_url" -o "$tmp_file"
install -m 0755 "$tmp_file" "$APPIMAGE_PATH"

cat >"${BIN_DIR}/waylively" <<EOF
#!/bin/sh
exec "$APPIMAGE_PATH" --manager "\$@"
EOF

cat >"${BIN_DIR}/waylively-manager" <<EOF
#!/bin/sh
exec "$APPIMAGE_PATH" --manager "\$@"
EOF

cat >"${BIN_DIR}/waylively-daemon" <<EOF
#!/bin/sh
export WAYLIVELY_APPIMAGE="$APPIMAGE_PATH"
exec "$APPIMAGE_PATH" --daemon "\$@"
EOF

cat >"${BIN_DIR}/waylively-engine" <<EOF
#!/bin/sh
export WAYLIVELY_APPIMAGE="$APPIMAGE_PATH"
exec "$APPIMAGE_PATH" --engine "\$@"
EOF

cat >"${BIN_DIR}/waylively-screenshot" <<EOF
#!/bin/sh
export WAYLIVELY_APPIMAGE="$APPIMAGE_PATH"
exec "$APPIMAGE_PATH" --screenshot "\$@"
EOF

chmod 0755 \
  "${BIN_DIR}/waylively" \
  "${BIN_DIR}/waylively-manager" \
  "${BIN_DIR}/waylively-daemon" \
  "${BIN_DIR}/waylively-engine" \
  "${BIN_DIR}/waylively-screenshot"

curl -fsSL "$ICON_URL" -o "$ICON_PATH"

cat >"$DESKTOP_PATH" <<EOF
[Desktop Entry]
Name=Waylively
Comment=Native Live Wallpapers for Wayland
Exec=${BIN_DIR}/waylively-manager
Icon=io.github.os_guy_original.Waylively
Terminal=false
Type=Application
Categories=Utility;GTK;
Keywords=wallpaper;live;wayland;lively;
StartupNotify=true
StartupWMClass=io.github.os_guy_original.Waylively
EOF

cat >"$SERVICE_PATH" <<EOF
[Unit]
Description=Waylively Live Wallpaper Daemon
PartOf=graphical-session.target
After=graphical-session.target

[Service]
Environment="WAYLIVELY_APPIMAGE=${APPIMAGE_PATH}"
ExecStart=${BIN_DIR}/waylively-daemon
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$(dirname "$DESKTOP_PATH")" >/dev/null 2>&1 || true
fi

echo "Waylively installed to ${APPIMAGE_PATH}"
echo "Launch it with: ${BIN_DIR}/waylively-manager"
echo "Enable the wallpaper daemon with: systemctl --user enable --now waylively.service"