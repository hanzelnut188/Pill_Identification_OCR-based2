# from flask import Flask, send_from_directory
# from app.route import index, upload_image, match_drug  # ✅ 確保有匯入 match_drug
# import os
#
# def create_app():
#     app = Flask(__name__)
#     app.config["UPLOAD_FOLDER"] = os.path.abspath("uploads")
#
#     # 註冊路由
#     app.add_url_rule("/", "/", index)
#     app.add_url_rule("/upload", "upload", upload_image, methods=["POST"])
#     app.add_url_rule("/match", "match", match_drug, methods=["POST"])  # ✅ 新增這行
#
#     @app.route("/uploads/<filename>", methods=["GET"])
#     def uploaded_file(filename):
#         file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
#         print("Trying to access file at:", file_path)
#         return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
#
#     return app
from flask import Flask, send_from_directory
from flask_cors import CORS

# from app.route import index, upload_image, match_drug
# import os
# import traceback
#
# import sys#可刪
# print("🔍 create_app 開始", file=sys.stderr, flush=True)#可刪
# def create_app():
#     print("🟡 [DEBUG] create_app() 開始初始化應用程式...")
#
#     try:
#         app = Flask(__name__)
#         CORS(app)
#         app.config["UPLOAD_FOLDER"] = os.path.abspath("uploads")
#         print(f"🟢 [DEBUG] 設定上傳路徑為：{app.config['UPLOAD_FOLDER']}")
#
#         # 註冊主要路由
#         app.add_url_rule("/", "/", index)
#         app.add_url_rule("/upload", "upload", upload_image, methods=["POST"])
#         app.add_url_rule("/match", "match", match_drug, methods=["POST"])
#         app.add_url_rule("/healthz", "healthz", lambda: ("OK", 200))
#
#         print("🟢 [DEBUG] 路由註冊成功")
#
#         # 靜態檔案提供（上傳圖片存取）
#         @app.route("/uploads/<filename>", methods=["GET"])
#         def uploaded_file(filename):
#             file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
#             print("📄 嘗試存取檔案：", file_path)
#             return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
#
#         # ➕ 健康檢查
#         @app.route("/healthz", methods=["GET"])
#         def health_check():
#             print("🟢 [DEBUG] 健康檢查成功！")
#             return "OK", 200
#
#         print("✅ [DEBUG] create_app() 成功結束，Flask app 準備好了！")
#         return app
#
#     except Exception as e:
#         print("❌ [ERROR] create_app() 發生例外錯誤！")
#         traceback.print_exc()  # 印出完整錯誤堆疊
#         raise e  # 重新拋出錯誤，讓 Render 能記錄 logs

# app/__init__.py
# from flask import Flask
# from flask_cors import CORS
# from pathlib import Path
#
# def create_app():
#     app = Flask(
#         __name__,
#         # 你的 index.html 現在在專案根目錄 → 用 "."；
#         # 若你改放到 templates/index.html，這裡就寫 "templates"
#         template_folder=".",
#         static_folder=str(Path("static"))  # 若沒有 static 可留著不影響
#     )
#     CORS(app)
#
#     # ✅ 只註冊 blueprint，不要再 add_url_rule
#     from app.route import bp
#     app.register_blueprint(bp)
#
#     # ✅ 健康檢查（只保留一個）
#     @app.get("/healthz")
#     def healthz():
#         return "OK", 200
#
#     return app

# app/__init__.py
from flask import Flask, send_from_directory
from flask_cors import CORS
import os
import sys
import traceback

print("🔍 create_app 開始", file=sys.stderr, flush=True)

def create_app():
    print("🟡 [DEBUG] create_app() 初始化中...")

    try:
        app = Flask(__name__, static_folder="static", template_folder="templates")
        CORS(app)
        app.config["UPLOAD_FOLDER"] = os.path.abspath("uploads")
        print(f"🟢 [DEBUG] UPLOAD_FOLDER = {app.config['UPLOAD_FOLDER']}")

        # ✅ 用 Blueprint 來掛路由（見下一節的 route.py）
        from app.route import bp
        app.register_blueprint(bp)

        # ✅ 健康檢查：只保留 *一個*
        @app.get("/healthz")
        def health_check():
            return "OK", 200

        # ✅ 若你有上傳檔案要對外提供
        @app.get("/uploads/<filename>")
        def uploaded_file(filename):
            return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

        print("✅ [DEBUG] create_app() 完成")
        return app

    except Exception as e:
        print("❌ [ERROR] create_app() 例外")
        traceback.print_exc()
        raise
