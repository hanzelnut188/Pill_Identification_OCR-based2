# 初始化 OpenOCR 引擎
from openocr import OpenOCR
import logging

from app.utils.image_io import read_image_safely

logging.getLogger("openrec").setLevel(logging.ERROR)
ocr_engine = OpenOCR(backend='onnx', device='cpu')
# ocr_engine = OpenOCR(backend="onnx", det_model_path="models/openocr_det_model.onnx", rec_model_path="models/openocr_rec_model.onnx")


from app.utils.ocr_utils import recognize_with_openocr
from app.utils.shape_color_utils import (
    rotate_image_by_angle,
    enhance_contrast,
    desaturate_image,
    enhance_for_blur,
    extract_dominant_colors_by_ratio,
    detect_shape_from_image
)

# 套用字體（用 FontProperties）

from matplotlib.font_manager import FontProperties


zh_font = FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")


from pillow_heif import register_heif_opener

register_heif_opener()

from inference_sdk import InferenceHTTPClient

import cv2

from rembg import remove
from ultralytics import YOLO
det_model = YOLO("/path/to/best.pt")

CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key="SOlzinVqG2xuWsPUUGRp"
    # api_key="kylIYUWNLWHPy2RXUVOe"
)
MODEL_ID = "pill-detection-poc-i0b3g/1"


####

def generate_image_versions(base_img):
    v1 = enhance_contrast(base_img, 1.5, 1.5, -0.5)
    v2 = desaturate_image(v1)
    v3 = enhance_contrast(base_img, 5.5, 2.0, -1.0)
    v4 = desaturate_image(v3)
    v5 = enhance_for_blur(base_img)
    return [
        (base_img, "原圖"),
        (v1, "增強1"),
        (v2, "去飽和1"),
        (v3, "增強2"),
        (v4, "去飽和2"),
        (v5, "模糊優化")
    ]


def get_best_ocr_texts(image_versions, angles=[0, 45, 90, 135, 180, 225, 270, 315], ocr_engine=None):
    version_results = {}
    score_dict = {}
    for img_v, version_name in image_versions:
        for angle in angles:
            rotated = rotate_image_by_angle(img_v, angle)
            full_name = f"{version_name}_旋轉{angle}"
            texts, score = recognize_with_openocr(rotated, ocr_engine=ocr_engine, name=full_name, min_score=0.8)

            # print(f"🔍 {full_name} => {texts} (score={score:.3f})")#註解SSS
            version_results[full_name] = texts
            score_dict[full_name] = score

    score_combined = {
        k: sum(len(txt) for txt in version_results[k]) * score_dict[k]
        for k in version_results
    }
    best_name = max(score_combined, key=score_combined.get)
    return version_results[best_name], best_name, score_dict[best_name]


