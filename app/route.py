# import pandas as pd
# from flask import request, jsonify, render_template
#
# import base64
# import tempfile
# import os
# import openpyxl
#
# from app.utils.matcher import match_ocr_to_front_back_by_permuted_ocr
# from app.utils.pill_detection import process_image
# from io import BytesIO
# from pillow_heif import register_heif_opener
# from PIL import Image, UnidentifiedImageError
# import shutil
#
# register_heif_opener()
# UPLOAD_FOLDER = "uploads/"
# ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
#
# df = pd.read_excel("data/TESTData.xlsx")
# color_dict = {
#     '白色': [1, 3, 4, 5, 6, 7, 8, 9, 11, 13, 15, 17, 18, 19, 23, 24, 25, 28, 29, 30, 35, 36, 38, 39, 40, 43, 45, 46, 47,
#              51, 52, 53, 56, 59, 61, 62, 64, 65, 66, 68, 70, 78, 82, 83, 84, 89, 90, 95, 96, 97, 98, 99, 101, 102, 103,
#              104, 105, 106, 107, 108, 111, 113, 114, 117, 119, 121, 124, 125, 126, 130, 131, 132, 134, 135, 136, 137,
#              139, 140, 141, 146, 148, 150, 151, 156, 163, 169, 170, 174, 176, 178, 180, 182, 183, 187, 189, 195, 199,
#              201, 205, 206, 207, 210, 211, 212, 213, 214, 217, 218, 221, 222, 223, 224, 225, 226, 229, 230, 231, 234,
#              239, 241, 245, 250, 251, 252, 257, 259, 262, 263, 266, 274, 275, 279, 280, 281, 282, 284, 285, 286, 289,
#              293, 296, 302, 303, 305, 306, 307, 308, 309, 310, 313, 315, 319, 320, 321, 325, 326, 327, 331, 332, 333,
#              334, 337, 338, 344, 345, 346, 349, 350, 351, 352, 355, 356, 357, 360, 362, 363, 365, 370, 373, 376, 377,
#              380, 383, 384, 385, 387, 388, 389, 391, 393, 394, 401], '透明': [33], '黑色': [14, 94],
#     '棕色': [42, 50, 60, 152, 193, 208, 215, 247, 329, 398],
#     '紅色': [12, 16, 25, 27, 32, 44, 55, 58, 126, 145, 153, 168, 170, 216, 227, 254, 261, 266, 294, 297, 299, 311, 327],
#     '橘色': [8, 12, 34, 48, 54, 72, 73, 74, 81, 87, 110, 118, 129, 145, 158, 178, 190, 191, 197, 202, 204, 233, 255,
#              273, 278, 314, 316, 317, 322, 330, 341, 343, 372, 378, 379, 381, 392, 395, 396, 400], '皮膚色': [157],
#     '黃色': [2, 14, 22, 37, 41, 49, 58, 67, 69, 71, 76, 77, 79, 85, 88, 91, 93, 109, 112, 116, 120, 147, 153, 154, 155,
#              159, 160, 162, 165, 166, 167, 177, 181, 184, 185, 186, 188, 209, 219, 228, 232, 235, 236, 237, 240, 243,
#              244, 246, 248, 249, 253, 258, 261, 264, 267, 268, 269, 271, 277, 278, 290, 298, 301, 304, 311, 312, 335,
#              339, 347, 348, 351, 359, 361, 364, 366, 367, 368, 369, 382, 386, 390, 402],
#     '綠色': [10, 57, 100, 117, 123, 133, 142, 192, 195, 196, 200, 256, 257, 287, 336, 353, 399],
#     '藍色': [63, 84, 112, 123, 138, 144, 164, 173, 177, 179, 198, 203, 208, 220, 272, 276, 284, 291, 323, 334, 369, 372,
#              374], '紫色': [75, 143, 149, 227, 340],
#     '粉紅色': [20, 21, 26, 31, 40, 80, 86, 92, 115, 122, 127, 128, 161, 171, 172, 175, 194, 234, 238, 242, 260, 265,
#                283, 288, 292, 295, 300, 318, 323, 324, 328, 342, 354, 358, 371, 374, 375, 397],
#     '灰色': [122, 242, 289, 356]}
# shape_dict = {
#     '圓形': [1, 2, 4, 5, 7, 9, 10, 13, 15, 16, 18, 20, 21, 22, 23, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 39, 40, 41,
#              42, 43, 45, 47, 48, 49, 50, 51, 52, 54, 55, 56, 60, 62, 63, 64, 65, 66, 68, 69, 71, 73, 75, 76, 77, 78, 80,
#              81, 82, 83, 86, 89, 90, 92, 95, 97, 98, 99, 100, 101, 103, 104, 106, 107, 108, 109, 110, 114, 116, 121,
#              124, 125, 127, 128, 129, 130, 131, 135, 136, 140, 142, 143, 146, 147, 148, 149, 150, 151, 152, 156, 157,
#              161, 162, 163, 164, 167, 168, 169, 173, 176, 180, 182, 183, 184, 185, 189, 190, 192, 194, 196, 197, 199,
#              200, 201, 204, 205, 206, 209, 210, 211, 213, 214, 215, 216, 218, 219, 221, 223, 224, 226, 229, 230, 231,
#              233, 235, 236, 238, 239, 241, 243, 245, 246, 249, 250, 251, 253, 255, 259, 260, 262, 267, 268, 269, 271,
#              273, 280, 281, 283, 286, 288, 290, 292, 293, 296, 297, 298, 299, 302, 304, 305, 306, 307, 308, 310, 313,
#              317, 321, 322, 324, 325, 326, 328, 331, 332, 335, 336, 337, 338, 339, 343, 346, 347, 349, 350, 353, 354,
#              357, 359, 360, 361, 362, 364, 368, 375, 376, 380, 382, 383, 385, 388, 389, 390, 391, 393, 394, 398, 402],
#     '橢圓形': [3, 6, 8, 11, 12, 14, 24, 27, 37, 38, 44, 46, 53, 57, 58, 59, 61, 67, 70, 72, 74, 79, 84, 85, 87, 88, 91,
#                93, 94, 96, 102, 105, 111, 112, 113, 117, 118, 119, 122, 123, 126, 132, 134, 137, 138, 139, 141, 145,
#                153, 154, 155, 158, 159, 160, 165, 166, 170, 171, 172, 174, 175, 177, 178, 179, 181, 186, 187, 193, 195,
#                202, 203, 207, 208, 212, 217, 220, 222, 225, 227, 228, 232, 234, 237, 240, 242, 247, 248, 252, 254, 256,
#                257, 258, 261, 263, 264, 265, 266, 272, 274, 275, 276, 277, 278, 282, 284, 287, 289, 291, 294, 300, 301,
#                303, 309, 311, 312, 314, 315, 316, 318, 319, 320, 323, 327, 329, 330, 333, 334, 341, 342, 344, 351, 352,
#                355, 356, 358, 367, 369, 370, 372, 373, 374, 377, 378, 379, 381, 386, 387, 392, 395, 396, 397, 399, 400],
#     '其他': [17, 19, 25, 115, 120, 133, 144, 188, 191, 198, 244, 270, 279, 285, 295, 340, 345, 348, 363, 365, 366, 371,
#              384, 401]}
#
#
# def allowed_file(filename):
#     return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
#
#
# def safe_get(row, key):
#     val = row.get(key, "")
#     if pd.isna(val):
#         return ""
#     return str(val).strip()
#
#
# # ✅ 改成函數，傳入 app
# def register_routes(app):
#     @app.route("/")
#     def index():
#         return render_template("index.html")
#
#     @app.route("/upload", methods=["POST"])
#     def upload_image():
#         if not request.is_json:
#             return jsonify({"error": "Invalid content type. JSON expected."}), 415
#
#         data = request.get_json()
#         image_data = data.get("image")
#
#         if not image_data or "," not in image_data:
#             return jsonify({"error": "Invalid or missing image data"}), 400
#
#         try:
#             image_binary = base64.b64decode(image_data.split(",")[1])
#             try:
#                 image = Image.open(BytesIO(image_binary)).convert("RGB")
#             except UnidentifiedImageError:
#                 return jsonify({"error": "無法辨識圖片格式"}), 400
#
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", mode="wb") as temp_file:
#                 image.save(temp_file, format="JPEG")
#                 temp_file.flush()
#                 os.fsync(temp_file.fileno())
#                 temp_file_path = temp_file.name
#
#             result = process_image(temp_file_path)
#             shutil.rmtree("./temp_imgs", ignore_errors=True)
#             os.remove(temp_file_path)
#
#             return jsonify({"message": "Image processed successfully", "result": result})
#
#         except Exception as e:
#             print(f"Error processing image: {e}")
#             return jsonify({"error": "Internal server error", "details": str(e)}), 500
#
#     @app.route("/match", methods=["POST"])
#     def match_drug():
#         try:
#             data = request.get_json()
#             texts = data.get("texts", [])
#             colors = data.get("colors", [])
#             shape = data.get("shape", "")
#
#             candidates = set()
#             for color in colors:
#                 candidates |= set(color_dict.get(color, []))
#
#             if shape:
#                 candidates &= set(shape_dict.get(shape, []))
#
#             if not candidates:
#                 return jsonify({"error": "找不到符合顏色與外型的藥品"}), 404
#
#             df_sub = df[df["用量排序"].isin(candidates)]
#
#             if not texts or texts == ["None"]:
#                 results = []
#                 for _, row in df_sub.iterrows():
#                     if str(row.get("文字", "")).strip() not in ["F:NONE|B:NONE", "F:None|B:None"]:
#                         continue
#                     picture_path = os.path.join("data/pictures", f"{row.get('批價碼', '')}.jpg")
#                     picture_base64 = ""
#                     if os.path.exists(picture_path):
#                         with open(picture_path, "rb") as f:
#                             picture_base64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
#                     results.append({
#                         "name": safe_get(row, "學名"),
#                         "symptoms": safe_get(row, "適應症"),
#                         "precautions": safe_get(row, "用藥指示與警語"),
#                         "side_effects": safe_get(row, "副作用"),
#                         "drug_image": picture_base64
#                     })
#                 return jsonify({"candidates": results})
#
#             match_result = match_ocr_to_front_back_by_permuted_ocr(texts, df_sub)
#             row = match_result.get("front", {}).get("row") or match_result.get("back", {}).get("row")
#             if isinstance(row, pd.Series):
#                 row = row.to_dict()
#
#             if isinstance(row, dict):
#                 picture_path = os.path.join("data/pictures", f"{row.get('批價碼', '')}.jpg")
#                 picture_base64 = ""
#                 if os.path.exists(picture_path):
#                     with open(picture_path, "rb") as f:
#                         picture_base64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
#                 return jsonify({
#                     "name": safe_get(row, "學名"),
#                     "symptoms": safe_get(row, "適應症"),
#                     "precautions": safe_get(row, "用藥指示與警語"),
#                     "side_effects": safe_get(row, "副作用"),
#                     "drug_image": picture_base64
#                 })
#
#             return jsonify({"error": "無法比對藥品"}), 404
#
#         except Exception as e:
#             import traceback
#             traceback.print_exc()
#             return jsonify({"error": "Internal server error", "details": str(e)}), 500
#
#     @app.route("/healthz")
#     def healthz():
#         return "ok", 200

