#!/bin/bash
# start.sh — OLED器件例生成器 一键启动脚本
# 用法：bash start.sh [dev|prod]

set -e
cd "$(dirname "$0")"

MODE=${1:-prod}

# ── 检查 .env ─────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    echo "⚠  未找到 .env，从模板创建..."
    cp .env.example .env
    echo "✓  已创建 .env，请按需修改后重新运行"
fi

# ── 读取配置 ──────────────────────────────────────────────────────────
source .env 2>/dev/null || true
PORT=${PORT:-5000}
HOST=${HOST:-0.0.0.0}

# ── 获取本机局域网 IP ─────────────────────────────────────────────────
LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║      OLED器件例专利生成器                 ║"
echo "╚═══════════════════════════════════════════╝"
echo ""
echo "  模式:     $MODE"
echo "  端口:     $PORT"
echo "  本机访问: http://localhost:$PORT"
echo "  局域网:   http://$LAN_IP:$PORT"
echo ""

if [ "${ENABLE_ACCESS_CODE}" = "true" ] || [ "${ENABLE_ACCESS_CODE}" = "1" ]; then
    echo "  🔑 访问码已启用"
    if [ -n "${ACCESS_CODE}" ]; then
        echo "  访问码: ${ACCESS_CODE}"
    else
        echo "  访问码: (启动时随机生成，见日志)"
    fi
    echo ""
fi

# ── 启动 ──────────────────────────────────────────────────────────────
if [ "$MODE" = "dev" ]; then
    echo "  [开发模式] 使用 Flask 内置服务器（热重载）"
    echo "─────────────────────────────────────────────"
    FLASK_DEBUG=1 python app.py

else
    echo "  [生产模式] 使用 Gunicorn"
    echo "─────────────────────────────────────────────"

    # 检查 gunicorn 是否安装
    if ! command -v gunicorn &> /dev/null; then
        echo "✗ 未找到 gunicorn，请先安装："
        echo "  pip install gunicorn"
        exit 1
    fi

    gunicorn -c gunicorn.conf.py "app:create_app()"
fi
