#!/usr/bin/env bash

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Colors for log prefix
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_LOG=""
FRONTEND_LOG=""

cleanup() {
    trap '' SIGINT SIGTERM  # block re-entry during cleanup
    echo ""
    echo -e "${YELLOW}[start.sh] 正在停止服务...${NC}"

    # Kill all child processes of this script (backends, frontends, tails, etc.)
    # Use -9 to force-kill immediately — no hanging
    pkill -9 -P $$ 2>/dev/null || true

    # Clean up temp log files
    [ -n "$BACKEND_LOG" ] && rm -f "$BACKEND_LOG"
    [ -n "$FRONTEND_LOG" ] && rm -f "$FRONTEND_LOG"

    echo -e "${YELLOW}[start.sh] 所有服务已停止${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Company Skill Creator${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# --- Backend ---
# Write to temp log, tail -f for prefixed output
# $! after &> captures the real python PID, not a pipe component
echo -e "${BLUE}[start.sh] 启动后端 (port 8046)...${NC}"
cd "$ROOT/backend"
BACKEND_LOG=$(mktemp)
python server.py &> "$BACKEND_LOG" &
tail -f "$BACKEND_LOG" | while IFS= read -r line; do
    echo -e "${BLUE}[backend]${NC} $line"
done &

# --- Frontend ---
echo -e "${GREEN}[start.sh] 启动前端 (port 5100)...${NC}"
cd "$ROOT/frontend"
FRONTEND_LOG=$(mktemp)
npx vite --host &> "$FRONTEND_LOG" &
tail -f "$FRONTEND_LOG" | while IFS= read -r line; do
    echo -e "${GREEN}[frontend]${NC} $line"
done &

echo ""
echo -e "${GREEN}----------------------------------------${NC}"
echo -e "${GREEN}  前端: http://localhost:5100${NC}"
echo -e "${GREEN}  后端: http://localhost:8046${NC}"
echo -e "${GREEN}  API文档: http://localhost:8046/docs${NC}"
echo -e "${GREEN}  按 Ctrl+C 停止所有服务${NC}"
echo -e "${GREEN}----------------------------------------${NC}"
echo ""

# Keep script alive until cleanup fires
wait
