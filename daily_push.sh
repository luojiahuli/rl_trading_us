#!/usr/bin/env bash
# 每日美股量化分析推送脚本
set -e
cd "$(dirname "$0")"

REPORT_LOG="output/logs/daily_us_$(date +%Y%m%d).log"
mkdir -p output/logs

echo "=== 美股量化日报 $(date +%Y-%m-%d) ===" > "$REPORT_LOG"
python3 main.py >> "$REPORT_LOG" 2>&1

tail -5 "$REPORT_LOG"
echo "日志已保存: $REPORT_LOG"