import os
import base64
import tempfile
import shutil
import pandas as pd
from flask import request, jsonify, render_template
from PIL import Image, UnidentifiedImageError
from io import BytesIO

from app.utils.pill_detection import process_image

# 假設這些是從其他模組匯入的變數和函數
# 你需要根據實際情況調整匯入
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


# 可以跑在RENDER 但功能無用
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_get(row, key):
    val = row.get(key, "")
    if pd.isna(val):
        return ""
    return str(val).strip()


def get_fallback_html():
    """簡化的回退 HTML"""
    return """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="utf-8">
    <title>Medical Detection APP</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: 'Segoe UI', system-ui, sans-serif; 
            margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
        }
        .container { 
            background: white; padding: 2rem; border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); text-align: center;
            max-width: 500px; width: 100%;
        }
        h1 { color: #333; margin-bottom: 1rem; }
        .status { 
            background: #e8f5e8; padding: 1rem; border-radius: 8px;
            margin: 1rem 0; border-left: 4px solid #4caf50;
        }
        .links a { 
            display: inline-block; margin: 0.5rem; padding: 0.5rem 1rem;
            background: #667eea; color: white; text-decoration: none;
            border-radius: 5px; transition: background 0.3s;
        }
        .links a:hover { background: #5a67d8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 Medical Detection APP</h1>
        <div class="status">
            <h3>✅ 服務正常運行中</h3>
            <p>後端 API 已啟動並可接收請求</p>
            <p>使用簡化模板顯示</p>
        </div>
        <div class="links">
            <a href="/debug">🔍 查看除錯資訊</a>
            <a href="/api/status">📊 API 狀態</a>
        </div>
        <div style="margin-top: 2rem; font-size: 0.9rem; color: #666;">
            <p>如果您是開發者，請檢查模板文件是否正確配置</p>
        </div>
    </div>
</body>
</html>"""


