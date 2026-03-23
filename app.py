"""app.py — Flask 应用工厂"""
from flask import Flask, render_template
from flask_cors import CORS
from config import Config
from routes.generate import bp as gen_bp
from routes.settings import bp as set_bp
from routes.hf import bp as hf_bp


def create_app(cfg: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(cfg)
    CORS(app)

    app.register_blueprint(gen_bp)
    app.register_blueprint(set_bp)
    app.register_blueprint(hf_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
