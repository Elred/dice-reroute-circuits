from flask import Flask, jsonify
from flask_cors import CORS
from drc_stat_engine.api.routes import api_bp


def create_app():
    app = Flask(__name__)
    CORS(app, origins=["http://localhost:5173"])
    app.register_blueprint(api_bp)

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        app.logger.exception("Unhandled exception")
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    create_app().run(port=5000, debug=True)
