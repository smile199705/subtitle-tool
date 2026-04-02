#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PID_FILE="$SCRIPT_DIR/.server.pid"
PORT=8765

echo "=== 字幕生产工具 ==="

# 1. Check Python3
if ! command -v python3 &>/dev/null; then
  echo "[错误] 未找到 python3，请先安装 Python 3.9+"
  exit 1
fi
echo "[1/5] Python3: $(python3 --version)"

# 2. Create venv if needed
if [ ! -d "$VENV" ]; then
  echo "[2/5] 创建虚拟环境..."
  python3 -m venv "$VENV"
else
  echo "[2/5] 虚拟环境已存在，跳过"
fi

# 3. Activate
source "$VENV/bin/activate"

# 4. Install requirements
echo "[3/5] 安装依赖（首次较慢）..."
pip install -q --upgrade pip
pip install -q -r "$SCRIPT_DIR/backend/requirements.txt"

# 5. Try mlx-whisper (M1 only, ignore failure)
echo "[4/5] 尝试安装 mlx-whisper（仅 Apple Silicon，失败可忽略）..."
pip install -q mlx-whisper 2>/dev/null && echo "  ✓ mlx-whisper 已安装" || echo "  ⚠ mlx-whisper 安装跳过（非 Apple Silicon 或已安装）"

# Kill any existing server on this port
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  kill "$OLD_PID" 2>/dev/null && echo "  已停止旧服务 (pid=$OLD_PID)" || true
  rm -f "$PID_FILE"
fi

# 6. Start server — 明确用 venv 内的 Python，避免使用系统 Python
echo "[5/5] 启动服务 (port $PORT)..."
cd "$SCRIPT_DIR"
"$VENV/bin/python" backend/server.py > /tmp/subtitle-tool.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"
echo "  服务 PID: $SERVER_PID  日志: /tmp/subtitle-tool.log"

# 7. Wait for server to be ready — 用 nc 检查端口，不依赖 HTTP 客户端
echo "  等待服务就绪..."
for i in $(seq 1 30); do
  sleep 0.5
  if nc -z 127.0.0.1 $PORT 2>/dev/null; then
    echo "  ✓ 服务已就绪"
    break
  fi
  # 检查进程是否意外退出
  if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "  [错误] 服务进程意外退出，查看日志: /tmp/subtitle-tool.log"
    cat /tmp/subtitle-tool.log
    exit 1
  fi
  if [ $i -eq 30 ]; then
    echo "  [错误] 服务启动超时，查看日志: /tmp/subtitle-tool.log"
    cat /tmp/subtitle-tool.log
    exit 1
  fi
done

# 8. Open browser
echo ""
echo "=== 启动成功 ==="
echo "  面板: http://127.0.0.1:$PORT"
echo "  API:  http://127.0.0.1:$PORT"
echo "  停止: ./stop.sh"
echo ""
open "http://127.0.0.1:$PORT"
