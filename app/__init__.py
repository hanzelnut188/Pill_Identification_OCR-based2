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

# from flask import Flask, jsonify, render_template
# from flask_cors import CORS
# import os
#
# def create_app():
#     app = Flask(
#         __name__,
#         template_folder="templates",       # ✅ HTML 存放位置
#         static_folder="static"            # ✅ CSS、JS 存放位置
#     )
#
#     CORS(app)
#
#     # 測試數據載入
#     try:
#         import pandas as pd
#         df = pd.read_excel("data/TESTData.xlsx")
#         print(f"✓ Successfully loaded Excel with {len(df)} rows")
#         data_status = f"Data loaded: {len(df)} rows"
#     except Exception as e:
#         print(f"✗ Error loading data: {e}")
#         data_status = f"Data load failed: {str(e)}"
#
#     # @app.route("/")
#     # def index():
#     #     return render_template("index.html")
#     @app.route("/")
#     def index():
#         try:
#             return render_template("index.html")
#         except Exception as e:
#             return f"HTML template rendering failed: {e}"
#
#     @app.route("/healthz")
#     def healthz():
#         return "ok", 200
#
#     # 導入並註冊其他路由（放在最後）
#     try:
#         from app.route import register_routes
#         register_routes(app)
#         print("✓ Additional routes registered")
#     except Exception as e:
#         print(f"✗ Error registering additional routes: {e}")
#
#     return app

# app/__init__.py - 除錯版本

import os
import sys

# 最早的除錯輸出
print("=== DEBUG: Starting app/__init__.py ===")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")

try:
    from flask import Flask, jsonify
    print("✓ Flask imported successfully")
except Exception as e:
    print(f"✗ Error importing Flask: {e}")
    sys.exit(1)

try:
    from flask_cors import CORS
    print("✓ Flask-CORS imported successfully")
except Exception as e:
    print(f"✗ Error importing Flask-CORS: {e}")

def create_app():
    print("=== DEBUG: create_app() called ===")

    try:
        app = Flask(__name__)
        print("✓ Flask app created")
    except Exception as e:
        print(f"✗ Error creating Flask app: {e}")
        raise

    try:
        CORS(app)
        print("✓ CORS configured")
    except Exception as e:
        print(f"✗ Error configuring CORS: {e}")

    # 基本路由（不涉及模板）
    @app.route("/")
    def index():
        return "Hello from create_app! Service is running."

    @app.route("/healthz")
    def healthz():
        return "ok", 200

    @app.route("/debug-info")
    def debug_info():
        return {
            "python_version": sys.version,
            "cwd": os.getcwd(),
            "files_in_cwd": os.listdir("."),
            "app_folder_exists": os.path.exists("app"),
            "templates_folder_exists": os.path.exists("app/templates"),
            "static_folder_exists": os.path.exists("app/static")
        }

    # 測試數據載入（可能的問題來源）
    try:
        print("=== DEBUG: Attempting to load data ===")
        import pandas as pd
        print("✓ Pandas imported")

        if os.path.exists("data/TESTData.xlsx"):
            print("✓ Excel file exists")
            df = pd.read_excel("data/TESTData.xlsx")
            print(f"✓ Successfully loaded Excel with {len(df)} rows")
            data_status = f"Data loaded: {len(df)} rows"
        else:
            print("✗ Excel file not found")
            data_status = "Excel file not found"

    except Exception as e:
        print(f"✗ Error loading data: {e}")
        data_status = f"Data load failed: {str(e)}"

    @app.route("/data-status")
    def data_status_route():
        return {"status": data_status}

    print("=== DEBUG: create_app() completed successfully ===")
    return app

print("=== DEBUG: app/__init__.py loaded successfully ===")