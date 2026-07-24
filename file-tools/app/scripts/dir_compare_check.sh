#!/bin/bash
set -eo pipefail
# dir_compare_check.sh — 目录比较脚本
# 比较两个目录的文件清单差异与内容一致性
# 用法：dir_compare_check.sh [0|1|2] 目录A 目录B [块大小]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# ==================== 参数校验 ====================
if [[ $# -lt 3 || $# -gt 4 ]]; then
    echo -e "${RED}参数错误！使用格式：$0 [0|1|2] 目录A 目录B [块大小]${NC}"
    echo "  0 = 极速轻量：仅文件名 + 文件总大小"
    echo "  1 = 推荐高速：大小 + 首尾局部哈希"
    echo "  2 = 完整严谨：大小 + 局部哈希 + 全文件SHA256"
    exit 1
fi

CHECK_MODE="$1"
DIR_A="${2%/}"
DIR_B="${3%/}"
BLOCK_SIZE="${4:-65536}"

if [[ "$CHECK_MODE" != "0" && "$CHECK_MODE" != "1" && "$CHECK_MODE" != "2" ]]; then
    echo -e "${RED}第一个参数仅允许 0、1、2${NC}"
    exit 1
fi

require_dir "$DIR_A" "目录A"
require_dir "$DIR_B" "目录B"

setup_cleanup

# ==================== 辅助函数 ====================
# 导出目录的相对路径文件清单（排序）
export_rel_list() {
    local base="$1"
    local out="$2"
    find "$base" -type f -print0 \
    | xargs -0 -I{} sh -c 'echo "${1#$2/}"' _ {} "$base" \
    | sed '/^$/d' | sort > "$out"
}

# 扫描目录总文件数、总字节
scan_dir_total() {
    local dir="$1"
    local name="$2"
    local tmp_list
    tmp_list=$(create_temp)
    echo -e "\n${CYAN}【$name】预扫描全部文件容量...${NC}" >&2
    find "$dir" -type f -print0 > "$tmp_list"
    local total=0
    local total_bytes=0
    if [[ -s "$tmp_list" ]]; then
        while IFS= read -r -d '' file; do
            local sz
            sz=$(_stat_size "$file")
            total_bytes=$(( total_bytes + sz ))
            total=$(( total + 1 ))
            progress "$total" "?" "$name"
        done < "$tmp_list"
    fi
    progress_done
    echo -e "${GREEN}$name 扫描完成${NC}" >&2
    echo -e "$total\n$total_bytes"
}

# ==================== 头部打印 ====================
case "$CHECK_MODE" in
    0) mode_desc="极速轻量比对（文件名+总大小）" ;;
    1) mode_desc="高速视频专用（大小+首尾局部哈希）" ;;
    2) mode_desc="完整全量哈希比对（速度慢，大视频不推荐）" ;;
esac

echo -e "${BOLD}==================== ${mode_desc} ====================${NC}"
echo "目录A：$DIR_A"
echo "目录B：$DIR_B"
echo -e "${BOLD}=========================================================================${NC}"

# ==================== 步骤1：文件清单比对 ====================
echo -e "\n${CYAN}[步骤1] 比对全部文件路径清单${NC}"

tmp_list_a=$(create_temp)
tmp_list_b=$(create_temp)
export_rel_list "$DIR_A" "$tmp_list_a"
export_rel_list "$DIR_B" "$tmp_list_b"

onlyA=$(comm -23 "$tmp_list_a" "$tmp_list_b")
onlyB=$(comm -13 "$tmp_list_a" "$tmp_list_b")
both_list=$(comm -12 "$tmp_list_a" "$tmp_list_b")
list_error=0

if [[ -n "$onlyA" ]]; then
    echo -e "${RED}❌ 【目录B缺失】仅目录A存在文件：${NC}"
    echo "$onlyA"
    list_error=1
fi
if [[ -n "$onlyB" ]]; then
    echo -e "${RED}❌ 【目录A缺失】仅目录B存在文件：${NC}"
    echo "$onlyB"
    list_error=1
fi
if [[ $list_error -eq 0 ]]; then
    echo -e "${GREEN}✅ 文件清单完全一致${NC}"
fi

# ==================== 步骤2：内容校验 ====================
content_error=0
if [[ "$CHECK_MODE" != "0" ]]; then
    if [[ "$CHECK_MODE" == "1" ]]; then
        echo -e "\n${CYAN}[步骤2] 高速校验：文件大小 + 首尾$(format_block_size $BLOCK_SIZE)局部哈希${NC}"
    else
        echo -e "\n${CYAN}[步骤2] 完整校验：大小 + 局部哈希 + 全文件SHA256（耗时久）${NC}"
    fi

    fail_flag=$(create_temp)
    > "$fail_flag"

    # 读取共有文件列表（兼容 bash 3.x+）
    total_both=0
    while IFS= read -r rel_path; do
        [ -z "$rel_path" ] && continue
        total_both=$((total_both + 1))
    done <<EOF2
