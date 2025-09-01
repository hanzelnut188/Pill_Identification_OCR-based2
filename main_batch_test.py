# app/main_batch_test.py
# Batch evaluation for pill recognition accuracy (text/shape/color + per-drug stats)
import time
import os
import re
import datetime
from pathlib import Path
from collections import defaultdict

import cv2

import app.utils.shape_color_utils as scu
import datetime
import os
import pandas as pd
import numpy as np

# Reuse your existing pipeline modules
from app.utils.pill_detection import (
    get_det_model,
    _pick_crop_from_boxes,  # uses YOLO crop without background removal
)
from app.utils.image_io import read_image_safely
from app.utils.shape_color_utils import (
    # extract_dominant_colors_by_ratio
    get_basic_color_name,
    get_dominant_colors,
    detect_shape_from_image
)
# OCR helpers (use pill_detection’s OpenOCR engine & version generator)
import app.utils.pill_detection as P  # gives access to generate_image_versions, get_best_ocr_texts, ocr_engine

# ---------- Config (edit these defaults as needed) ----------
# Excel with ground-truth
DEFAULT_EXCEL = Path("data/TESTData.xlsx")
# Root that contains subfolders per drug (named by 學名, “/” replaced by space)
DEFAULT_IMAGES_ROOT = Path(r"C:\Users\92102\OneDrive - NTHU\桌面\大三下\畢業專題\drug_photos")
# Evaluation range (用量排序)
DEFAULT_START = 1
DEFAULT_END = 402
# Where to write the summary workbook
DEFAULT_REPORT_XLSX = Path("reports/藥物辨識成功率總表.xlsx")
DEFAULT_REPORT_XLSX.parent.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------


def _norm_expected_text_tokens(exp: str):
    """
    Parse expected text in 'F:...|B:...' format into token lists.
    Returns (front_tokens, back_tokens, is_none_expected)
    """
    if not isinstance(exp, str):
        return [], [], True
    s = exp.strip().upper().replace(" ", "")
    if s in ("", "F:NONE|B:NONE"):
        return [], [], True

    # Extract F and B payloads
    m = re.match(r"^F:(.*?)\|B:(.*)$", s)
    if not m:
        # Fallback: treat whole string as a single side
        toks = re.findall(r"[A-Z0-9\-]+", s)
        return toks, [], False

    f_raw, b_raw = m.group(1), m.group(2)
    f_none = (f_raw == "NONE")
    b_none = (b_raw == "NONE")
    f_tokens = [] if f_none else re.findall(r"[A-Z0-9\-]+", f_raw)
    b_tokens = [] if b_none else re.findall(r"[A-Z0-9\-]+", b_raw)

    is_none_expected = (f_none and b_none)
    return f_tokens, b_tokens, is_none_expected


def _tokens_match(recognized_str: str, tokens):
    """Check if all expected tokens appear in the recognized string."""
    if not tokens:
        return False
    return all(tok in recognized_str for tok in tokens)


def _normalize_colors_set(colors):
    """Map near-colors to same bucket and return a set."""
    if not colors:
        return set()
    mapping = {
        "皮膚色": "黃色",
        "橘色": "紅色",
        "粉紅色": "紅色",
        "透明": "白色",
        "棕色": "黑色",
    }
    out = []
    for c in colors:
        c = (c or "").strip()
        out.append(mapping.get(c, c))
    return set(out)


def _expected_color_set(exp: str):
    """Parse expected colors string like '白色|黃色' into mapped set."""
    if not isinstance(exp, str):
        return set()
    parts = [p.strip() for p in exp.split("|") if p.strip()]
    return _normalize_colors_set(parts)


def _collect_images(folder: Path):
    """Gather image files under a drug folder, skip augmented names."""
    if not folder.exists():
        return []
    exts = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
    skip_keywords = ["_rot", "_bright", "_noise", "_flip", "_removed", "NEW_PHOTOS"]
    imgs = []
    for p in folder.rglob("*"):
        if p.suffix.lower() in exts and not any(k in str(p) for k in skip_keywords):
            imgs.append(p)
    return imgs


