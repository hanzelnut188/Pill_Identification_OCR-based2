#
#
# import os
# import sys
#
# print("=== DEBUG: Starting app/__init__.py ===")
# print(f"Current working directory: {os.getcwd()}")
#
# try:
#     from flask import Flask, jsonify, render_template
#     print("✓ Flask and render_template imported successfully")
# except Exception as e:
#     print(f"✗ Error importing Flask: {e}")
#
# try:
#     from flask_cors import CORS
#     print("✓ Flask-CORS imported successfully")
# except Exception as e:
#     print(f"✗ Error importing Flask-CORS: {e}")
#
# def create_app():
#     print("=== DEBUG: create_app() called ===")
#
#     # 檢查模板和靜態文件路徑
#     print("=== DEBUG: Checking paths ===")
#
#     # 獲取當前文件的絕對路徑
#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     print(f"Current __init__.py directory: {current_dir}")
#
#     # 設置絕對路徑
#     template_folder = os.path.join(current_dir, "templates")
#     static_folder = os.path.join(current_dir, "static")
#
#     print(f"Template folder (absolute): {template_folder}")
#     print(f"Static folder (absolute): {static_folder}")
#     print(f"Template folder exists: {os.path.exists(template_folder)}")
#     print(f"Static folder exists: {os.path.exists(static_folder)}")
#
#     # 列出文件
#     try:
#         if os.path.exists(template_folder):
#             template_files = os.listdir(template_folder)
#             print(f"Template files: {template_files}")
#         if os.path.exists(static_folder):
#             static_files = os.listdir(static_folder)
#             print(f"Static files: {static_files}")
#     except Exception as e:
#         print(f"Error listing files: {e}")
#
#     try:
#         # 使用絕對路徑創建 Flask 應用
#         app = Flask(
#             __name__,
#             template_folder=template_folder,
#             static_folder=static_folder,
#             static_url_path='/static'
#         )
#         print(f"✓ Flask app created")
#         print(f"  Template folder: {app.template_folder}")
#         print(f"  Static folder: {app.static_folder}")
#         print(f"  Static URL path: {app.static_url_path}")
#     except Exception as e:
#         print(f"✗ Error creating Flask app: {e}")
#         raise
#
#     try:
#         CORS(app)
#         print("✓ CORS configured")
#     except Exception as e:
#         print(f"✗ Error configuring CORS: {e}")
#
#     # 測試靜態文件路由
#     @app.route("/test-static")
#     def test_static():
#         try:
#             from flask import url_for
#             css_url = url_for('static', filename='index.css')
#             js_url = url_for('static', filename='index.js')
#             return f"CSS URL: {css_url}<br>JS URL: {js_url}"
#         except Exception as e:
#             return f"Static URL generation failed: {str(e)}"
#
#     # 測試模板路由（帶錯誤處理）
#     @app.route("/")
#     def index():
#         try:
#             print("=== DEBUG: Attempting to render template ===")
#
#             # 檢查模板文件存在
#             template_path = os.path.join(app.template_folder, "index.html")
#             print(f"Template path: {template_path}")
#             print(f"Template exists: {os.path.exists(template_path)}")
#
#             # 檢查靜態文件存在
#             css_path = os.path.join(app.static_folder, "index.css")
#             js_path = os.path.join(app.static_folder, "index.js")
#             print(f"CSS path: {css_path}, exists: {os.path.exists(css_path)}")
#             print(f"JS path: {js_path}, exists: {os.path.exists(js_path)}")
#
#             if not os.path.exists(template_path):
#                 return f"Template not found at: {template_path}"
#
#             # 嘗試讀取模板內容以確認可訪問性
#             try:
#                 with open(template_path, 'r', encoding='utf-8') as f:
#                     template_content = f.read()
#                 print(f"✓ Template content read successfully, length: {len(template_content)}")
#             except Exception as read_error:
#                 print(f"✗ Cannot read template file: {read_error}")
#                 return f"Cannot read template: {str(read_error)}"
#
#             return render_template("index.html")
#
#         except Exception as e:
#             print(f"✗ Template rendering error: {e}")
#             import traceback
#             traceback.print_exc()
#             return f"Template rendering failed: {str(e)}"
#
#     # 簡化版首頁（不依賴靜態文件）
#     @app.route("/simple-home")
#     def simple_home():
#         return """
#         <!DOCTYPE html>
#         <html lang="zh-Hant">
#         <head>
#             <meta charset="utf-8">
#             <title>Pill Detection - Simple</title>
#             <meta name="viewport" content="width=device-width, initial-scale=1.0">
#         </head>
#         <body>
#             <div style="text-align: center; padding: 20px;">
#                 <h1>Medical Detection APP</h1>
#                 <p>簡化版本 - 不依賴外部CSS/JS</p>
#                 <p>服務正常運行中...</p>
#             </div>
#         </body>
#         </html>
#         """
#
#     @app.route("/healthz")
#     def healthz():
#         return "ok", 200
#
#     # 數據載入
#     try:
#         import pandas as pd
#         df = pd.read_excel("data/TESTData.xlsx")
#         print(f"✓ Successfully loaded Excel with {len(df)} rows")
#         data_status = f"Data loaded: {len(df)} rows"
#     except Exception as e:
#         print(f"✗ Error loading data: {e}")
#         data_status = f"Data load failed: {str(e)}"
#
#     @app.route("/debug")
#     def debug():
#         info = {
#             "cwd": os.getcwd(),
#             "current_dir": current_dir,
#             "template_folder": app.template_folder,
#             "template_path_exists": os.path.exists(app.template_folder),
#             "static_folder": app.static_folder,
#             "static_path_exists": os.path.exists(app.static_folder),
#             "data_status": data_status,
#             "template_folder_absolute": os.path.abspath(app.template_folder),
#             "static_folder_absolute": os.path.abspath(app.static_folder)
#         }
#
#         try:
#             info["files_in_template_folder"] = os.listdir(app.template_folder)
#         except Exception as e:
#             info["files_in_template_folder"] = [f"Error: {str(e)}"]
#
#         try:
#             info["files_in_static_folder"] = os.listdir(app.static_folder)
#         except Exception as e:
#             info["files_in_static_folder"] = [f"Error: {str(e)}"]
#
#         return info
#
#     # 新增：測試 Jinja2 環境
#     @app.route("/test-jinja")
#     def test_jinja():
#         try:
#             # 測試 Jinja2 loader
#             loader = app.jinja_env.loader
#             template_list = loader.list_templates()
#             return {
#                 "jinja_loader_type": str(type(loader)),
#                 "template_searchpath": getattr(loader, 'searchpath', 'N/A'),
#                 "available_templates": template_list
#             }
#         except Exception as e:
#             return {"error": str(e)}
#
#     print("=== DEBUG: create_app() completed successfully ===")
#     return app
#
# print("=== DEBUG: app/__init__.py loaded successfully ===")

import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

def create_app():
    # 直接使用確定的路徑，不需要複雜判斷
    current_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(current_dir, "templates"),
        static_folder=os.path.join(current_dir, "static"),
        static_url_path='/static'
    )

    CORS(app)

    # 主頁
    @app.route("/")
    def index():
        return render_template("index.html")

    # 健康檢查
    @app.route("/healthz")
    def healthz():
        return "ok", 200

    # 載入你的實際路由
    from app.route import register_routes
    register_routes(app)

    # 錯誤處理 - 確保 API 永遠返回 JSON
    @app.errorhandler(404)
    def not_found(error):
        if request.path in ['/upload', '/match'] or request.path.startswith('/api/'):
            return jsonify({"error": "API 端點不存在"}), 404
        return render_template("index.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        if request.path in ['/upload', '/match'] or request.path.startswith('/api/'):
            return jsonify({"error": "伺服器內部錯誤"}), 500
        return render_template("index.html"), 500

    return app