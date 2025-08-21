# import os
# import sys
#
# from app.route import register_routes
# #路徑沒問題
# print("=== DEBUG: Starting app/__init__.py ===")
# print(f"Current working directory: {os.getcwd()}")
#
# try:
#     from flask import Flask, jsonify, render_template
#
#     print("✓ Flask and render_template imported successfully")
# except Exception as e:
#     print(f"✗ Error importing Flask: {e}")
#
# try:
#     from flask_cors import CORS
#
#     print("✓ Flask-CORS imported successfully")
# except Exception as e:
#     print(f"✗ Error importing Flask-CORS: {e}")
#
#
# def create_app():
#     print("=== DEBUG: create_app() called ===")
#
#     # 簡化路徑設定 - 根據DEBUG_INFO，我們知道正確路徑
#     template_folder = "app/templates"
#     # static_folder = "app/static"
#     static_folder = os.path.join(os.path.dirname(__file__), "static")
#
#
#     print(f"Using template folder: {template_folder}")
#     print(f"Using static folder: {static_folder}")
#
#     # 檢查路徑是否存在
#     if os.path.exists(template_folder):
#         print(f"✓ Template folder exists: {template_folder}")
#         try:
#             template_files = os.listdir(template_folder)
#             print(f"  Template files: {template_files}")
#         except Exception as e:
#             print(f"  Error listing template files: {e}")
#     else:
#         print(f"✗ Template folder not found: {template_folder}")
#
#     if os.path.exists(static_folder):
#         print(f"✓ Static folder exists: {static_folder}")
#         try:
#             static_files = os.listdir(static_folder)
#             print(f"  Static files: {static_files}")
#         except Exception as e:
#             print(f"  Error listing static files: {e}")
#     else:
#         print(f"✗ Static folder not found: {static_folder}")
#
#     try:
#         # 創建 Flask app - 使用正確的路徑設定
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
#
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
#     # 數據載入
#     try:
#         import pandas as pd
#         df = pd.read_excel("data/TESTData.xlsx")
#         print(f"✓ Successfully loaded Excel with {len(df)} rows")
#         data_status = f"Data loaded: {len(df)} rows"
#         app.df = df
#     except Exception as e:
#         print(f"✗ Error loading data: {e}")
#         data_status = f"Data load failed: {str(e)}"
#         app.df = None
#
#     # 註冊路由
#     register_routes(app, data_status)
#     print("=== DEBUG: create_app() completed successfully ===")
#     return app


import os
import sys
import traceback

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

    # 簡化路徑設定
    template_folder = "app/templates"
    static_folder = "app/static"

    print(f"Using template folder: {template_folder}")
    print(f"Using static folder: {static_folder}")

    # 檢查路徑是否存在
    if os.path.exists(template_folder):
        print(f"✓ Template folder exists: {template_folder}")
        try:
            template_files = os.listdir(template_folder)
            print(f"  Template files: {template_files}")
        except Exception as e:
            print(f"  Error listing template files: {e}")
    else:
        print(f"✗ Template folder not found: {template_folder}")

    if os.path.exists(static_folder):
        print(f"✓ Static folder exists: {static_folder}")
        try:
            static_files = os.listdir(static_folder)
            print(f"  Static files: {static_files}")
        except Exception as e:
            print(f"  Error listing static files: {e}")
    else:
        print(f"✗ Static folder not found: {static_folder}")

    try:
        # 創建 Flask app
        app = Flask(
            __name__,
            template_folder=template_folder,
            static_folder=static_folder,
            static_url_path='/static'
        )
        print(f"✓ Flask app created")
        print(f"  Template folder: {app.template_folder}")
        print(f"  Static folder: {app.static_folder}")
        print(f"  Static URL path: {app.static_url_path}")

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

        # 🔥 詳細診斷模板問題
        template_path = os.path.join(app.template_folder, "index.html")
        print(f"Template path: {template_path}")
        print(f"Template exists: {os.path.exists(template_path)}")

        # 檢查文件內容
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Template file size: {len(content)} characters")
                print(f"First 100 chars: {repr(content[:100])}")

                # 檢查可能的問題
                if content.strip() == '':
                    print("❌ Template file is empty!")
                    return get_fallback_html()

                if '\x00' in content:
                    print("❌ Template contains null bytes!")
                    return get_fallback_html()

                # 檢查編碼問題
                try:
                    content.encode('utf-8')
                    print("✓ Template encoding is valid UTF-8")
                except UnicodeEncodeError as e:
                    print(f"❌ Template encoding error: {e}")
                    return get_fallback_html()

        except Exception as e:
            print(f"❌ Error reading template file: {e}")
            print(f"Full traceback: {traceback.format_exc()}")
            return get_fallback_html()

        # 🔥 嘗試不同的渲染方法
        print("Attempting to render template...")

        # 方法 1: 直接 render_template
        try:
            print("Method 1: Direct render_template")
            result = render_template('index.html')
            print("✓ Method 1 successful")
            return result
        except Exception as e:
            print(f"❌ Method 1 failed: {e}")
            print(f"Full traceback: {traceback.format_exc()}")

        # 方法 2: 使用 app_context
        try:
            print("Method 2: With app_context")
            with app.app_context():
                result = render_template('index.html')
                print("✓ Method 2 successful")
                return result
        except Exception as e:
            print(f"❌ Method 2 failed: {e}")
            print(f"Full traceback: {traceback.format_exc()}")

        # 方法 3: 手動讀取文件
        try:
            print("Method 3: Manual file read")
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print("✓ Method 3 successful - returning raw HTML")
            return content
        except Exception as e:
            print(f"❌ Method 3 failed: {e}")
            print(f"Full traceback: {traceback.format_exc()}")

        # 所有方法都失敗，返回 fallback
        print("❌ All rendering methods failed, using fallback")
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

        # 🔥 詳細模板診斷
        try:
            template_path = os.path.join(app.template_folder, "index.html")
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            info["template_diagnostic"] = {
                "size": len(template_content),
                "is_empty": template_content.strip() == '',
                "has_null_bytes": '\x00' in template_content,
                "first_100_chars": repr(template_content[:100]),
                "last_100_chars": repr(template_content[-100:]),
                "line_count": len(template_content.split('\n')),
                "encoding_test": "OK"
            }

            # 測試編碼
            try:
                template_content.encode('utf-8')
                info["template_diagnostic"]["encoding_test"] = "UTF-8 OK"
            except UnicodeEncodeError as e:
                info["template_diagnostic"]["encoding_test"] = f"Encoding Error: {str(e)}"

        except Exception as e:
            info["template_diagnostic"] = {"error": str(e)}

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Detailed Debug Info</title>
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
            <h1>🔍 Detailed Debug Information</h1>
            <div class="section">
                <h2>Template Diagnostic Results</h2>
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
            background: #ffe6e6; padding: 1rem; border-radius: 8px;
            margin: 1rem 0; border-left: 4px solid #ff4444;
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
            <h3>⚠️ 模板診斷模式</h3>
            <p>正在詳細檢查模板文件問題</p>
            <p>使用備用頁面顯示</p>
        </div>
        <div class="links">
            <a href="/debug">🔍 查看詳細診斷結果</a>
            <a href="/api/status">📊 API 狀態</a>
        </div>
    </div>
</body>
</html>"""


print("=== DEBUG: app/__init__.py loaded successfully ===")
