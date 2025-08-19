# # app/__init__.py
#
# from flask import Flask
# from flask_cors import CORS
#
# import os
#
# def create_app():
#     app = Flask(__name__)
#     CORS(app)
#     app.config["UPLOAD_FOLDER"] = os.path.abspath("uploads")
#     from app.route import register_routes  # ✅ 改成匯入 register_routes 函數
#     # ✅ 註冊所有路由
#     register_routes(app)
#
#     return app
# app/__init__.py - 基本版本
# app/__init__.py - 加入數據載入測試
from flask import Flask, jsonify, render_template
from flask_cors import CORS
import os

def create_app():
    app = Flask(
        __name__,
        template_folder="templates",       # ✅ HTML 存放位置
        static_folder="static"            # ✅ CSS、JS 存放位置
    )

    CORS(app)

    # 測試數據載入
    try:
        import pandas as pd
        df = pd.read_excel("data/TESTData.xlsx")
        print(f"✓ Successfully loaded Excel with {len(df)} rows")
        data_status = f"Data loaded: {len(df)} rows"
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        data_status = f"Data load failed: {str(e)}"

    # @app.route("/")
    # def index():
    #     return render_template("index.html")
    @app.route("/")
    def index():
        try:
            return render_template("index.html")
        except Exception as e:
            return f"HTML template rendering failed: {e}"

    @app.route("/healthz")
    def healthz():
        return "ok", 200

    @app.route("/data-status")
    def data_status_route():
        return {"status": data_status}
    from app.route import register_routes  # ✅ 放在 create_app 開頭
    register_routes(app)  # ✅ 加在 return app 前

    return app
