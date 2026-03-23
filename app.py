"""app.py — Flask 应用工厂"""
from __future__ import annotations
import threading
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from config import Config
from routes.generate import bp as gen_bp
from routes.settings import bp as set_bp
from routes.hf import bp as hf_bp

logger = logging.getLogger(__name__)

# ── 全局并发信号量（防止 LLM 任务堆积爆显存/超时）────────────────────
_job_semaphore = threading.Semaphore(Config.MAX_CONCURRENT_JOBS)


def create_app(cfg: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(cfg)
    app.secret_key = cfg.SECRET_KEY
    CORS(app, supports_credentials=True)

    # 注入信号量供路由使用
    app.job_semaphore = _job_semaphore

    app.register_blueprint(gen_bp)
    app.register_blueprint(set_bp)
    app.register_blueprint(hf_bp)

    # ── 访问码中间件 ──────────────────────────────────────────────────
    @app.before_request
    def check_access():
        if not cfg.ENABLE_ACCESS_CODE:
            return  # 未启用访问码，直接放行

        # 静态资源不拦截
        if request.endpoint in ("static", "auth_page", "auth_verify", "auth_logout"):
            return

        if not session.get("authed"):
            # API 请求返回 JSON 401，页面请求跳转登录页
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "未授权，请先输入访问码"}), 401
            return redirect(url_for("auth_page"))

    # ── 登录页 ────────────────────────────────────────────────────────
    @app.route("/login", methods=["GET"])
    def auth_page():
        if session.get("authed"):
            return redirect("/")
        return render_template("login.html")

    @app.route("/login", methods=["POST"])
    def auth_verify():
        code = request.form.get("code", "").strip()
        if code == cfg.ACCESS_CODE:
            session["authed"] = True
            session.permanent = True
            app.permanent_session_lifetime = __import__("datetime").timedelta(
                seconds=cfg.SESSION_LIFETIME
            )
            return redirect("/")
        return render_template("login.html", error="访问码错误，请重试")

    @app.route("/logout")
    def auth_logout():
        session.clear()
        return redirect(url_for("auth_page"))

    # ── 主页 ──────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("index.html")

    # ── 健康检查（局域网其他机器可 ping 确认服务存活）────────────────
    @app.route("/health")
    def health():
        import platform, sys
        return jsonify({
            "status":   "ok",
            "host":     platform.node(),
            "python":   sys.version.split()[0],
            "debug":    cfg.DEBUG,
            "access_code_enabled": cfg.ENABLE_ACCESS_CODE,
        })

    return app


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = create_app()
    logger.info(f"启动服务 → http://0.0.0.0:{Config.PORT}")
    if Config.ENABLE_ACCESS_CODE:
        logger.info(f"访问码：{Config.ACCESS_CODE}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
