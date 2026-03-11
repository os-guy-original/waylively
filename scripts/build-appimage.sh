#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DIST_DIR="${ROOT_DIR}/dist"
APPDIR="${DIST_DIR}/Waylively.AppDir"
TOOLS_DIR="${ROOT_DIR}/.cache/appimage"

ARCH_RAW="$(uname -m)"
case "$ARCH_RAW" in
  x86_64|amd64) ARCH="x86_64" ;;
  aarch64|arm64) ARCH="aarch64" ;;
  *) echo "Unsupported architecture: $ARCH_RAW" >&2; exit 1 ;;
esac

VERSION="$(python3 - <<'PY'
import pathlib, tomllib
data = tomllib.loads(pathlib.Path('pyproject.toml').read_text())
print(data['project']['version'])
PY
)"
OUTPUT_APPIMAGE="${DIST_DIR}/Waylively-${VERSION}-${ARCH}.AppImage"
APPIMAGETOOL="${TOOLS_DIR}/appimagetool-${ARCH}.AppImage"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"

mkdir -p "$DIST_DIR" "$TOOLS_DIR"
rm -rf "$APPDIR" "$OUTPUT_APPIMAGE"
mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" \
  "$APPDIR/usr/share/icons/hicolor/128x128/apps" \
  "$APPDIR/usr/share/icons/hicolor/scalable/apps" \
  "$APPDIR/usr/share/metainfo"
mkdir -p "$APPDIR/usr/lib/waylively-src"

if [[ ! -x "$APPIMAGETOOL" ]]; then
  curl -fL "$APPIMAGETOOL_URL" -o "$APPIMAGETOOL"
  chmod +x "$APPIMAGETOOL"
fi

cp -a "$ROOT_DIR/bin" "$ROOT_DIR/waylively" "$ROOT_DIR/data" "$ROOT_DIR/LICENSE" "$APPDIR/usr/lib/waylively-src/"

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
APPDIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
SRC_DIR="$APPDIR/usr/lib/waylively-src"
export PYTHONPATH="$SRC_DIR${PYTHONPATH:+:$PYTHONPATH}"
export WAYLIVELY_APPIMAGE="${APPIMAGE:-}"
exec /usr/bin/python3 "$SRC_DIR/bin/waylively" "$@"
EOF
chmod +x "$APPDIR/AppRun"

python3 - <<'PY'
from pathlib import Path
desktop = Path('data/io.github.os_guy_original.Waylively.desktop').read_text()
desktop = desktop.replace('Exec=waylively-manager', 'Exec=waylively')
Path('dist/Waylively.AppDir/io.github.os_guy_original.Waylively.desktop').write_text(desktop)
Path('dist/Waylively.AppDir/usr/share/applications/io.github.os_guy_original.Waylively.desktop').write_text(desktop)
PY

install -Dm644 "$ROOT_DIR/waylively/ui/assets/icon.png" "$APPDIR/io.github.os_guy_original.Waylively.png"
install -Dm644 "$ROOT_DIR/waylively/ui/assets/icon.png" "$APPDIR/usr/share/icons/hicolor/128x128/apps/io.github.os_guy_original.Waylively.png"
install -Dm644 "$ROOT_DIR/waylively/ui/assets/icon.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/io.github.os_guy_original.Waylively.svg"
install -Dm644 "$ROOT_DIR/data/io.github.os_guy_original.Waylively.metainfo.xml" "$APPDIR/usr/share/metainfo/io.github.os_guy_original.Waylively.metainfo.xml"
install -Dm644 "$ROOT_DIR/data/io.github.os_guy_original.Waylively.metainfo.xml" "$APPDIR/usr/share/metainfo/io.github.os_guy_original.Waylively.appdata.xml"

ARCH="$ARCH" VERSION="$VERSION" "$APPIMAGETOOL" --appimage-extract-and-run "$APPDIR" "$OUTPUT_APPIMAGE"

echo "Built $OUTPUT_APPIMAGE"