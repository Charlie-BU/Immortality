#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

ROLE="${1:-lark}"

if [ "$ROLE" = "http" ]; then
    uv run robyn -m src.robyn_main --process=1 --workers=3  # 切不可开多进程，否则会导致一个耗时请求无法正确处理 why??
elif [ "$ROLE" = "lark" ]; then
    uv run -m src.lark_main
else
    echo "Usage: $0 [http|lark]"
    exit 1
fi
