import os

# 在任何 heavy import 之前限制執行緒
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

try:
    from flask import Flask, jsonify, render_template

except Exception as e:
    print(f"Error importing Flask: {e}")

try:
    from flask_cors import CORS

except Exception as e:
    print(f"Error importing Flask-CORS: {e}")

def create_app():
    base_dir = os.getcwd()
    template_folder = os.path.join(base_dir, "app", "templates")
    static_folder = os.path.join(base_dir, "app", "static")

    # 檢查路徑是否存在
    if os.path.exists(template_folder):

        try:
            template_files = os.listdir(template_folder)

            index_path = os.path.join(template_folder, "index.html")


        except Exception as e:
            print(f"  Error listing template files: {e}")
    else:

        # 嘗試其他可能的路徑
        alternative_paths = [
            os.path.join(base_dir, "templates"),
            "app/templates",
            "templates"
        ]
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                template_folder = alt_path
                print(f"Found alternative template folder: {alt_path}")
                break

    if os.path.exists(static_folder):

        try:
            static_files = os.listdir(static_folder)

        except Exception as e:
            print(f"  Error listing static files: {e}")
    else:

        # 嘗試其他可能的路徑
        alternative_static_paths = [
            os.path.join(base_dir, "static"),
            "app/static",
            "static"
        ]
        for alt_path in alternative_static_paths:
            if os.path.exists(alt_path):
                static_folder = alt_path
                print(f"Found alternative static folder: {alt_path}")
                break

    try:
        # 創建 Flask app
        app = Flask(
            __name__,
            template_folder=template_folder,
            static_folder=static_folder,
            static_url_path='/static'
        )

        # # 驗證 Flask 能找到模板
        # try:
        #     template_loader = app.jinja_env.loader
        #
        #     # 測試模板載入
        #     template_source = template_loader.get_source(app.jinja_env, 'index.html')
        #
        #
        # except Exception as template_test_error:
        #     print(f"Flask cannot find template: {template_test_error}")

    except Exception as e:
        print(f"Error creating Flask app: {e}")
        raise

    try:
        CORS(app)

    except Exception as e:
        print(f"Error configuring CORS: {e}")
    from app.utils.data_loader import generate_color_shape_dicts
    import pandas as pd
    # 數據載入
    try:

        df = pd.read_excel("data/TESTData.xlsx")

        data_status = f"Data loaded: {len(df)} rows"
        app.df = df
        # 動態生成分類字典
        color_dict, shape_dict, invalid_colors = generate_color_shape_dicts(df)
        app.color_dict = color_dict
        app.shape_dict = shape_dict
        ###以下可刪
        # === Color statistics (per designed buckets) ===
        COLOR_BUCKETS = ["白色","黃色","黑色","棕色","紅色","透明","皮膚色","橘色","綠色","藍色","紫色","粉紅色","灰色"]

        # Count UNIQUE drugs mapped to each color (e.g., unique '用量排序' ids).
        color_counts = {c: 0 for c in COLOR_BUCKETS}
        try:
            for c in COLOR_BUCKETS:
                vals = color_dict.get(c, [])
                # Use a set to avoid double-counting the same drug if it appears multiple times
                color_counts[c] = len(set(vals)) if hasattr(vals, "__iter__") else int(vals)
            # expose on app for other routes / debug
            app.color_counts = color_counts

            # Console summary (always includes zeros)
            summary = " | ".join(f"{c}:{int(color_counts[c])}" for c in COLOR_BUCKETS)
            print("📊 顏色→藥物數量統計（Excel/字典基準）", summary)

        except Exception as e:
            print(f"⚠️ Color counting failed: {e}")
            app.color_counts = {c: 0 for c in COLOR_BUCKETS}
        ###以上可刪

    except Exception as e:
        print(f"✗ Error loading data: {e}")
        data_status = f"Data load failed: {str(e)}"
        app.df = None

    # 註冊路由
    from app.route import register_routes
    register_routes(app, data_status)
    # ⑤ 預熱模型（使用「lazy 單例」的 getter，不會重複載）
    from app.utils.pill_detection import get_det_model, get_ocr_engine
    try:
        get_det_model()
        get_ocr_engine()
        print("🔥 Warmed up YOLO & OpenOCR")
    except Exception as e:
        print(f"⚠️ Warmup failed: {e}")

    return app