print("=== DEBUG: app/__init__.py loaded successfully ===")


def register_routes(app, data_status):
    """註冊所有路由到 Flask app"""

    # 從 app 取得數據，如果沒有則創建空的 DataFrame
    df = getattr(app, 'df', pd.DataFrame())

    # 你需要根據實際情況初始化這些變數
    # 這裡假設它們是從數據中建立的索引
    color_dict = getattr(app, 'color_dict', {})
    shape_dict = getattr(app, 'shape_dict', {})
    @app.route("/")
    def index():
        try:
            print("=== DEBUG: Rendering index page ===")
            # 使用 Flask 的 render_template 而不是手動讀取
            return render_template("index.html")
        except Exception as e:
            print(f"Error rendering template: {e}")
            return get_fallback_html()

    @app.route("/healthz")
    def healthz():
        return "ok", 200

    @app.route("/debug")
    def debug():
        import json

        info = {
            "status": "running",
            "cwd": os.getcwd(),
            "template_folder": app.template_folder,
            "template_exists": os.path.exists(app.template_folder),
            "static_folder": app.static_folder,
            "static_exists": os.path.exists(app.static_folder),
            "data_status": data_status,
            "flask_info": {
                "template_folder": app.template_folder,
                "static_folder": app.static_folder,
                "static_url_path": app.static_url_path
            }
        }

        # 列出文件
        try:
            if os.path.exists(app.template_folder):
                info["template_files"] = os.listdir(app.template_folder)
            else:
                info["template_files"] = ["Template folder not found"]
        except Exception as e:
            info["template_files"] = [f"Error: {str(e)}"]

        try:
            if os.path.exists(app.static_folder):
                info["static_files"] = os.listdir(app.static_folder)
            else:
                info["static_files"] = ["Static folder not found"]
        except Exception as e:
            info["static_files"] = [f"Error: {str(e)}"]

        # 檢查具體文件路徑
        info["file_paths"] = {
            "index.html": os.path.join(app.template_folder, "index.html"),
            "index.css": os.path.join(app.static_folder, "index.css"),
            "index.js": os.path.join(app.static_folder, "index.js"),
            "config.js": os.path.join(app.static_folder, "config.js")
        }

        info["file_exists"] = {
            path_name: os.path.exists(path) for path_name, path in info["file_paths"].items()
        }
        info["color_dict_keys"] = list(color_dict.keys())
        info["shape_dict_keys"] = list(shape_dict.keys())
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Debug Info</title>
            <style>
                body {{ font-family: monospace; margin: 20px; }}
                pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow: auto; }}
                .section {{ margin: 20px 0; }}
                h2 {{ color: #333; border-bottom: 2px solid #ccc; }}
            </style>
        </head>
        <body>
            <h1>🔍 Debug Information</h1>
            <div class="section">
                <h2>System Status</h2>
                <pre>{json.dumps(info, indent=2, ensure_ascii=False)}</pre>
            </div>
            <div class="section">
                <h2>Quick Links</h2>
                <p><a href="/">← Back to Home</a></p>
                <p><a href="/api/status">API Status</a></p>
                <p><a href="/static/index.css">Test CSS File</a></p>
                <p><a href="/static/index.js">Test JS File</a></p>
            </div>
        </body>
        </html>
        """
    #
    # @app.route("/upload", methods=["POST"])
    # def upload_image():
    #     """圖片上傳和處理路由"""
    #     if not request.is_json:
    #         return jsonify({"error": "Invalid content type. JSON expected."}), 415
    #
    #     data = request.get_json()
    #     image_data = data.get("image")
    #
    #     if not image_data or "," not in image_data:
    #         return jsonify({"error": "Invalid or missing image data"}), 400
    #
    #     try:
    #         # 解碼 base64 圖片
    #         image_binary = base64.b64decode(image_data.split(",")[1])
    #
    #         try:
    #             image = Image.open(BytesIO(image_binary)).convert("RGB")
    #         except UnidentifiedImageError:
    #             return jsonify({"error": "無法辨識圖片格式"}), 400
    #
    #         # 創建臨時文件
    #         with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", mode="wb") as temp_file:
    #             image.save(temp_file, format="JPEG")
    #             temp_file.flush()
    #             os.fsync(temp_file.fileno())
    #             temp_file_path = temp_file.name
    #
    #         # 圖像處理
    #         try:
    #             print(f"[DEBUG] Calling process_image() with {temp_file_path}")
    #             result = process_image(temp_file_path)
    #             print(f"[DEBUG] process_image result: {result}")
    #         except Exception as e:
    #             print(f"[ERROR] process_image failed: {e}")
    #             import traceback
    #             traceback.print_exc()
    #             return jsonify({"error": "圖片處理失敗", "details": str(e)}), 500
    #
    #         # 清理臨時檔案
    #         try:
    #             shutil.rmtree("./temp_imgs", ignore_errors=True)
    #             os.remove(temp_file_path)
    #         except Exception as e:
    #             print(f"Error cleaning up temp files: {e}")
    #
    #         # 回傳結果
    #         return jsonify({"message": "Image processed successfully", "result": result})
    #
    #     except Exception as e:
    #         print(f"Error processing image: {e}")
    #         import traceback
    #         traceback.print_exc()
    #         return jsonify({"error": "Internal server error", "details": str(e)}), 500

    @app.route("/api/status")
    def api_status():
        return jsonify({
            "status": "running",
            "version": "1.0.0",
            "data_loaded": hasattr(app, 'df') and app.df is not None,
            "data_rows": len(app.df) if hasattr(app, 'df') and app.df is not None else 0,
            "endpoints": ["/", "/healthz", "/debug", "/api/status"]
        })

    print("✓ Routes registered successfully")
    #
    # @app.route("/match", methods=["POST"])
    # def match_drug():
    #     """藥物比對路由"""
    #     try:
    #         data = request.get_json()
    #         texts = data.get("texts", [])
    #         colors = data.get("colors", [])
    #         shape = data.get("shape", "")
    #
    #         if df.empty:
    #             return jsonify({"error": "資料庫未載入"}), 500
    #
    #         # 尋找候選藥物
    #         candidates = set()
    #
    #         # 根據顏色篩選
    #         for color in colors:
    #             candidates |= set(color_dict.get(color, []))
    #
    #         # 根據形狀篩選
    #         if shape:
    #             candidates &= set(shape_dict.get(shape, []))
    #
    #         if not candidates:
    #             return jsonify({"error": "找不到符合顏色與外型的藥品"}), 404
    #
    #         # 篩選數據
    #         df_sub = df[df["用量排序"].isin(candidates)] if "用量排序" in df.columns else df
    #
    #         # 如果沒有文字或文字為空
    #         if not texts or texts == ["None"]:
    #             results = []
    #             for _, row in df_sub.iterrows():
    #                 if str(row.get("文字", "")).strip() not in ["F:NONE|B:NONE", "F:None|B:None"]:
    #                     continue
    #
    #                 # 尋找藥物圖片
    #                 picture_path = os.path.join("data/pictures", f"{row.get('批價碼', '')}.jpg")
    #                 picture_base64 = ""
    #                 if os.path.exists(picture_path):
    #                     try:
    #                         with open(picture_path, "rb") as f:
    #                             picture_base64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    #                     except Exception as e:
    #                         print(f"Error reading picture {picture_path}: {e}")
    #
    #                 results.append({
    #                     "name": safe_get(row, "學名"),
    #                     "symptoms": safe_get(row, "適應症"),
    #                     "precautions": safe_get(row, "用藥指示與警語"),
    #                     "side_effects": safe_get(row, "副作用"),
    #                     "drug_image": picture_base64
    #                 })
    #
    #             return jsonify({"candidates": results})
    #
    #         # 進行 OCR 比對 - 這個函數需要你實作或匯入
    #         try:
    #             # match_result = match_ocr_to_front_back_by_permuted_ocr(texts, df_sub)
    #             # 暫時的替代方案
    #             match_result = {"front": {"row": df_sub.iloc[0] if not df_sub.empty else None}}
    #         except NameError:
    #             return jsonify({"error": "OCR 比對功能未實作"}), 500
    #
    #         row = match_result.get("front", {}).get("row") or match_result.get("back", {}).get("row")
    #
    #         if isinstance(row, pd.Series):
    #             row = row.to_dict()
    #
    #         if isinstance(row, dict):
    #             # 尋找藥物圖片
    #             picture_path = os.path.join("data/pictures", f"{row.get('批價碼', '')}.jpg")
    #             picture_base64 = ""
    #             if os.path.exists(picture_path):
    #                 try:
    #                     with open(picture_path, "rb") as f:
    #                         picture_base64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    #                 except Exception as e:
    #                     print(f"Error reading picture {picture_path}: {e}")
    #
    #             return jsonify({
    #                 "name": safe_get(row, "學名"),
    #                 "symptoms": safe_get(row, "適應症"),
    #                 "precautions": safe_get(row, "用藥指示與警語"),
    #                 "side_effects": safe_get(row, "副作用"),
    #                 "drug_image": picture_base64
    #             })
    #
    #         return jsonify({"error": "無法比對藥品"}), 404
    #
    #     except Exception as e:
    #         import traceback
    #         traceback.print_exc()
    #         return jsonify({"error": "Internal server error", "details": str(e)}), 500
