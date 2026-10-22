#!/usr/bin/env bash
# Tao APT repo tinh (flat) tu cac file .deb da build, de tu host (vd sau Nginx).
#   ./make-apt-repo.sh /duong/dan/output [thu-muc-chua-deb]
# Ket qua: <output>/ (Packages, Packages.gz, Release). Tro Nginx vao thu muc nay.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/packaging/apt-repo}"
DEB_DIR="${2:-$(cd "$ROOT/.." && pwd)}"

command -v dpkg-scanpackages >/dev/null 2>&1 || {
  echo "Can goi 'dpkg-dev': sudo apt install dpkg-dev"; exit 1; }

mkdir -p "$OUT"
cp "$DEB_DIR"/dnsentinel_*_all.deb "$OUT"/ 2>/dev/null || {
  echo "Khong tim thay dnsentinel_*_all.deb trong $DEB_DIR"; exit 1; }

cd "$OUT"
dpkg-scanpackages --multiversion . > Packages
gzip -9kf Packages
cat > Release <<EOF
Origin: DNSentinel
Label: DNSentinel
Suite: stable
Codename: stable
Architectures: all
Components: main
Description: APT repo tu host cho DNSentinel
Date: $(date -Ru)
EOF

echo ">> APT repo san sang tai: $OUT"
echo ">> Client cai bang:"
echo "   echo 'deb [trusted=yes] http://<host>/dnsentinel ./' | sudo tee /etc/apt/sources.list.d/dnsentinel.list"
echo "   sudo apt update && sudo apt install dnsentinel"
