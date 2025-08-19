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
from flask import Flask, jsonify, render_template
from flask_cors import CORS
import os

def create_app():
    app = Flask(
        __name__,
        template_folder="templates",       # 修正：相對於當前 app/ 目錄
        static_folder="static"            # 修正：相對於當前 app/ 目錄
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

    # 除錯：檢查模板資料夾
    template_dir = app.template_folder
    static_dir = app.static_folder
    print(f"Template folder: {template_dir}")
    print(f"Static folder: {static_dir}")

    # 檢查檔案是否存在
    try:
        import os
        files_in_templates = os.listdir(template_dir) if os.path.exists(template_dir) else []
        files_in_static = os.listdir(static_dir) if os.path.exists(static_dir) else []
        print(f"Files in templates: {files_in_templates}")
        print(f"Files in static: {files_in_static}")
    except Exception as e:
        print(f"Error checking directories: {e}")

    @app.route("/")
    def index():
        try:
            # 先檢查模板是否存在
            template_path = os.path.join(app.template_folder, "index.html")
            if not os.path.exists(template_path):
                return f"Template not found at: {template_path}<br>Status: {data_status}"

            return render_template("index.html")
        except Exception as e:
            return f"HTML template rendering failed: {e}<br>Status: {data_status}"

    @app.route("/healthz")
    def healthz():
        return "ok", 200

    @app.route("/data-status")
    def data_status_route():
        return {"status": data_status}

    # 導入並註冊其他路由（放在最後）
    try:
        from app.route import register_routes
        register_routes(app)
        print("✓ Additional routes registered")
    except Exception as e:
        print(f"✗ Error registering additional routes: {e}")

    return app