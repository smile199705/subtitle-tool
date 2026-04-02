#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.server.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "未找到 .server.pid，服务可能未运行"
  exit 0
fi

PID=$(cat "$PID_FILE")
if kill "$PID" 2>/dev/null; then
  echo "已停止服务 (pid=$PID)"
else
  echo "进程 $PID 不存在（可能已退出）"
fi
rm -f "$PID_FILE"
