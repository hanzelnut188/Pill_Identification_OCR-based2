import os
import cv2
import numpy as np
from flask import Flask, request, jsonify
import easyocr
from werkzeug.utils import secure_filename
from flask import render_template
import torch
import base64
from pill_detection import process_image
import tempfile
import subprocess
from flask_cors import CORS

UPLOAD_FOLDER = "uploads/"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
reader = easyocr.Reader(["en"])  # 使用英文模型

# 禁用 cuDNN
torch.backends.cudnn.enabled = False

app = Flask(__name__)
CORS(app)


# 設置上傳文件夾
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# 定義首頁路由
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_image():
    # 確保請求是 JSON 格式
    if not request.is_json:
        return jsonify({"error": "Invalid content type. JSON expected."}), 415

    # 取得 JSON 資料
    data = request.get_json()
    image_data = data.get("image")

    if not image_data:
        return jsonify({"error": "No image data found"}), 400

    try:
        # 解碼 base64 圖片
        if "," not in image_data:
            return jsonify({"error": "Invalid image data format"}), 400

        image_binary = base64.b64decode(image_data.split(",")[1])

        # 創建臨時檔案儲存圖片
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(image_binary)
            temp_file_path = temp_file.name

        # 調用 process_image 函式並捕捉輸出
        result = process_image(temp_file_path)
        print(result)

        return jsonify({"message": "Image processed successfully", "result": result})

    except Exception as e:
        print(f"Error processing image: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=8001)
