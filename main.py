# from flask import Flask
# from app import create_app
#
# app = create_app()
#
#
# if __name__ == "__main__":
#     # app.run(debug=True, port=8001, host="0.0.0.0")
#     app.run(debug=False, use_reloader=False, port=8001, host="0.0.0.0")
#


import os
from app import create_app
import sys#可刪
print("🚀 啟動主程式 main.py", file=sys.stderr, flush=True)#可刪
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render 會提供 PORT
    print(f"🟢 正在啟動 Flask on port {port}")
    app.run(host="0.0.0.0", port=port)

