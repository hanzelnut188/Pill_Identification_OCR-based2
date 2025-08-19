from flask import Flask, send_from_directory
from flask_cors import CORS
import os
from app.route import register_routes  # 改為導入函數！

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config["UPLOAD_FOLDER"] = os.path.abspath("uploads")
    register_routes(app)

    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return app