$both_list
EOF2

    current=0
    while IFS= read -r rel_path; do
        [ -z "$rel_path" ] && continue
        current=$((current + 1))
        file_a="${DIR_A}/${rel_path}"
        file_b="${DIR_B}/${rel_path}"

        if [[ ! -f "$file_a" || ! -f "$file_b" ]]; then
            echo -e "\n${YELLOW}跳过非文件：$rel_path${NC}"
            continue
        fi

        progress "$current" "$total_both" "$rel_path"

        # 先对比文件大小
        size_a=$(_stat_size "$file_a")
        size_b=$(_stat_size "$file_b")
        if [[ "$size_a" != "$size_b" ]]; then
            echo -e "\n${RED}❌ 文件大小不一致${NC}"
            echo "相对路径：$rel_path"
            echo "A路径：$file_a | 大小：$size_a Byte"
            echo "B路径：$file_b | 大小：$size_b Byte"
            echo 1 >> "$fail_flag"
            continue
        fi

        # 局部首尾哈希校验（模式1/2都执行）
        hash_a=$(partial_hash "$file_a" $BLOCK_SIZE)
        hash_b=$(partial_hash "$file_b" $BLOCK_SIZE)
        if [[ "$hash_a" != "$hash_b" ]]; then
            echo -e "\n${RED}❌ 文件首尾片段不一致（内容不同）${NC}"
            echo "相对路径：$rel_path"
            echo "A完整路径：$file_a | 局部哈希：$hash_a"
            echo "B完整路径：$file_b | 局部哈希：$hash_b"
            echo 1 >> "$fail_flag"
            continue
        fi

        # 仅模式2才计算完整 sha256
        if [[ "$CHECK_MODE" == "2" ]]; then
            full_a=$(full_sha256 "$file_a")
            full_b=$(full_sha256 "$file_b")
            if [[ "$full_a" != "$full_b" ]]; then
                echo -e "\n${RED}❌ 完整SHA256哈希不一致${NC}"
                echo "相对路径：$rel_path"
                echo "A完整路径：$file_a | SHA256: $full_a"
                echo "B完整路径：$file_b | SHA256: $full_b"
                echo 1 >> "$fail_flag"
            fi
        fi
    done <<EOF2
$both_list
EOF2
    progress_done
    [[ -s "$fail_flag" ]] && content_error=1
fi

# ==================== 步骤3：容量统计 ====================
echo -e "\n${CYAN}[步骤3] 目录总文件与总容量统计${NC}"

res_a=$(scan_dir_total "$DIR_A" "目录A")
total_a_files=$(echo "$res_a" | head -n1)
total_a_bytes=$(echo "$res_a" | tail -n1)

res_b=$(scan_dir_total "$DIR_B" "目录B")
total_b_files=$(echo "$res_b" | head -n1)
total_b_bytes=$(echo "$res_b" | tail -n1)

# 汇总表格
echo -e "\n${CYAN}==================== 容量汇总 ====================${NC}"
printf "%-8s | %8s | %12s | %s\n" "" "文件总数" "总字节数" "可读容量"
echo "--------------------------------------------------"
printf "%-8s | %8d | %12d | %s\n" "目录A" "$total_a_files" "$total_a_bytes" "$(format_bytes $total_a_bytes)"
printf "%-8s | %8d | %12d | %s\n" "目录B" "$total_b_files" "$total_b_bytes" "$(format_bytes $total_b_bytes)"
echo -e "${CYAN}==================================================${NC}"

total_error=0
(( total_a_files != total_b_files )) && echo -e "${RED}❌ 文件总数不一致${NC}" && total_error=1
(( total_a_bytes != total_b_bytes )) && echo -e "${RED}❌ 整体总容量字节不一致${NC}" && total_error=1

# ==================== 最终结论 ====================
final_error=0
(( list_error == 1 )) && final_error=1
(( total_error == 1 )) && final_error=1
(( content_error == 1 )) && final_error=1

if (( final_error == 1 )); then
    echo "RESULT:has_diff"
    echo -e "\n${RED}${BOLD}❌ 校验失败：存在文件缺失/容量/内容差异，详见上方日志${NC}"
    exit 99
else
    echo "RESULT:ok"
    echo -e "\n${GREEN}${BOLD}✅ 全部校验通过，两个目录完全一致${NC}"
    case "$CHECK_MODE" in
        0) echo -e "${YELLOW}提示：当前极速模式仅核对文件名与大小，推荐使用模式1做精准校验${NC}" ;;
        1) echo -e "${YELLOW}提示：使用首尾$(format_block_size $BLOCK_SIZE)局部哈希校验，兼顾速度与准确率${NC}" ;;
    esac
    exit 0
fi
