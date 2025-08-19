# app/__init__.py

from flask import Flask
from flask_cors import CORS
from app.route import register_routes  # ✅ 改成匯入 register_routes 函數
import os

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config["UPLOAD_FOLDER"] = os.path.abspath("uploads")

    # ✅ 註冊所有路由
    register_routes(app)

    return app
