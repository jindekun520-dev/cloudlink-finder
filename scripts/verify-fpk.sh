#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(awk -F '=' '$1 ~ /^[[:space:]]*version[[:space:]]*$/ {value=$2; gsub(/^[[:space:]]+|[[:space:]]+$/, "", value); print value; exit}' "$ROOT_DIR/fpk/manifest")"
FPK_FILE="${1:-$ROOT_DIR/release/cloudlink-finder-${VERSION}.fpk}"

if [[ ! -f "$FPK_FILE" ]]; then
  echo "FPK 文件不存在：$FPK_FILE" >&2
  exit 1
fi

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cloudlink-fpk-verify.XXXXXX")"
cleanup() {
  if [[ -d "$WORK_DIR" ]]; then
    rm -r "$WORK_DIR"
  fi
}
trap cleanup EXIT

tar -xzf "$FPK_FILE" -C "$WORK_DIR"

for path in manifest config/privilege config/resource cmd/main ICON.PNG ICON_256.PNG app.tgz; do
  if [[ ! -e "$WORK_DIR/$path" ]]; then
    echo "FPK 缺少必需内容：$path" >&2
    exit 1
  fi
done

python3 -m json.tool "$WORK_DIR/config/privilege" >/dev/null
python3 -m json.tool "$WORK_DIR/config/resource" >/dev/null
bash -n "$WORK_DIR/cmd/main"

python3 - "$WORK_DIR/ICON.PNG" 64 "$WORK_DIR/ICON_256.PNG" 256 <<'PY'
import struct
import sys

for index in range(1, len(sys.argv), 2):
    path = sys.argv[index]
    expected_size = int(sys.argv[index + 1])
    with open(path, "rb") as handle:
        data = handle.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} 不是 PNG"
    width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", data[16:29])
    assert (width, height) == (expected_size, expected_size), f"{path} 尺寸错误"
    assert bit_depth == 8, f"{path} 位深错误"
    assert color_type == 2, f"{path} 必须是无 Alpha 的 RGB PNG"
    assert b"sRGB" in data or b"iCCP" in data, f"{path} 缺少 sRGB 色彩信息"
PY

mkdir -p "$WORK_DIR/app"
tar -xzf "$WORK_DIR/app.tgz" -C "$WORK_DIR/app"

python3 - "$WORK_DIR/app/ui/config" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    config = json.load(handle)

entry = config[".url"]["third-pan-search.Application"]
assert entry["title"] == "网盘搜索神器"
assert entry["icon"] == "images/icon_{0}.png"
assert entry["type"] == "url"
assert entry["protocol"] == "http"
assert entry["port"] == "8899"
assert entry["url"] == "/"
PY

for path in docker/docker-compose.yaml docker/Dockerfile docker/backend/app/main.py docker/frontend/package.json docker/nginx/default.conf docker/supervisor/supervisord.conf ui/config ui/images/icon_64.png ui/images/icon_256.png; do
  if [[ ! -e "$WORK_DIR/app/$path" ]]; then
    echo "app.tgz 缺少必需内容：$path" >&2
    exit 1
  fi
done

python3 - "$WORK_DIR/app/ui/images/icon_64.png" 64 "$WORK_DIR/app/ui/images/icon_256.png" 256 <<'PY'
import struct
import sys

for index in range(1, len(sys.argv), 2):
    path = sys.argv[index]
    expected_size = int(sys.argv[index + 1])
    with open(path, "rb") as handle:
        data = handle.read()
    width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", data[16:29])
    assert (width, height) == (expected_size, expected_size), f"{path} 尺寸错误"
    assert bit_depth == 8 and color_type == 2, f"{path} 必须是无 Alpha 的 RGB PNG"
    assert b"sRGB" in data or b"iCCP" in data, f"{path} 缺少 sRGB 色彩信息"
PY

python3 -m json.tool "$WORK_DIR/app/ui/config" >/dev/null
docker compose -f "$WORK_DIR/app/docker/docker-compose.yaml" config --quiet

if find "$WORK_DIR/app" \( -name '.DS_Store' -o -name 'node_modules' -o -name '*.db' \) -print -quit | grep -q .; then
  echo "FPK 中包含不应打包的本地文件" >&2
  exit 1
fi

echo "FPK 结构与配置校验通过：$FPK_FILE"
echo "包大小：$(du -h "$FPK_FILE" | awk '{print $1}')"
echo "SHA-256：$(shasum -a 256 "$FPK_FILE" | awk '{print $1}')"
