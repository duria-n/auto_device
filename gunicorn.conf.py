# gunicorn.conf.py — Gunicorn 生产部署配置
#
# 启动命令（在项目根目录执行）：
#   gunicorn -c gunicorn.conf.py "app:create_app()"
#
# 或直接：
#   ./start.sh

import os
import multiprocessing

# ── 绑定地址 ──────────────────────────────────────────────────────────
# 0.0.0.0 = 监听所有网卡（局域网可访问）
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "5000")
bind = f"{host}:{port}"

# ── Worker 配置 ────────────────────────────────────────────────────────
# LLM 推理是 CPU/GPU 密集型，worker 数不宜过多
# 纯模板模式可设 CPU核数×2+1；LLM 模式建议 1~2
worker_class = "sync"                     # sync 适合阻塞型 LLM 调用
workers      = int(os.getenv("WORKERS", "2"))
threads      = int(os.getenv("THREADS", "4"))   # 每 worker 线程数

# ── 超时 ──────────────────────────────────────────────────────────────
# LLM 推理可能较慢，设长一些
timeout      = int(os.getenv("TIMEOUT", "300"))   # 5分钟
keepalive    = 5

# ── 日志 ──────────────────────────────────────────────────────────────
loglevel     = os.getenv("LOG_LEVEL", "info")
accesslog    = os.getenv("ACCESS_LOG", "-")   # "-" = stdout
errorlog     = os.getenv("ERROR_LOG",  "-")
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sµs'

# ── 进程管理 ──────────────────────────────────────────────────────────
pidfile      = "/tmp/oled_generator.pid"
preload_app  = False    # False = 每个 worker 单独加载（HF 模型不共享，避免显存翻倍）

# ── 优雅重启 ──────────────────────────────────────────────────────────
graceful_timeout = 30
