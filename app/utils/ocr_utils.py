import cv2
import json
import re
import os


def recognize_with_openocr(img, name="default", min_score=0.8, ocr_engine=None):
    """
    使用 OpenOCR 執行辨識
    - img: OpenCV 影像
    - name: 儲存暫存圖用的名稱
    - min_score: 過濾最低信心分數
    - ocr_engine: 必須傳入已初始化的 OpenOCR 引擎
    """
    if ocr_engine is None:
        raise ValueError("ocr_engine is required")

    TEMP_FOLDER = "./temp_imgs"
    os.makedirs(TEMP_FOLDER, exist_ok=True)

    temp_path = os.path.join(TEMP_FOLDER, f"temp_{name}.jpg")
    cv2.imwrite(temp_path, img)

    result, _ = ocr_engine(temp_path)

    if result is None:
        return [], 0.0

    try:
        result_json = json.loads(result[0].split('\t')[1])
        valid = [r for r in result_json if r.get("score", 0) >= min_score]
        texts = [
            re.sub(r'[^A-Z0-9\\-]', '', r["transcription"].strip().upper())
            for r in valid if r["transcription"].strip()
        ]
        avg_score = sum(r["score"] for r in valid) / len(valid) if valid else 0.0
        # print(f"[{name}] 📝 OCR 結果：{texts} (Avg Score: {avg_score:.2f})")
        return texts, avg_score
    except Exception as e:
        print(f"[{name}] ⚠️ JSON 解析失敗：{e}")
        return [], 0.0
