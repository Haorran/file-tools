#!/bin/bash
# common.sh — 共享工具函数
# 被 dir_compare_check.sh 和 dir_duplicate_check.sh 共同引用
# 兼容 macOS / Linux

# ==================== 平台检测 ====================
IS_MACOS=false
if [[ "$(uname -s)" == "Darwin" ]]; then
    IS_MACOS=true
fi

# ==================== 跨平台命令 ====================
_sha256() {
    if $IS_MACOS; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        sha256sum "$1" | awk '{print $1}'
    fi
}

_stat_size() {
    if $IS_MACOS; then
        stat -f "%z" "$1"
    else
        stat -c "%s" "$1"
    fi
}

_dd_head() {
    local file="$1" bs="$2"
    if $IS_MACOS; then
        dd if="$file" bs="$bs" count=1 2>/dev/null
    else
        dd if="$file" bs="$bs" count=1 iflag=direct,nonblock 2>/dev/null
    fi
}

_dd_tail() {
    local file="$1" bs="$2" skip="$3"
    if $IS_MACOS; then
        dd if="$file" bs="$bs" skip="$skip" count=1 2>/dev/null
    else
        dd if="$file" bs="$bs" skip="$skip" count=1 iflag=direct,nonblock 2>/dev/null
    fi
}

# ==================== 颜色常量 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ==================== 临时文件管理 ====================
_CLEANUP_FILES=()

setup_cleanup() {
    trap '_cleanup_all' EXIT INT TERM HUP
}

create_temp() {
    local f
    f=$(mktemp)
    _CLEANUP_FILES+=("$f")
    echo "$f"
}

_cleanup_all() {
    for f in "${_CLEANUP_FILES[@]}"; do
        rm -f "$f"
    done
}

# ==================== 容量格式化 ====================
format_bytes() {
    local bytes="$1"
    if (( bytes < 1024 )); then echo "${bytes} B"; return; fi
    local kb=$(( bytes / 1024 ))
    if (( kb < 1024 )); then echo "${kb} KB"; return; fi
    local mb=$(( kb / 1024 ))
    if (( mb < 1024 )); then echo "${mb} MB"; return; fi
    local gb=$(( mb / 1024 ))
    echo "${gb} GB"
}

# ==================== 哈希计算 ====================
# 计算文件首尾各 N 字节的局部哈希
partial_hash() {
    local file="$1"
    local block_size=${2:-65536}
    local file_sz
    file_sz=$(_stat_size "$file")

    local head
    local tail
    if (( file_sz <= block_size )); then
        head=$(_sha256 "$file")
        tail="$head"
    else
        head=$(_dd_head "$file" "$block_size" | _sha256 /dev/stdin)
        tail=$(_dd_tail "$file" "$block_size" $((file_sz / block_size - 1)) | _sha256 /dev/stdin)
    fi
    echo "${head}_${tail}"
}

full_sha256() {
    _sha256 "$1"
}

format_block_size() {
    local bytes="$1"
    if (( bytes >= 1048576 )); then echo "$(( bytes / 1048576 ))MB"
    elif (( bytes >= 1024 )); then echo "$(( bytes / 1024 ))KB"
    else echo "${bytes}B"
    fi
}

# ==================== 进度输出 ====================
progress() {
    local current="$1"
    local total="$2"
    local name="$3"
    local pct=0
    if [[ "$total" =~ ^[0-9]+$ ]] && (( total > 0 )); then
        pct=$(( current * 100 / total ))
    fi
    if [[ "$total" =~ ^[0-9]+$ ]]; then
        printf "\r${YELLOW}进度 [%d%%] %d/%d %s${NC}" "$pct" "$current" "$total" "$name" >&2
    else
        printf "\r${YELLOW}进度 [%d] %d %s${NC}" "$current" "$current" "$name" >&2
    fi
}

progress_done() {
    echo "" >&2
}

# ==================== 目录校验 ====================
require_dir() {
    local d="$1"
    local label="${2:-目录}"
    if [[ ! -d "$d" ]]; then
        echo -e "${RED}${label}不存在：$d${NC}" >&2
        exit 2
    fi
}
