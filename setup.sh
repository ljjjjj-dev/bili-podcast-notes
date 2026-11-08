#!/bin/bash
# 一次性安装所有工具到 tools/：独立版 Python、yt-dlp、语音转文字程序、ffmpeg、Whisper 模型。
# 只支持 Apple 芯片（M 系列）的 Mac。大约需要下载 1.5 GB（Python 和程序）+ 1.5 GB（模型）。
#
# 用法: ./setup.sh            安装全部
#       ./setup.sh --no-model 先不下载语音模型（只用 B站字幕时不需要；以后需要再运行一次 ./setup.sh）
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"
TOOLS="${TOOLS_DIR:-$ROOT/tools}"

PY_RELEASE="20261026"
PY_FILE="cpython-3.13.18+${PY_RELEASE}-aarch64-apple-darwin-install_only.tar.gz"
PY_URL_BASE="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_RELEASE}"
MODEL="mlx-community/whisper-large-v3-turbo"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
  echo "这套工具只支持 Apple 芯片（M 系列）的 Mac：语音转写用的是 Apple 的 MLX 框架。"; exit 1
fi

mkdir -p "$TOOLS/bin" "$TOOLS/models"

# 1. 独立版 Python
if [ ! -x "$TOOLS/python/bin/python3" ]; then
  say "1/4 下载独立版 Python 3.13（约 25 MB）"
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  curl -fSL --progress-bar -o "$TMP/$PY_FILE" "$PY_URL_BASE/${PY_FILE//+/%2B}"
  curl -fsSL -o "$TMP/SHA256SUMS" "$PY_URL_BASE/SHA256SUMS"
  EXPECTED="$(grep " $PY_FILE\$" "$TMP/SHA256SUMS" | awk '{print $1}')"
  ACTUAL="$(shasum -a 256 "$TMP/$PY_FILE" | awk '{print $1}')"
  if [ -z "$EXPECTED" ] || [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "校验失败：下载的文件和官方发布的不一致，已停止安装。"; exit 1
  fi
  echo "校验通过（SHA256 $ACTUAL）"
  mkdir -p "$TOOLS/python"
  tar xzf "$TMP/$PY_FILE" -C "$TOOLS/python" --strip-components 1
  [ -e "$TOOLS/python/bin/python" ] || ln -s python3 "$TOOLS/python/bin/python"
else
  say "1/4 独立版 Python 已安装，跳过"
fi
PY="$TOOLS/python/bin/python"

# 2. Python 包
say "2/4 安装 yt-dlp、语音转文字程序、ffmpeg（约 1.3 GB）"
"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q -r "$ROOT/requirements.txt"

# 3. ffmpeg 快捷方式（相对路径，文件夹挪动后仍然有效）
say "3/4 设置 ffmpeg"
FF="$("$PY" -c "import imageio_ffmpeg, os; print(os.path.relpath(imageio_ffmpeg.get_ffmpeg_exe(), '$TOOLS/bin'))")"
ln -sfn "$FF" "$TOOLS/bin/ffmpeg"
"$TOOLS/bin/ffmpeg" -version | head -1

# 4. Whisper 模型
if [ "${1:-}" = "--no-model" ]; then
  say "4/4 按要求跳过语音模型"
else
  say "4/4 下载 Whisper 语音模型（约 1.5 GB，已下载过会跳过）"
  HF_HOME="$TOOLS/models/huggingface" "$PY" -c "from huggingface_hub import snapshot_download as d; print(d('$MODEL'))"
fi

# 个人文件都放在 local/（不进主仓库，可以单独备份到你自己的私有仓库）
mkdir -p "$ROOT/local"
[ -f "$ROOT/local/settings.json" ] || { cp "$ROOT/config/settings.example.json" "$ROOT/local/settings.json"; echo "已创建 local/settings.json，请打开改成你自己的输出文件夹和浏览器。"; }
[ -f "$ROOT/local/profile.md" ] || { cp "$ROOT/config/profile.example.md" "$ROOT/local/profile.md"; echo "已创建 local/profile.md，可以按自己的情况修改。"; }

say "安装完成。接下来在 Claude 桌面应用的 Code 标签页里，用这个文件夹开一个会话，把B站链接发给 Claude 即可。"
