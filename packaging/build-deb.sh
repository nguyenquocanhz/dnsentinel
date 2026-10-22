#!/usr/bin/env bash
# Build .deb KHONG can debhelper (dung dpkg-deb). Chay duoc tren box toi gian.
# (Neu co debhelper: 'dpkg-buildpackage -us -uc -b' cung chay nho debian/.)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -m1 '^version' "$ROOT/pyproject.toml" | sed -E 's/.*"(.*)".*/\1/')"
STAGE="$ROOT/packaging/stage"
OUT="${1:-$(cd "$ROOT/.." && pwd)}"

echo ">> Build dnsentinel $VERSION"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/lib/dnsentinel/build" "$STAGE/lib/systemd/system"

cp -r "$ROOT/src" "$ROOT/pyproject.toml" "$ROOT/requirements.txt" \
      "$ROOT/README.md" "$ROOT/LICENSE" "$STAGE/usr/lib/dnsentinel/build/"
cp "$ROOT/systemd/dnsentinel.service" "$STAGE/lib/systemd/system/"
find "$STAGE/usr/lib/dnsentinel/build" -name '__pycache__' -type d -prune \
     -exec rm -rf {} + 2>/dev/null || true

cat > "$STAGE/DEBIAN/control" <<EOF
Package: dnsentinel
Version: $VERSION
Section: admin
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-venv
Maintainer: DNSentinel contributors <noreply@example.com>
Description: Giam sat uptime phan giai DNS ten mien .vn qua cum VNNIC
 Truy van NS/SOA/A/AAAA toi a..h.dns-servers.vn, tong hop up/degraded/down,
 tinh uptime %. Python thuan, nhe, mot SQLite. CLI quan ly ten mien.
EOF

for s in postinst prerm postrm; do
  sed '/#DEBHELPER#/d' "$ROOT/debian/$s" > "$STAGE/DEBIAN/$s"
  chmod 0755 "$STAGE/DEBIAN/$s"
done

DEB="$OUT/dnsentinel_${VERSION}_all.deb"
dpkg-deb --root-owner-group --build "$STAGE" "$DEB"
echo ">> Built: $DEB"
