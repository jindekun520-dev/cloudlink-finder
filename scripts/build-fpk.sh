#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FNPACK_VERSION="1.2.3"
APP_NAME="cloudlink-finder"
PACKAGE_NAME="cloudlink-finder"

manifest_value() {
  awk -F '=' -v key="$1" '
    $1 ~ "^[[:space:]]*" key "[[:space:]]*$" {
      value = $2
      sub(/^[[:space:]]+/, "", value)
      sub(/[[:space:]]+$/, "", value)
      print value
      exit
    }
  ' "$ROOT_DIR/fpk/manifest"
}

resolve_fnpack() {
  if [[ -n "${FNPACK_BIN:-}" ]]; then
    printf '%s\n' "$FNPACK_BIN"
    return
  fi

  if command -v fnpack >/dev/null 2>&1; then
    command -v fnpack
    return
  fi

  local os arch platform cache_dir binary url expected_sha actual_sha
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"

  case "$os" in
    darwin|linux) ;;
    *) echo "不支持的系统：$os" >&2; exit 1 ;;
  esac

  case "$arch" in
    arm64|aarch64) arch="arm64" ;;
    x86_64|amd64) arch="amd64" ;;
    *) echo "不支持的 CPU 架构：$arch" >&2; exit 1 ;;
  esac

  platform="${os}-${arch}"
  cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/cloudlink-finder"
  binary="$cache_dir/fnpack-${FNPACK_VERSION}-${platform}"
  url="https://static2.fnnas.com/fnpack/fnpack-${FNPACK_VERSION}-${platform}"
  mkdir -p "$cache_dir"

  if [[ ! -x "$binary" ]]; then
    echo "下载飞牛官方 fnpack ${FNPACK_VERSION} (${platform})..." >&2
    curl --fail --location --silent --show-error "$url" --output "$binary"
    chmod 0755 "$binary"
  fi

  # 官方静态地址的 macOS ARM64 1.2.3 二进制校验值，防止缓存文件损坏。
  if [[ "$platform" == "darwin-arm64" ]]; then
    expected_sha="d40cb00896cb2a5d211357d255750ed0cbe7f2d141df671c2b717afb4e74bf77"
    actual_sha="$(shasum -a 256 "$binary" | awk '{print $1}')"
    if [[ "$actual_sha" != "$expected_sha" ]]; then
      echo "fnpack SHA-256 校验失败" >&2
      exit 1
    fi
  fi

  printf '%s\n' "$binary"
}

VERSION="$(manifest_value version)"
if [[ -z "$VERSION" ]]; then
  echo "无法从 fpk/manifest 读取版本号" >&2
  exit 1
fi

FNPACK="$(resolve_fnpack)"
BUILD_ROOT="$ROOT_DIR/build/fpk"
RELEASE_DIR="$ROOT_DIR/release"
mkdir -p "$BUILD_ROOT" "$RELEASE_DIR"

STAGING_DIR="$(mktemp -d "$BUILD_ROOT/${APP_NAME}.XXXXXX")"
PACK_DIR="$(mktemp -d "$BUILD_ROOT/output.XXXXXX")"

# 前端必须在打包机上预构建：Dockerfile 已移除 Node 构建阶段，
# NAS 端不会再执行 npm install，dist 缺失会直接导致镜像构建失败。
if ! command -v npm >/dev/null 2>&1; then
  echo "未检测到 npm，无法预构建前端产物" >&2
  exit 1
fi

echo "正在本地预构建前端产物..."
(cd "$ROOT_DIR/frontend" && npm ci --no-audit && npm run build)

if [[ ! -f "$ROOT_DIR/frontend/dist/index.html" ]]; then
  echo "前端预构建失败：缺少 frontend/dist/index.html" >&2
  exit 1
fi

cleanup() {
  if [[ -d "$STAGING_DIR" ]]; then
    rm -r "$STAGING_DIR"
  fi
  if [[ -d "$PACK_DIR" ]]; then
    rm -r "$PACK_DIR"
  fi
}
trap cleanup EXIT

rsync -a --exclude '.DS_Store' "$ROOT_DIR/fpk/" "$STAGING_DIR/"
cp "$ROOT_DIR/ICON.PNG" "$STAGING_DIR/ICON.PNG"
cp "$ROOT_DIR/ICON_256.PNG" "$STAGING_DIR/ICON_256.PNG"
cp "$ROOT_DIR/ICON.PNG" "$STAGING_DIR/app/ui/images/cloudlink_finder_v108_64.png"
cp "$ROOT_DIR/ICON_256.PNG" "$STAGING_DIR/app/ui/images/cloudlink_finder_v108_256.png"
cp "$ROOT_DIR/docker/Dockerfile" "$STAGING_DIR/app/docker/Dockerfile"

rsync -a \
  --exclude '.DS_Store' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'data/*.db' \
  --exclude 'data/*.sqlite*' \
  --exclude 'tests' \
  "$ROOT_DIR/backend/" "$STAGING_DIR/app/docker/backend/"

# 镜像构建只需要 dist，源码与依赖清单仅保留 package.json 便于溯源。
# 为了与 Dockerfile 的 COPY dist/ 保持一致，直接把产物放到 docker/dist 下。
rsync -a --exclude '.DS_Store' "$ROOT_DIR/frontend/dist/" "$STAGING_DIR/app/docker/dist/"
cp "$ROOT_DIR/frontend/package.json" "$STAGING_DIR/app/docker/package.json"

rsync -a "$ROOT_DIR/nginx/" "$STAGING_DIR/app/docker/nginx/"
rsync -a "$ROOT_DIR/supervisor/" "$STAGING_DIR/app/docker/supervisor/"
chmod 0755 "$STAGING_DIR/cmd/"*

echo "使用 $FNPACK 构建 FPK..."
(
  cd "$PACK_DIR"
  "$FNPACK" build --directory "$STAGING_DIR"
)

BUILT_FPK="$PACK_DIR/${APP_NAME}.fpk"
if [[ ! -f "$BUILT_FPK" ]]; then
  echo "fnpack 未生成预期文件：$BUILT_FPK" >&2
  exit 1
fi

FINAL_FPK="$RELEASE_DIR/${PACKAGE_NAME}-${VERSION}.fpk"
install -m 0644 "$BUILT_FPK" "$FINAL_FPK"

echo "FPK 构建完成：$FINAL_FPK"
shasum -a 256 "$FINAL_FPK"
