#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Colors for log prefix
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BACKEND_PID=""
FRONTEND_PID=""
CLEANED=0

cleanup() {
    if [ "$CLEANED" -eq 1 ]; then return; fi
    CLEANED=1
    echo ""
    echo -e "${YELLOW}[start.sh] 正在停止服务...${NC}"

    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
        wait "$BACKEND_PID" 2>/dev/null
        echo -e "${YELLOW}[start.sh] 后端已停止${NC}"
    fi

    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null
        wait "$FRONTEND_PID" 2>/dev/null
        echo -e "${YELLOW}[start.sh] 前端已停止${NC}"
    fi

    echo -e "${YELLOW}[start.sh] 所有服务已停止${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Company Skill Creator${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# --- Backend ---
echo -e "${BLUE}[start.sh] 启动后端 (port 8046)...${NC}"
cd "$ROOT/backend"
python server.py 2>&1 | while IFS= read -r line; do
    echo -e "${BLUE}[backend]${NC} $line"
done &
BACKEND_PID=$!

# --- Frontend ---
echo -e "${GREEN}[start.sh] 启动前端 (port 5173)...${NC}"
cd "$ROOT/frontend"
npx vite --host 2>&1 | while IFS= read -r line; do
    echo -e "${GREEN}[frontend]${NC} $line"
done &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}----------------------------------------${NC}"
echo -e "${GREEN}  前端: http://localhost:5173${NC}"
echo -e "${GREEN}  后端: http://localhost:8046${NC}"
echo -e "${GREEN}  API文档: http://localhost:8046/docs${NC}"
echo -e "${GREEN}  按 Ctrl+C 停止所有服务${NC}"
echo -e "${GREEN}----------------------------------------${NC}"
echo ""

# Wait for either process to exit
wait -n "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
cleanup