def get_bbox_from_rembg_alpha(img_path):
    input_img = cv2.imread(img_path)
    rembg_img = remove(input_img)

    if rembg_img.shape[2] == 4:
        alpha = rembg_img[:, :, 3]
        alpha = cv2.GaussianBlur(alpha, (5, 5), 0)
        _, mask = cv2.threshold(alpha, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
            return rembg_img, (x, y, w, h)  # ➜ return cropped image & bounding box
    return None, None


# === 模組化：從完整圖片與偵測框中擷取藥物區域 ===
# def extract_pill_region(img_path, detection_result, margin=10):
def extract_pill_region(input_img, detection_result, margin=10):
    #    input_img = read_image_safely(img_path)
    if input_img is None:
        # print(f"❌ extract_pill_region: 無法讀取圖片：{img_path}")#註解SSS
        return None, None

    try:
        h_img, w_img = input_img.shape[:2]
        cx, cy = detection_result["x"], detection_result["y"]
        bw, bh = detection_result["width"], detection_result["height"]

        x0 = max(0, int(cx - bw / 2) - margin)
        y0 = max(0, int(cy - bh / 2) - margin)
        x1 = min(w_img, int(cx + bw / 2) + margin)
        y1 = min(h_img, int(cy + bh / 2) + margin)

        cropped_original = input_img[y0:y1, x0:x1]

        try:
            cropped_removed = remove(cropped_original)
        except Exception as e:
            # print(f"❌ rembg 去背失敗：{e}")#註解SSS
            return cropped_original, None

        return cropped_original, cropped_removed

    except Exception as e:
        # print(f"❗ extract_pill_region 錯誤：{e}")#註解SSS
        return None, None


# def fallback_rembg_bounding(img_path):
# input_img = read_image_safely(img_path)
def fallback_rembg_bounding(input_img):
    if input_img is None:
        # print(f"❌ fallback: 無法讀取圖片：{img_path}")#註解SSS
        return None, None

    try:
        rembg_img = remove(input_img)
    except Exception as e:
        print(f"❌ rembg 去背失敗：{e}")
        return None, None

    if rembg_img is None or rembg_img.shape[2] < 4:
        print(f"⚠️ rembg 回傳結果異常")
        return None, None

    try:
        alpha = rembg_img[:, :, 3]
        alpha = cv2.GaussianBlur(alpha, (5, 5), 0)
        _, mask = cv2.threshold(alpha, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
            cropped = rembg_img[y:y + h, x:x + w]
            return input_img[y:y + h, x:x + w], cropped  # 返回原圖區塊、去背區塊
        else:
            print("⚠️ fallback 沒有偵測到輪廓")
    except Exception as e:
        print(f"❗ fallback rembg bounding 出錯：{e}")

    return None, None




from ultralytics import YOLO

# ✅ 全域載入本地 YOLO 模型（請提前初始化一次）
det_model = YOLO("/path/to/best.pt")  # 替換成你的 Roboflow 匯出 .pt 路徑


def process_image(img_path: str):
    """
    單張藥品圖片辨識流程（本地 YOLOv8 + OpenOCR + 顏色外型分析）
    """
    from PIL import Image
    import base64

    # === 讀取圖片 ===
    input_img = read_image_safely(img_path)
    if input_img is None:
        return {"error": "無法讀取圖片"}

    # === 使用本地 YOLO 模型進行推論 ===
    results = det_model(input_img)

    # === 處理 YOLO 偵測結果 ===
    preds = results[0].boxes
    if preds and len(preds) > 0:
        # 取最大框（信心分數最高的）
        boxes = preds.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
        best_idx = preds.conf.argmax().item()
        box = boxes[best_idx]
        x1, y1, x2, y2 = map(int, box)
        cropped_original = input_img[y1:y2, x1:x2]
        cropped_removed = remove(cropped_original)  # 仍使用 rembg 去背
    else:
        # YOLO 偵測不到 ➜ fallback
        cropped_original, cropped_removed = fallback_rembg_bounding(input_img)
        if cropped_removed is None:
            return {"error": "藥品擷取失敗"}

    # === 裁切圖轉 Base64 給前端展示 ===
    _, buffer = cv2.imencode(".jpg", cropped_original)
    cropped_base64 = base64.b64encode(buffer).decode("utf-8")
    cropped_base64 = f"data:image/jpeg;base64,{cropped_base64}"

    # === 外型、顏色分析 ===
    shape, _ = detect_shape_from_image(cropped_removed, cropped_original, expected_shape=None, debug=False)
    colors = extract_dominant_colors_by_ratio(cropped_removed, visualize=False)

    # === 多版本 OCR 辨識 ===
    image_versions = generate_image_versions(cropped_removed)
    best_texts, best_name, best_score = get_best_ocr_texts(image_versions, ocr_engine=ocr_engine)

    print("文字辨識：" + str(best_texts if best_texts else ["None"]))
    print("最佳版本：" + str(best_name))
    print("信心分數：" + str(round(best_score, 3)))
    print("顏色：" + str(colors))
    print("外型：" + str(shape))

    return {
        "文字辨識": best_texts if best_texts else ["None"],
        "最佳版本": best_name,
        "信心分數": round(best_score, 3),
        "顏色": colors,
        "外型": shape,
        "cropped_image": cropped_base64
    }