def _run_single_image(img_path: Path, det_model, exp_shape=None):
    """
    Run the same pipeline you use online, but keep it local and without rembg fallback.
    Returns dict with keys: text(list), shape(str), colors(list), yolo_ok(bool)
    """
    img = read_image_safely(img_path)
    if img is None:
        return {"text": [], "shape": "", "colors": [], "yolo_ok": False}

    # YOLO detect (try normal then lower conf)
    # NOTE: we call YOLO directly here to avoid rembg fallback path
    fp16 = False  # keep CPU friendly
    res = det_model.predict(source=img, imgsz=640, conf=0.25, iou=0.7, device="cpu", verbose=False, half=fp16)[0]
    boxes = res.boxes
    if boxes is None or boxes.xyxy.shape[0] == 0:
        res_lo = det_model.predict(source=img, imgsz=640, conf=0.10, iou=0.7, device="cpu", verbose=False, half=fp16)[0]
        boxes = res_lo.boxes

    if boxes is None or boxes.xyxy.shape[0] == 0:
        return {"text": [], "shape": "", "colors": [], "yolo_ok": False}

    # Crop using your helper (returns cropped_original, cropped_copy)
    crop = _pick_crop_from_boxes(img, boxes)

    # Shape / Color
    shape, _ = detect_shape_from_image(crop, expected_shape=exp_shape)
    # colors = extract_dominant_colors_by_ratio(crop)
    rgb_colors, hex_colors = get_dominant_colors(crop, k=3, min_ratio=0.30)
    rgb_colors_int = [tuple(map(int, c)) for c in rgb_colors]
    basic_names = []
    hsv_values = []
    for rgb in rgb_colors_int:
        bgr = np.uint8([[rgb[::-1]]])
        h_raw, s, v = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0][0]
        h_deg = h_raw * 2
        hsv_values.append((h_deg, s, v))

        cname = get_basic_color_name(rgb)
        basic_names.append(cname)

    colors = list(dict.fromkeys(basic_names))
    # OCR: generate versions then pick best
    versions = P.generate_image_versions(crop)
    texts, _, _ = P.get_best_ocr_texts(versions, ocr_engine=P.ocr_engine)

    return {"text": texts or [], "shape": shape or "", "colors": colors or [], "yolo_ok": True}


