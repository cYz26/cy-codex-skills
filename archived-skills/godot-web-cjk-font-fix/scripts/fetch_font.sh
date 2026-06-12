#!/usr/bin/env bash
set -euo pipefail

FONT_ID="${1:-noto-sans-cjk-sc-regular-otf}"
CACHE_DIR="${FONT_CACHE_DIR:-$HOME/.codex/cache/fonts}"

download_with_curl() {
	local url="$1"
	local out="$2"
	curl -fL --retry 3 --retry-delay 2 --connect-timeout 10 --max-time 300 -o "$out" "$url"
}

download_with_wget() {
	local url="$1"
	local out="$2"
	wget -q --tries=3 --timeout=30 -O "$out" "$url"
}

download_file() {
	local url="$1"
	local out="$2"
	if [ -f "$url" ]; then
		cp "$url" "$out"
		return 0
	fi
	if [[ "$url" == file://* ]]; then
		local file_path="${url#file://}"
		file_path="${file_path//%20/ }"
		if [ -f "$file_path" ]; then
			cp "$file_path" "$out"
			return 0
		fi
	fi
	if command -v curl >/dev/null 2>&1; then
		download_with_curl "$url" "$out"
	elif command -v wget >/dev/null 2>&1; then
		download_with_wget "$url" "$out"
	else
		echo "error: curl or wget is required for downloading font files." >&2
		return 1
	fi
}

declare -a CANDIDATE_URLS=()
FILE_NAME=""

case "$FONT_ID" in
	noto-sans-cjk-sc-regular-otf)
		FILE_NAME="NotoSansCJKsc-Regular.otf"
		CANDIDATE_URLS=(
			"${FONT_SOURCE_URL:-}"
			"https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
			"https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
		)
		;;
	source-han-sans-cn-regular-otf)
		FILE_NAME="SourceHanSansCN-Regular.otf"
		CANDIDATE_URLS=(
			"${FONT_SOURCE_URL:-}"
			"https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SimplifiedChinese/SourceHanSansCN-Regular.otf"
			"https://raw.githubusercontent.com/adobe-fonts/source-han-sans/release/OTF/SimplifiedChinese/SourceHanSansCN-Regular.otf"
		)
		;;
	*)
		echo "error: unsupported font id '$FONT_ID'." >&2
		echo "supported: noto-sans-cjk-sc-regular-otf, source-han-sans-cn-regular-otf" >&2
		exit 1
		;;
esac

mkdir -p "$CACHE_DIR"
TARGET_PATH="$CACHE_DIR/$FILE_NAME"
TMP_PATH="$TARGET_PATH.part"

if [ -s "$TARGET_PATH" ]; then
	echo "$TARGET_PATH"
	exit 0
fi

rm -f "$TMP_PATH"
for url in "${CANDIDATE_URLS[@]}"; do
	if [ -z "$url" ]; then
		continue
	fi
	echo "fetch font: $url" >&2
	if download_file "$url" "$TMP_PATH"; then
		mv "$TMP_PATH" "$TARGET_PATH"
		echo "$TARGET_PATH"
		exit 0
	fi
done

rm -f "$TMP_PATH"
echo "error: failed to download font '$FONT_ID'." >&2
echo "hint: set FONT_SOURCE_URL to a reachable direct file URL and retry." >&2
exit 1
