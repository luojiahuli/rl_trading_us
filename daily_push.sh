#!/usr/bin/env bash
# 每日美股量化分析推送 + 自动推送 GitHub
# 运行: bash daily_push.sh
# 建议 cron: 30 15 * * 1-5

set -e
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
REPORT_LOG="output/logs/daily_us_$(date +%Y%m%d).log"
mkdir -p output/logs

echo "=== 美股量化日报 $(date +%Y-%m-%d) ===" > "$REPORT_LOG"

# 1. 运行分析
python3 main.py >> "$REPORT_LOG" 2>&1
RET=$?
if [ $RET -ne 0 ]; then
    echo "运行失败 (exit=$RET)" >> "$REPORT_LOG"
    cat "$REPORT_LOG" | tail -5
    exit $RET
fi

echo "分析完成" >> "$REPORT_LOG"

# 2. 生成回测报告
python3 generate_report.py >> "$REPORT_LOG" 2>&1 || echo "报告生成跳过" >> "$REPORT_LOG"

# 3. 检查是否有变更，推送到 GitHub
cd "$PROJECT_DIR"

if ! git config user.name > /dev/null 2>&1; then
    git config user.name "luojiahuli"
    git config user.email "luojiahuli@users.noreply.github.com"
fi

git add src/backtest/ README.md output/reports/ daily_push.sh generate_report.py src/agents/ config.py main.py

if git diff --cached --quiet; then
    echo "无变更，跳过推送" >> "$REPORT_LOG"
else
    DATE_TAG=$(date '+%Y-%m-%d')
    git commit -m "daily us analysis ${DATE_TAG}"
    git push origin main 2>&1 >> "$REPORT_LOG"
    echo "已推送 GitHub" >> "$REPORT_LOG"
fi

echo "完成 $(date)" >> "$REPORT_LOG"
cat "$REPORT_LOG" | tail -5