def main(
        excel_path: Path = DEFAULT_EXCEL,
        images_root: Path = DEFAULT_IMAGES_ROOT,
        start_index: int = DEFAULT_START,
        end_index: int = DEFAULT_END,
        report_xlsx: Path = DEFAULT_REPORT_XLSX,
        write_report: bool = True
):
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel not found: {excel_path}")

    df = pd.read_excel(excel_path)
    df_range = df[(df["用量排序"] >= start_index) & (df["用量排序"] <= end_index)].copy()
    if df_range.empty:
        print("[WARN] No rows in the specified range.")
        return

    det_model = get_det_model()
    if hasattr(scu, "RATIO_LOG"):
        scu.RATIO_LOG.clear()
    # Counters
    total_images = 0
    text_success_total = 0
    shape_success_total = 0
    color_success_total = 0
    total_success = 0
    yolo_total = 0
    yolo_success = 0

    per_drug_stats = defaultdict(lambda: {"total": 0, "success": 0})
    missing_folders = []
    t0 = time.perf_counter()
    for _, row in df_range.iterrows():
        raw_name = str(row.get("學名", "")).strip()
        usage_order = int(row.get("用量排序", -1))
        folder_name = raw_name.replace("/", " ")
        folder = images_root / folder_name

        if not folder.exists():
            missing_folders.append((usage_order, raw_name))
            continue

        imgs = _collect_images(folder)
        if not imgs:
            print(f"[SKIP] No images in: {folder}")
            continue

        # Expected ground truth from Excel
        exp_text = str(row.get("文字", "")).strip()
        f_tokens, b_tokens, none_expected = _norm_expected_text_tokens(exp_text)

        exp_shape = str(row.get("形狀", "")).strip()
        exp_color_set = _expected_color_set(str(row.get("顏色", "")).strip())

        for img_path in imgs:
            total_images += 1

            out = _run_single_image(img_path, det_model, exp_shape=exp_shape)
            yolo_total += 1
            if out["yolo_ok"]:
                yolo_success += 1

            # Text correctness
            rec_concat = "".join(out["text"]).upper().replace(" ", "")
            is_text_correct = False
            if none_expected:
                is_text_correct = True
            else:
                if _tokens_match(rec_concat, f_tokens) or _tokens_match(rec_concat, b_tokens):
                    is_text_correct = True

            # Shape correctness
            is_shape_correct = False
            if exp_shape:
                is_shape_correct = (out["shape"].strip() == exp_shape)

            # Color correctness (order-insensitive with mapping)
            pred_color_set = _normalize_colors_set(out["colors"])
            is_color_correct = False
            if exp_color_set:
                is_color_correct = (pred_color_set == exp_color_set)

            if is_text_correct:
                text_success_total += 1
                total_success += 1  # overall metric uses text as primary

            if is_shape_correct:
                shape_success_total += 1

            if is_color_correct:
                color_success_total += 1

            per_drug_stats[raw_name]["total"] += 1
            if is_text_correct:
                per_drug_stats[raw_name]["success"] += 1

    # ---------- Print summary ----------
    if missing_folders:
        print("\n[Missing folders]")
        for uo, name in missing_folders:
            print(f"  用量排序={uo}  學名={name}")
        print(f"Total missing: {len(missing_folders)}")

    if total_images == 0:
        print("\n[RESULT] No images processed.")
        return

    text_rate = text_success_total / total_images
    shape_rate = shape_success_total / total_images
    color_rate = color_success_total / total_images
    match_rate = total_success / total_images
    yolo_rate = yolo_success / max(1, yolo_total)
    roboflow_total = yolo_total
    roboflow_success = yolo_success

    print("\n📊 總體統計：")

    print("🔠 文字辨識：")
    print(f" - 辨識結果：{text_success_total} 張正確")
    print(f" - 正式結果：{total_images} 張（總圖片數）")
    print(f" - 辨識成功率：{text_rate:.2%}" if total_images else " - 辨識成功率：N/A")

    print("\n🟫 外型辨識：")
    print(f" - 辨識結果：{shape_success_total} 張正確")
    print(f" - 正確結果：{total_images} 張（總圖片數）")
    print(f" - 辨識成功率：{shape_rate:.2%}" if total_images else " - 辨識成功率：N/A")

    print("\n🎨 顏色辨識：")
    print(f" - 辨識結果：{color_success_total} 張正確")
    print(f" - 正確結果：{total_images} 張（總圖片數）")
    print(f" - 辨識成功率：{color_rate:.2%}" if total_images else " - 辨識成功率：N/A")

    print("\n💊 藥品名稱比對：")
    print(f" - 辨識結果：{total_success} 張比對成功")
    print(f" - 正確結果：{total_images} 張（總圖片數）")
    print(
        f" - 整體辨識成功率（以文字為主）：{match_rate:.2%}" if total_images else " - 整體辨識成功率（以文字為主）：N/A")

    print("\n🔍 Roboflow 偵測統計：")
    print(f" - 成功偵測圖片數：{roboflow_success} / {roboflow_total}")
    print(f" - 偵測成功率：{yolo_rate:.2%}" if roboflow_total else " - 偵測成功率：N/A")

    # print("📦 各藥品辨識情況：")
    # for drug, stats in per_drug_stats.items():
    #     print(f"- {drug}: {stats['success']} / {stats['total']} 成功")

    # ---------- Write to report workbook ----------
    # Column name: today (or _v2, _v3 if exists)

    # ---------- 寫回「藥物辨識成功率總表.xlsx」：索引/欄位名稱完全沿用舊版 ----------

    # 路徑請依你目前環境調整；若不在 Colab，改成本機路徑即可
    text_rate = round(text_success_total / total_images, 4) if total_images else None
    shape_rate = round(shape_success_total / total_images, 4) if total_images else None
    color_rate = round(color_success_total / total_images, 4) if total_images else None
    match_rate = round(total_success / total_images, 4) if total_images else None
    roboflow_rate = round(roboflow_success / total_images, 4) if total_images else None

    if write_report:
        rate_excel_path = r"reports\藥物辨識成功率總表.xlsx"

        base_col_name = datetime.datetime.now().strftime("%Y-%m-%d")
        col_name = base_col_name

        # === [2] 自訂 index：403 個藥物 + 15 統計欄位 ===
        drug_indexes = [str(i) for i in range(1, 404)]
        stat_indexes = [
            "文字辨識正確數",
            "文字辨識總數",
            "文字成功率",
            "外型辨識正確數",
            "外型辨識總數",
            "外型成功率",
            "顏色辨識正確數",
            "顏色辨識總數",
            "顏色成功率",
            "藥名比對正確數",
            "藥名比對總數",
            "藥名比對成功率",
            "Roboflow 正確數",
            "Roboflow 總數",
            "Roboflow 成功率"
        ]
        custom_index = drug_indexes + stat_indexes

        # === [3] 讀取或初始化目標 Excel ===
        if os.path.exists(rate_excel_path):
            rate_df = pd.read_excel(rate_excel_path, index_col=0)
            rate_df.index = rate_df.index.astype(str)

            # 確保 DataFrame 有正確的 index（重新索引，缺失的用 NaN 填充）
            rate_df = rate_df.reindex(custom_index)
        else:
            rate_df = pd.DataFrame(index=custom_index)

        # === [4] 欄位名稱自動加版本避免覆蓋 ===
        version = 1
        while col_name in rate_df.columns:
            version += 1
            col_name = f"{base_col_name}_v{version}"

        # === [5] 個別藥品成功率（403 筆） ===
        new_col = []
        for idx in range(1, 404):
            matched_rows = df[df["用量排序"] == idx]
            if matched_rows.empty:
                new_col.append(None)
                continue
            drug_name = str(matched_rows["學名"].values[0]).strip()
            stat = per_drug_stats.get(drug_name, None)
            if stat and stat["total"] > 0:
                success_rate = stat["success"] / stat["total"]
            else:
                success_rate = None
            new_col.append(success_rate)

        # === [6] 總體統計資料 ===

        # === [7] 附加統計欄位 ===
        new_col += [
            text_success_total, total_images, text_rate,
            shape_success_total, total_images, shape_rate,
            color_success_total, total_images, color_rate,
            total_success, total_images, match_rate,
            roboflow_success, total_images, roboflow_rate
        ]

        if len(new_col) != len(rate_df.index):
            raise ValueError(f"資料長度不匹配！new_col: {len(new_col)}, DataFrame index: {len(rate_df.index)}")

        # === [9] 寫入並儲存 ===
        rate_df[col_name] = new_col
        os.makedirs(os.path.dirname(rate_excel_path), exist_ok=True)
        rate_df.to_excel(rate_excel_path, engine="openpyxl")
        print(f"✅ 已成功將辨識結果寫入 Excel：{rate_excel_path}（欄位：{col_name}）")

    t2 = time.perf_counter()
    print(f"完成，總耗時 {t2 - t0:.2f}s")

    return shape_success_total / total_images if total_images else 0.0


