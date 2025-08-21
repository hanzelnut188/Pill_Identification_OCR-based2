# import os
# from app import create_app
#
# app = create_app()
#
# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 10000))
#     app.run(host="0.0.0.0", port=port, debug=False)
# 步驟 1：恢復應用工廠模式
# main.py
import os

try:
    from app import create_app

    app = create_app()
    print("✓ Successfully imported and created app")
except Exception as e:
    print("✗ Fallback activated due to error:")
    import traceback

    traceback.print_exc()

    from flask import Flask

    app = Flask(__name__)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
