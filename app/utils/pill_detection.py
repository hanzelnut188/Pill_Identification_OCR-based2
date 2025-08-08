# 初始化 OpenOCR 引擎
import base64

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



import cv2

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


from rembg import remove

from ultralytics import YOLO
import torch

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
_det_model = None


def get_det_model():
    global _det_model
    if _det_model is None:
        m = YOLO("models/best.pt")
        try:
            m.fuse()
        except Exception:
            pass
        _det_model = m
    return _det_model


def _pick_crop_from_boxes(input_img, boxes):
    """從 YOLO boxes 選最佳框並做 padding、回傳裁切圖"""
    xyxy = boxes.xyxy.cpu().numpy()  # [N,4]
    conf = boxes.conf.squeeze().cpu().numpy()  # [N,] 或 scalar
    conf = conf if conf.ndim else conf[None]  # 保證是一維
    areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
    score = conf * (areas / (areas.max() + 1e-6))  # 面積加權，避免挑到超小但高 conf 的框
    best_idx = score.argmax()
    x1, y1, x2, y2 = map(int, xyxy[best_idx])
    # 以框大小做 padding（8%）
    bw, bh = x2 - x1, y2 - y1
    pad = int(0.08 * max(bw, bh))
    h, w = input_img.shape[:2]
    x1 = max(0, x1 - pad);
    y1 = max(0, y1 - pad)
    x2 = min(w - 1, x2 + pad);
    y2 = min(h - 1, y2 + pad)
    cropped_original = input_img[y1:y2, x1:x2]
    cropped_removed = remove(cropped_original)
    return cropped_original, cropped_removed


def process_image(img_path: str):

    det_model = get_det_model()
    """
    單張藥品圖片辨識流程（本地 YOLOv8 + OpenOCR + 顏色外型分析）
    """
    # === 讀取圖片 ===
    input_img = read_image_safely(img_path)
    if input_img is None:
        return {"error": "無法讀取圖片"}

    # === YOLO 偵測（先正常閾值，失敗再降閾值）===
    res = det_model.predict(source=input_img, imgsz=640, conf=0.25, iou=0.7,
                            device=DEVICE, verbose=False)[0]
    boxes = res.boxes

    if boxes is not None and boxes.xyxy.shape[0] > 0:
        cropped_original, cropped_removed = _pick_crop_from_boxes(input_img, boxes)
    else:
        res_lo = det_model.predict(source=input_img, imgsz=640, conf=0.10, iou=0.7,
                                   device=DEVICE, verbose=False)[0]
        boxes_lo = res_lo.boxes
        if boxes_lo is not None and boxes_lo.xyxy.shape[0] > 0:
            cropped_original, cropped_removed = _pick_crop_from_boxes(input_img, boxes_lo)
        else:
            # 最後才走 rembg fallback
            cropped_original, cropped_removed = fallback_rembg_bounding(input_img)
            if cropped_removed is None:
                return {"error": "藥品擷取失敗"}

    # === 裁切圖轉 Base64（給前端顯示） ===
    ok, buffer = cv2.imencode(".jpg", cropped_original)
    cropped_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}" if ok else None

    # === 外型、顏色分析 ===
    shape, _ = detect_shape_from_image(cropped_removed, cropped_original, expected_shape=None, debug=False)
    colors = extract_dominant_colors_by_ratio(cropped_removed, visualize=False)

    # === 多版本 OCR 辨識 ===
    image_versions = generate_image_versions(cropped_removed)
    best_texts, best_name, best_score = get_best_ocr_texts(image_versions, ocr_engine=ocr_engine)

    print("文字辨識：", best_texts if best_texts else ["None"])
    print("最佳版本：", best_name)
    print("信心分數：", round(best_score, 3))
    print("顏色：", colors)
    print("外型：", shape)

    return {
        "文字辨識": best_texts if best_texts else ["None"],
        "最佳版本": best_name,
        "信心分數": round(best_score, 3),
        "顏色": colors,
        "外型": shape,

        "cropped_image": cropped_b64
    }