def _set_shape_thresholds(circle_lo, circle_hi, ellipse_hi):
    # 匯入你剛剛加了全域參數的模組
    import app.utils.shape_color_utils as scu
    scu.set_shape_thresholds(circle_lo, circle_hi, ellipse_hi)


if __name__ == "__main__":
    # Simple CLI via env vars or edit defaults at top
    excel = Path(os.environ.get("BATCH_EXCEL", DEFAULT_EXCEL))
    root = Path(os.environ.get("BATCH_IMAGES_ROOT", DEFAULT_IMAGES_ROOT))
    start = int(os.environ.get("BATCH_START", DEFAULT_START))
    end = int(os.environ.get("BATCH_END", DEFAULT_END))
    report = Path(os.environ.get("BATCH_REPORT", DEFAULT_REPORT_XLSX))

    DO_SEARCH = False  # 想直接跑單次就設 False
    # DO_SEARCH = False  # 想直接跑單次就設 False
    _set_shape_thresholds(1.00, 1.20, 3.80)
    if not DO_SEARCH:
        # 單次跑：用目前預設門檻
        acc = main(excel, root, start, end, report)  # 或 main(..., write_report=True)
        print(f"[RUN] shape accuracy = {acc:.4%}")
    else:

        grid_lo = [1.00]
        grid_hi = [1.10, 1.15, 1.20, 1.25]
        grid_ehi = [2.0, 2.5, 3.0, 3.5]
        # === Top 10 (coarse) ===
        # 1) acc=87.6143%  circle=(1.00,1.20)  ellipse<=3.80
        # 2) acc=87.2486%  circle=(1.00,1.24)  ellipse<=3.80
        # 3) acc=86.8830%  circle=(1.00,1.16)  ellipse<=3.80

        best = []
        for lo in grid_lo:
            for hi in grid_hi:
                # 不需要寬度檢查了，因為 lo 固定 1.00
                for ehi in grid_ehi:
                    if ehi <= hi:  # 橢圓上限要高於圓形上限
                        continue
                    _set_shape_thresholds(lo, hi, ehi)
                    print(f"\n[SEARCH] circle=({lo:.2f},{hi:.2f}) ellipse<={ehi:.2f}")
                    acc = main(excel, root, start, end, report, write_report=False)  # 先不要寫報表
                    best.append((acc, lo, hi, ehi))
                    print(f"[SEARCH] shape acc = {acc:.4%}")

        best.sort(key=lambda x: x[0], reverse=True)
        print("=== Top 10 (coarse) ===")
        for i, (acc, lo, hi, ehi) in enumerate(best[:10], 1):
            print(f"{i}) acc={acc:.4%}  circle=({lo:.2f},{hi:.2f})  ellipse<={ehi:.2f}")

        # 用最佳組合正式跑一次並寫入報表
        best_acc, best_lo, best_hi, best_ehi = best[0]
        _set_shape_thresholds(best_lo, best_hi, best_ehi)
        print(f"\n[FINAL] 使用最佳組合 circle=({best_lo},{best_hi}), ellipse<={best_ehi} 寫入報表")
        _ = main(excel, root, start, end, report, write_report=True)
