import os
import traceback
from app.utils.data_loader import generate_color_shape_dicts
print("=== DEBUG: Starting app/__init__.py ===")
print(f"Current working directory: {os.getcwd()}")

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

    # 註冊路由
    register_routes(app, data_status)
    print("=== DEBUG: create_app() completed successfully ===")
    return app


def register_routes(app, data_status):
    """註冊路由"""

    @app.route("/")
    def index():
        print("=== DEBUG: Rendering index page ===")

        try:
            # 直接使用 render_template，應該現在能工作了
            result = render_template('index.html')
            print("✓ Template rendered successfully using render_template")
            return result

        except Exception as e:
            print(f"❌ render_template failed: {e}")
            print(f"Full traceback: {traceback.format_exc()}")

            # 回退到手動讀取
            print("Using manual file read as fallback...")
            try:
                template_path = os.path.join(app.template_folder, "index.html")
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print("✓ Manual file read successful")
                return content
            except Exception as fallback_error:
                print(f"❌ Manual fallback also failed: {fallback_error}")
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

        # 測試模板系統
        try:
            template_loader = app.jinja_env.loader
            template_source = template_loader.get_source(app.jinja_env, 'index.html')
            info["template_test"] = "✓ Flask can find index.html"
        except Exception as e:
            info["template_test"] = f"❌ Flask cannot find template: {str(e)}"

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

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fixed Template Debug Info</title>
            <style>
                body {{ font-family: monospace; margin: 20px; }}
                pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow: auto; }}
                .section {{ margin: 20px 0; }}
                h2 {{ color: #333; border-bottom: 2px solid #ccc; }}
                .error {{ background: #ffe6e6; border-left: 4px solid #ff4444; padding: 10px; }}
                .success {{ background: #e6ffe6; border-left: 4px solid #44ff44; padding: 10px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; }}
            </style>
        </head>
        <body>
            <h1>🔧 Fixed Template Path Debug</h1>
            <div class="section">
                <h2>Template System Test</h2>
                <div class="success" style="margin: 10px 0;">
                    <strong>Status:</strong> {info.get('template_test', 'Unknown')}
                </div>
                <pre>{json.dumps(info, indent=2, ensure_ascii=False)}</pre>
            </div>
            <div class="section">
                <h2>Quick Links</h2>
                <p><a href="/">← Try Home Again</a></p>
                <p><a href="/api/status">API Status</a></p>
                <p><a href="/static/index.css">Test CSS File</a></p>
                <p><a href="/static/index.js">Test JS File</a></p>
            </div>
        </body>
        </html>
        """

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
            background: #e6ffe6; padding: 1rem; border-radius: 8px;
            margin: 1rem 0; border-left: 4px solid #44ff44;
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
            <h3>✅ 模板路徑已修正</h3>
            <p>使用絕對路徑配置 Flask 模板</p>
            <p>如果看到這個頁面，說明 fallback 正在工作</p>
        </div>
        <div class="links">
            <a href="/debug">🔧 查看修正後的診斷</a>
            <a href="/api/status">📊 API 狀態</a>
        </div>
    </div>
</body>
</html>"""


print("=== DEBUG: app/__init__.py loaded successfully ===")
