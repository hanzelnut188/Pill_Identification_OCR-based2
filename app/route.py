import imghdr
import io
import os
from io import BytesIO
import pandas as pd
from flask import request, jsonify, render_template
import base64
import time
import shutil
from app.utils.matcher import match_ocr_to_front_back_by_permuted_ocr
import tempfile
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()  # ✅ 全域註冊 HEIC 支援
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


def register_routes(app, data_status):
    """註冊所有路由到 Flask app"""

    # 從 app 取得數據，如果沒有則創建空的 DataFrame
    df = getattr(app, 'df', pd.DataFrame())

    color_dict = getattr(app, 'color_dict', {})
    shape_dict = getattr(app, 'shape_dict', {})

    @app.route("/")
    def index():
        try:
            # print("=== DEBUG: Rendering index page ===")
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

    @app.route("/upload", methods=["POST"])
    def upload_image():
        # print("🟡 [UPLOAD] 收到 POST")

        try:
            t0 = time.perf_counter()
            data = request.get_json()
            if not data or "image" not in data:
                return jsonify({"ok": False, "error": "缺少 image 欄位"}), 400

            b64_data = data["image"]
            # print(f"🟡 [UPLOAD] JSON 解析完成，有 image 欄位: {bool(b64_data)}")

            # 嘗試剝除 base64 header
            if b64_data.startswith("data:"):
                b64_data = b64_data.split(",")[1]

            image_bytes = base64.b64decode(b64_data)
            # print(f"🟡 [UPLOAD] base64 解碼成功，長度: {len(image_bytes)} bytes")

            # 嘗試用 Pillow 開啟圖片
            image = None
            try:
                image = Image.open(io.BytesIO(image_bytes))
                image.verify()  # 驗證格式合法
                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")  # 再打開一次取得像素
                # print("🟢 [UPLOAD] Pillow 成功辨識圖片格式")
            except Exception as e:
                print(f"❌ [UPLOAD] Pillow 無法辨識圖片格式: {e}")
                # 嘗試用 imghdr 判斷副檔名
                fmt = imghdr.what(None, image_bytes)
                print(f"❌ [UPLOAD] imghdr 檢測結果: {fmt}")
                return jsonify({"ok": False, "error": "不支援的圖片格式"}), 400

            # 儲存成臨時檔案
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            image.save(temp_file.name)
            temp_path = temp_file.name
            temp_file.close()
            # print(f"🟢 [UPLOAD] 寫入臨時檔 {temp_path} ({os.path.getsize(temp_path)} bytes)")

            # 呼叫核心辨識邏輯
            from app.utils.pill_detection import process_image
            result = process_image(temp_path) or {}
            t2 = time.perf_counter()
            print(
                f"🟢 [UPLOAD] 推論成功：文字={result['文字辨識']}最佳版本={result['最佳版本']}信心分數={result['信心分數']} 顏色={result['顏色']} 外型={result['外型']}")
            print(f"🟢 [UPLOAD] 完成，總耗時 {t2 - t0:.2f}s")
            return jsonify({"ok": True, "result": result}), 200

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"🔴 [UPLOAD] 失敗：{e}")
            return jsonify({
                "ok": False,
                "error": f"{e}",
                "result": {"文字辨識": [], "顏色": [], "外型": "", "cropped_image": ""}
            }), 200

        finally:
            try:
                shutil.rmtree("./temp_imgs", ignore_errors=True)
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                print(f"⚠️ [UPLOAD] 臨時檔清理失敗：{e}")

    @app.route("/api/status")
    def api_status():
        return jsonify({
            "status": "running",
            "version": "1.0.0",
            "data_loaded": hasattr(app, 'df') and app.df is not None,
            "data_rows": len(app.df) if hasattr(app, 'df') and app.df is not None else 0,
            "endpoints": ["/", "/healthz", "/debug", "/api/status"]
        })

    # print("✓ Routes registered successfully")

    @app.route("/match", methods=["POST"])
    def match_drug():
        """藥物比對路由"""
        # print("🟡 [MATCH] 收到請求")
        try:
            data = request.get_json()
            # print(
            #     f"🟡 [MATCH] 請求內容：texts={data.get('texts')}, colors={data.get('colors')}, shape={data.get('shape')}")
            texts = data.get("texts", [])
            colors = data.get("colors", [])
            shape = data.get("shape", "")

            if df.empty:
                print("🔴 [MATCH] 錯誤：資料庫未載入")
                return jsonify({"error": "資料庫未載入"}), 500
            # print("🟡 [MATCH] 開始篩選候選藥物")
            # 尋找候選藥物
            candidates = set()

            # 根據顏色篩選
            for color in colors:
                print(f"    - 顏色篩選：{color} ➜ {len(color_dict.get(color, []))} 筆")
                candidates |= set(color_dict.get(color, []))

            # 根據形狀篩選
            if shape:
                before_shape = len(candidates)  # 之後可刪
                candidates &= set(shape_dict.get(shape, []))
                print(f"    - 外型交集：{shape} ➜ 從 {before_shape} 筆減為 {len(candidates)} 筆")
            if not candidates:
                print("🔴 [MATCH] 沒有符合的候選藥物")
                return jsonify({"error": "找不到符合顏色與外型的藥品"}), 404

            print("[DEBUG] STEP 3 - 顏色候選數量", len(candidates))

            # 篩選數據
            df_sub = df[df["用量排序"].isin(candidates)] if "用量排序" in df.columns else df
            print(f"🟡 [MATCH] 經過篩選剩下 {len(df_sub)} 筆藥物")
            # 如果沒有文字或文字為空
            if not texts or texts == ["None"]:
                print("🟡 [MATCH] 無文字情境，搜尋純顏色/外型比對結果")
                results = []
                for _, row in df_sub.iterrows():
                    if str(row.get("文字", "")).strip() not in ["F:NONE|B:NONE", "F:None|B:None"]:
                        continue

                    # 尋找藥物圖片
                    picture_path = os.path.join("data/pictures", f"{row.get('批價碼', '')}.jpg")
                    picture_base64 = ""
                    if os.path.exists(picture_path):
                        try:
                            with open(picture_path, "rb") as f:
                                picture_base64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
                        except Exception as e:
                            print(f"Error reading picture {picture_path}: {e}")

                    results.append({
                        "name": safe_get(row, "學名"),
                        "symptoms": safe_get(row, "適應症"),
                        "precautions": safe_get(row, "用藥指示與警語"),
                        "side_effects": safe_get(row, "副作用"),
                        "drug_image": picture_base64
                    })

                return jsonify({"candidates": results})
            # print("[DEBUG] STEP 4 - Shape", shape)
            # 進行 OCR 比對 - 這個函數需要你實作或匯入
            try:
                match_result = match_ocr_to_front_back_by_permuted_ocr(texts, df_sub)
                # 暫時的替代方案
                print(f"🟡 [MATCH] 有文字，要進行比對 ➜ {texts}")
                # match_result = {"front": {"row": df_sub.iloc[0] if not df_sub.empty else None}}
            except NameError:
                return jsonify({"error": "OCR 比對功能未實作"}), 500

            front_row = match_result.get("front", {}).get("row")
            back_row = match_result.get("back", {}).get("row")

            row = None
            if isinstance(front_row, pd.Series) and not front_row.empty:
                row = front_row
            elif isinstance(back_row, pd.Series) and not back_row.empty:
                row = back_row

            if isinstance(row, pd.Series):
                row = row.to_dict()

            if isinstance(row, dict):
                # 尋找藥物圖片
                picture_path = os.path.join("data/pictures", f"{row.get('批價碼', '')}.jpg")
                picture_base64 = ""
                if os.path.exists(picture_path):
                    try:
                        with open(picture_path, "rb") as f:
                            picture_base64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
                    except Exception as e:
                        print(f"Error reading picture {picture_path}: {e}")
                print("🟢 [MATCH] 比對完成，準備回傳")
                return jsonify({
                    "name": safe_get(row, "學名"),
                    "symptoms": safe_get(row, "適應症"),
                    "precautions": safe_get(row, "用藥指示與警語"),
                    "side_effects": safe_get(row, "副作用"),
                    "drug_image": picture_base64
                })

            return jsonify({"error": "無法比對藥品"}), 404

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": "Internal server error", "details": str(e)}), 500
