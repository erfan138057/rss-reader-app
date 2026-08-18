#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-$(git -C "$ROOT" describe --tags --always)}"
ARCH="$(uname -m)"
BINARY_NAME="RSS-Reader-Pro"
PACKAGE_NAME="RSS-Reader-Pro-${VERSION}-linux-${ARCH}"
DIST_DIR="$ROOT/dist"
STAGE_DIR="$DIST_DIR/$PACKAGE_NAME"
ARCHIVE="$DIST_DIR/$PACKAGE_NAME.tar.gz"

rm -rf "$STAGE_DIR" "$ARCHIVE"
mkdir -p "$STAGE_DIR"

install -m 0755 "$DIST_DIR/$BINARY_NAME" "$STAGE_DIR/$BINARY_NAME"
install -m 0644 "$ROOT/assets/rss-reader-pro.png" "$STAGE_DIR/rss-reader-pro.png"
install -m 0644 "$ROOT/LICENSE" "$STAGE_DIR/LICENSE"

cat > "$STAGE_DIR/README-LINUX.txt" <<'EOF'
RSS Reader Pro for Linux
========================

This is a portable x86_64 build. Extract the archive, open a terminal in this
directory, and run:

    ./RSS-Reader-Pro

The application stores its database and settings in your user application-data
directory, not beside this executable. Video links use your system's default
media handler. No VLC installation is required.

For best compatibility, use a current 64-bit Linux desktop with an X11 or
Wayland session. If your distribution is older than Ubuntu 22.04 or equivalent,
run the application from source with Python and the project requirements.
EOF

(
  cd "$DIST_DIR"
  tar --owner=0 --group=0 --numeric-owner -czf "$ARCHIVE" "$PACKAGE_NAME"
)

echo "$ARCHIVE"
