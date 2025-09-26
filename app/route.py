import imghdr
import io
import os
from io import BytesIO

import cv2
import numpy as np
import pandas as pd
from flask import request, jsonify, render_template
import base64
import time
import shutil
from app.utils.matcher import match_top_n_ocr_to_front_back
import tempfile
from PIL import Image
from pillow_heif import register_heif_opener
from app.utils.matcher import match_ocr_to_front_back_by_permuted_ocr, lcs_score

register_heif_opener()  # ✅ 全域註冊 HEIC 支援
# 假設這些是從其他模組匯入的變數和函數
# 你需要根據實際情況調整匯入
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

from app.utils.pill_detection import process_image


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
            "color_counts": getattr(app, 'color_counts', {}),
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

    @app.route("/api/color-stats")
    def api_color_stats():
        buckets = ["白色", "透明", "黑色", "棕色", "紅色", "橘色", "皮膚色", "黃色", "綠色", "藍色", "紫色", "粉紅色",
                   "灰色"]
        counts = getattr(app, "color_counts", {})
        result = {c: int(counts.get(c, 0)) for c in buckets}
        return jsonify({"counts": result, "total_colors": len(buckets)})

    @app.route("/upload", methods=["POST"])
    def upload_image():
        temp_path = None
        try:
            t0 = time.perf_counter()
            # === 1. 解析 JSON 並確認欄位 ===
            data = request.get_json()
            if not data or "image" not in data:
                return jsonify({"ok": False, "error": "缺少 image 欄位"}), 400
            b64_data = data["image"]
            # t1 = time.perf_counter()
            # print(f"📥 base64 JSON 接收：{(t1 - t0) * 1000:.1f} ms")

            # === 2. 嘗試剝除 base64 header 並解碼 ===
            if b64_data.startswith("data:"):
                b64_data = b64_data.split(",")[1]
            image_bytes = base64.b64decode(b64_data)
            # t2 = time.perf_counter()
            # print(f"🧪 base64 解碼成功：{(t2 - t1) * 1000:.1f} ms")

            # === 3. 嘗試用 Pillow 解析圖片格式 ===
            # === 3. 嘗試用 Pillow 解析圖片格式 ===
            image = None
            try:
                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                # （已移除 image.verify() 以避免重複解碼/重開）
            except Exception as e:

                print(f"❌ [UPLOAD] Pillow 無法辨識圖片格式: {e}")
                fmt = imghdr.what(None, image_bytes)
                print(f"❌ [UPLOAD] imghdr 檢測結果: {fmt}")
                return jsonify({"ok": False, "error": "不支援的圖片格式"}), 400

            # t3 = time.perf_counter()
            # print(f"🖼️ Pillow 解碼驗證：{(t3 - t2) * 1000:.1f} ms")

            # === 4. 暫存為圖片檔案（JPEG）===
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            temp_path = temp_file.name
            image.save(temp_path, format="JPEG")
            temp_file.close()
            # t4 = time.perf_counter()
            # print(f"🧠 圖片儲存至暫存檔：{(t4 - t3) * 1000:.1f} ms")

            # === 5. 呼叫核心辨識邏輯（傳圖片路徑）===
            result = process_image(temp_path) or {}

            t5 = time.perf_counter()

            # print(f"🔁 呼叫 process_image()：{(t5 - t4) * 1000:.1f} ms")
            if isinstance(result, dict) and "error" in result:
                print(f"🔴 [UPLOAD] pipeline error: {result['error']}")
                return jsonify({"ok": False, "error": result.get("error", "unknown")}), 422

            # === 6. 回傳 + 結束 ===
            print(
                f"🟢 [UPLOAD] 推論成功：文字={result['文字辨識']}最佳版本={result['最佳版本']}信心分數={result['信心分數']} 顏色={result['顏色']} 外型={result['外型']}")
            print(f"⏱️ [UPLOAD] 完成，總耗時 {(t5 - t0):.2f} s")

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
    MIN_TOP1_ACCEPT = 0.30  # Top-1 分數低於此值 → 請重拍
    HARD_THRESHOLD = 0.80  # 正常門檻

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
            # --- 顏色交集 ---
            color_sets = []
            for color in colors:
                ids = set(color_dict.get(color, []))
                print(f"    - 顏色篩選：{color} ➜ {len(ids)} 筆")
                color_sets.append(ids)

            if color_sets:
                candidates = set.intersection(*color_sets)
                print(f"    ✅ 顏色交集後 ➜ {len(candidates)} 筆")
            else:
                candidates = set()

            # --- 外型交集 ---
            if shape:
                before_shape = len(candidates)
                shape_ids = set(shape_dict.get(shape, []))
                candidates &= shape_ids
                print(f"    ✅ 外型交集：{shape} ➜ 從 {before_shape} 筆減為 {len(candidates)} 筆")

            # === 無候選處理 ===
            if not candidates:
                print("🔴 [MATCH] 沒有符合的候選藥物")
                return jsonify({"error": "找不到符合顏色與外型的藥品"}), 404

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
            # === 有文字：先用正常門檻比對 ===
            print(f"🟡 [MATCH] 有文字，要進行比對 ➜ {texts}")
            # match_result = match_ocr_to_front_back_by_permuted_ocr(texts, df_sub, threshold=HARD_THRESHOLD)

            top_matches = match_top_n_ocr_to_front_back(texts, df_sub, threshold=HARD_THRESHOLD, top_n=4)

            # === 門檻沒過：降門檻取 Top-1 回傳（low_confidence） ===
            if not top_matches:
                print("🟠 [MATCH] 門檻未通過，啟用 Top-1 回傳（low_confidence）")
                fallback = match_ocr_to_front_back_by_permuted_ocr(texts, df_sub, threshold=0.0)

                # 從 front/back 取分數最高者
                best, best_side = None, None
                if fallback:
                    for side in ("front", "back"):
                        if side in fallback and fallback[side].get("row") is not None:
                            if (best is None) or (fallback[side]["score"] > best["score"]):
                                best = fallback[side];
                                best_side = side

                # 若有 Top-1 且分數尚可 → 以低信心單一結果回傳
                if best and best["score"] >= MIN_TOP1_ACCEPT:
                    row = best["row"]
                    if isinstance(row, pd.Series):
                        row = row.to_dict()

                    picture_path = os.path.join("data/pictures", f"{row.get('批價碼', '')}.jpg")
                    picture_base64 = ""
                    if os.path.exists(picture_path):
                        with open(picture_path, "rb") as f:
                            picture_base64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"

                    return jsonify({
                        "name": safe_get(row, "學名"),
                        "symptoms": safe_get(row, "適應症"),
                        "precautions": safe_get(row, "用藥指示與警語"),
                        "side_effects": safe_get(row, "副作用"),
                        "drug_image": picture_base64,
                        "score": round(best["score"], 3),
                        "side": best_side,
                        "low_confidence": True
                    }), 200

                # Top-1 也太低 → 請重拍
                return jsonify({
                    "error": "影像過於模糊或光線不足，建議重拍（請讓藥面填滿畫面、避免反光、對焦清晰）。",
                    "need_retake": True
                }), 422
            # === 正常門檻有結果：走原本路徑 ===
            # === 正常門檻有結果：組成多筆 candidates 回傳 ===
            results = []
            for match in top_matches:
                row = match["row"]
                if isinstance(row, pd.Series):
                    row = row.to_dict()

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
                    "drug_image": picture_base64,
                    "score": round(match["score"], 3),
                    "match": match["match"],
                    "side": match["side"]
                })

            print(f"🟢 [MATCH] Top-{len(results)} 比對完成，準備回傳")
            return jsonify({"candidates": results}), 200

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": "Internal server error", "details": str(e)}), 500
