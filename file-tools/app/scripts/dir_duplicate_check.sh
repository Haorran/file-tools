#!/bin/bash
set -eo pipefail
# dir_duplicate_check.sh — 目录内文件工具箱脚本
# 检查单个目录内是否有内容重复的文件
# 用法：dir_duplicate_check.sh [0|1|2] 扫描目录 [过滤阈值KB] [块大小]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# 不可见分隔符，用于 awk 字段分割
SEP=$'\001'

# ==================== 参数校验 ====================
if [[ $# -lt 2 || $# -gt 4 ]]; then
    echo -e "${RED}参数错误！使用格式：$0 [0|1|2] 扫描目录 [过滤阈值KB] [块大小]${NC}"
    echo "  0 = 仅文件名匹配（无内容校验）"
    echo "  1 = 大小+首尾局部哈希（推荐视频，忽略文件名）"
    echo "  2 = 完整全文件SHA256校验"
    echo "示例："
    echo "  $0 1 /vol1/media          # 全部文件参与"
    echo "  $0 1 /vol1/media 1024     # 仅 ≥1024KB 文件参与"
    exit 1
fi

SCAN_MODE="$1"
SCAN_DIR="${2%/}"
FILTER_KB="$3"
BLOCK_SIZE="${4:-65536}"

if [[ ! "$SCAN_MODE" =~ ^[012]$ ]]; then
    echo -e "${RED}第一个参数仅支持 0、1、2${NC}"
    exit 1
fi

require_dir "$SCAN_DIR" "扫描目录"

if [[ -n "$FILTER_KB" ]]; then
    if ! [[ "$FILTER_KB" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}第三个参数必须是纯数字，单位KB${NC}"
        exit 1
    fi
fi

setup_cleanup

# ==================== 头部打印 ====================
case "$SCAN_MODE" in
    0) mode_desc="仅文件名匹配（无内容校验）" ;;
    1) mode_desc="大小+首尾局部哈希（推荐视频）" ;;
    2) mode_desc="完整全文件SHA256校验" ;;
esac

echo -e "${BOLD}==================== 目录重复文件扫描 ====================${NC}"
echo "扫描目录：$SCAN_DIR"
echo "校验模式：$SCAN_MODE | $mode_desc"
if [[ -n "$FILTER_KB" ]]; then
    echo "文件过滤：仅 ≥${FILTER_KB}KB 的文件参与校验"
else
    echo "文件过滤：无过滤，所有文件参与校验"
fi
echo -e "${BOLD}================================================================${NC}"

# ==================== 步骤1：生成文件清单 ====================
echo -e "\n${CYAN}[步骤1] 遍历目录生成文件清单...${NC}"

tmp_filelist=$(create_temp)
find "$SCAN_DIR" -type f > "$tmp_filelist"
total_files=$(wc -l < "$tmp_filelist")
echo -e "目录内总文件数：${GREEN}$total_files${NC}"

# ==================== 步骤2：计算校验标识并分组 ====================
echo -e "\n${CYAN}[步骤2] 计算校验标识并分组...${NC}"

tmp_cache=$(create_temp)
current=0
skip_count=0

while IFS= read -r file; do
    current=$((current + 1))
    file_base=$(basename "$file")
    file_bytes=$(_stat_size "$file")
    file_kb=$(( file_bytes / 1024 ))

    # 文件大小过滤
    if [[ -n "$FILTER_KB" ]] && (( file_kb < FILTER_KB )); then
        skip_count=$((skip_count + 1))
        continue
    fi

    processed=$((current - skip_count))
    progress "$processed" "$((total_files - skip_count))" "$file_base"

    # 根据模式计算分组 key
    case "$SCAN_MODE" in
        0) key="$file_base" ;;
        1) key=$(partial_hash "$file" $BLOCK_SIZE) ;;
        2) key=$(full_sha256 "$file") ;;
    esac

    # 写入缓存：key \t size \t filepath
    echo "${key}${SEP}${file_bytes}${SEP}${file}" >> "$tmp_cache"
done < "$tmp_filelist"

progress_done

if [[ -n "$FILTER_KB" ]]; then
    echo -e "${YELLOW}本次扫描跳过小文件总数：${skip_count} 个（小于${FILTER_KB}KB）${NC}"
fi

# ==================== 步骤3：分组匹配并输出 ====================
echo -e "\n${BOLD}==================== 重复文件扫描结果 ====================${NC}"

tmp_result=$(create_temp)

sort -t"$SEP" -k1,1 "$tmp_cache" | awk -v sep="$SEP" '
BEGIN { FS = sep }
{
    gkey = $1
    sz = $2
    path = $3
    if (gkey == last_gkey) {
        paths[gkey] = paths[gkey] "\n  " path
        cnt[gkey]++
        total_dup++
    } else {
        last_gkey = gkey
        paths[gkey] = "  " path
        cnt[gkey] = 1
        size_map[gkey] = sz
    }
}
END {
    found = 0
    for (k in cnt) {
        if (cnt[k] >= 2) {
            found = 1
            print "【分组校验标识】" k
            print "文件字节大小：" size_map[k] " Bytes (" size_map[k]/1024/1024 " MB)"
            print "匹配文件路径列表："
            print paths[k]
            print "-------------------------------------------------"
        }
    }
    if (found == 0) {
        print "NO_DUPLICATES"
    } else {
        print "TOTAL_GROUPS:" found
        print "TOTAL_DUP_FILES:" total_dup
    }
}' > "$tmp_result"

# 输出结果
if grep -q "NO_DUPLICATES" "$tmp_result"; then
    echo "RESULT:no_dup"
    echo -e "${GREEN}✅ 未检测到任何重复文件${NC}"
else
    group_total=0
    file_dup_total=0

    while IFS= read -r line; do
        if [[ "$line" =~ ^【分组校验标识】 ]]; then
            group_total=$((group_total + 1))
            echo -e "\n${YELLOW}$line${NC}"
        elif [[ "$line" == "-------------------------------------------------" ]]; then
            continue
        elif [[ "$line" =~ ^"TOTAL_GROUPS:" ]]; then
            group_total="${line#*:}"
        elif [[ "$line" =~ ^"TOTAL_DUP_FILES:" ]]; then
            file_dup_total="${line#*:}"
        elif [[ "$line" =~ ^"  /" ]]; then
            echo "$line"
        else
            echo "$line"
        fi
    done < "$tmp_result"

    echo -e "\n${CYAN}==================== 统计汇总 ====================${NC}"
    echo -n "重复文件分组总数："
    echo -e "${RED}$group_total${NC} 组"
    echo -n "冗余重复文件总数："
    echo -e "${RED}$file_dup_total${NC} 个"
    echo "提示：同一分组校验标识一致，文件内容相同；每组仅保留1份，其余可删除释放磁盘空间"
    echo "RESULT:has_dup"
fi

exit 0
