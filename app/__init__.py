import os

# ✅ 在任何 heavy import 之前限制執行緒（放第一行！）
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

from app.route import register_routes
from app.utils.data_loader import generate_color_shape_dicts
from app.utils.logging_utils import log_mem

print("=== DEBUG: Starting app/__init__.py ===")
print(f"Current working directory: {os.getcwd()}")

######################
# ============= 預先載入所有重型庫 =============
print("🟡 [STARTUP] 開始載入深度學習庫...")

try:
    # 預先載入 torch (最重的)
    print("🟡 [STARTUP] 載入 torch...")
    import torch

    print("🟢 [STARTUP] torch 載入完成")
    log_mem("after torch import")
    # 預先載入 ultralytics (YOLO)
    print("🟡 [STARTUP] 載入 ultralytics...")
    import ultralytics

    print("🟢 [STARTUP] ultralytics 載入完成")
    log_mem("after ultralytics import")
    # 預先載入 process_image
    print("🟡 [STARTUP] 載入 process_image...")
    from app.utils.pill_detection import process_image

    print("🟢 [STARTUP] process_image 載入完成")
    log_mem("after process_image import")

    print("🟢 [STARTUP] 所有深度學習庫載入完成!")

except Exception as e:
    print(f"🔴 [STARTUP] 載入庫時發生錯誤: {e}")
    import traceback

    traceback.print_exc()

######################


try:
    from flask import Flask, jsonify, render_template

    print("✓ Flask and render_template imported successfully")
except Exception as e:
    print(f"✗ Error importing Flask: {e}")

try:
    from flask_cors import CORS

    print("✓ Flask-CORS imported successfully")
except Exception as e:
    print(f"✗ Error importing Flask-CORS: {e}")


def create_app():
    print("=== DEBUG: create_app() called ===")

    # 🔥 修正路徑問題 - 使用絕對路徑
    base_dir = os.getcwd()
    template_folder = os.path.join(base_dir, "app", "templates")
    static_folder = os.path.join(base_dir, "app", "static")

    print(f"Base directory: {base_dir}")
    print(f"Using template folder: {template_folder}")
    print(f"Using static folder: {static_folder}")

    # 檢查路徑是否存在
    if os.path.exists(template_folder):
        print(f"✓ Template folder exists: {template_folder}")
        try:
            template_files = os.listdir(template_folder)
            print(f"  Template files: {template_files}")

            # 檢查 index.html 具體路徑
            index_path = os.path.join(template_folder, "index.html")
            print(f"  Index.html path: {index_path}")
            print(f"  Index.html exists: {os.path.exists(index_path)}")

        except Exception as e:
            print(f"  Error listing template files: {e}")
    else:
        print(f"✗ Template folder not found: {template_folder}")
        # 嘗試其他可能的路徑
        alternative_paths = [
            os.path.join(base_dir, "templates"),
            "app/templates",
            "templates"
        ]
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                template_folder = alt_path
                print(f"✓ Found alternative template folder: {alt_path}")
                break

    if os.path.exists(static_folder):
        print(f"✓ Static folder exists: {static_folder}")
        try:
            static_files = os.listdir(static_folder)
            print(f"  Static files: {static_files}")
        except Exception as e:
            print(f"  Error listing static files: {e}")
    else:
        print(f"✗ Static folder not found: {static_folder}")
        # 嘗試其他可能的路徑
        alternative_static_paths = [
            os.path.join(base_dir, "static"),
            "app/static",
            "static"
        ]
        for alt_path in alternative_static_paths:
            if os.path.exists(alt_path):
                static_folder = alt_path
                print(f"✓ Found alternative static folder: {alt_path}")
                break

    try:
        # 🔥 創建 Flask app - 使用絕對路徑
        app = Flask(
            __name__,
            template_folder=template_folder,
            static_folder=static_folder,
            static_url_path='/static'
        )
        print(f"✓ Flask app created")
        print(f"  Template folder (actual): {app.template_folder}")
        print(f"  Static folder (actual): {app.static_folder}")
        print(f"  Static URL path: {app.static_url_path}")
        log_mem("after Flask app created")
        # 🔥 驗證 Flask 能找到模板
        try:
            template_loader = app.jinja_env.loader
            print(f"  Jinja2 loader: {template_loader}")

            # 測試模板載入
            template_source = template_loader.get_source(app.jinja_env, 'index.html')
            print("✓ Flask can find index.html template")

        except Exception as template_test_error:
            print(f"❌ Flask cannot find template: {template_test_error}")

    except Exception as e:
        print(f"✗ Error creating Flask app: {e}")
        raise

    try:
        CORS(app)
        print("✓ CORS configured")
    except Exception as e:
        print(f"✗ Error configuring CORS: {e}")

    # 數據載入
    try:
        import pandas as pd
        df = pd.read_excel("data/TESTData.xlsx")
        print(f"✓ Successfully loaded Excel with {len(df)} rows")
        data_status = f"Data loaded: {len(df)} rows"
        app.df = df
        # ✅ 動態生成分類字典
        color_dict, shape_dict, invalid_colors = generate_color_shape_dicts(df)
        app.color_dict = color_dict
        app.shape_dict = shape_dict

    except Exception as e:
        print(f"✗ Error loading data: {e}")
        data_status = f"Data load failed: {str(e)}"
        app.df = None
    log_mem("after data load")
    # 註冊路由

    register_routes(app, data_status)
    print("=== DEBUG: create_app() completed successfully ===")
    log_mem("after register_routes")
    # app/__init__.py（create_app() 的最後）
    from app.utils.pill_detection import get_det_model
    print("🟡 [WARMUP] 載入 YOLO 權重…")
    det =get_det_model()
    print("🟢 [WARMUP] YOLO 準備完成")
    log_mem("after get_det_model")
    # 可選暖機一次（小張 dummy 圖）
    try:
        import numpy as np, cv2
        dummy = np.zeros((320, 320, 3), dtype=np.uint8)
        print("🟡 [WARMUP] 做一次 dummy 推論…")
        det.predict(source=dummy, imgsz=320, conf=0.25, iou=0.7, device="cpu", verbose=False)
        print("🟢 [WARMUP] 推論暖機完成")
        log_mem("after warmup predict")
    except Exception as e:
        print(f"⚠️ [WARMUP] dummy 推論失敗（可忽略）：{e}")

    print("=== DEBUG: create_app() completed successfully ===")
    return app
