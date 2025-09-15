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
    _pick_crop_from_boxes  # uses YOLO crop without background removal
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
DEFAULT_END =1
# Where to write the summary workbook
DEFAULT_REPORT_XLSX = Path("reports/藥物辨識成功率總表.xlsx")
DEFAULT_REPORT_XLSX.parent.mkdir(parents=True, exist_ok=True)
PRINT_COLOR_ERRORS = True  # 途中即時印出顏色誤判明細


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


def _to_color_set_exact(colors):
    """把預測清單轉成『嚴格』集合（去空白、去空字、去重；不做任何近似映射）。"""
    if not colors:
        return set()
    return set(c.strip() for c in colors if c and c.strip())


def _parse_expected_colors_exact(exp):
    """把 Excel 欄位 '白色|紅色' 解析成嚴格集合（不做任何近似映射）。"""
    if not isinstance(exp, str):
        return set()
    parts = [p.strip() for p in exp.split("|") if p.strip()]
    return set(parts)


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


import app.utils.pill_detection as P


def _run_single_image(img_path: Path, det_model, exp_shape=None, enable_fallback=True):
    """
    Batch-side pipeline aligned with process_image:
    YOLO(conf=0.25→0.10) → (optional REMBG fallback) → shape/color → multi-version OCR
    Returns: {"text", "shape", "colors", "yolo_ok"}
    """
    out = P.process_image(str(img_path))
    if not out or out.get("error"):
        return {"out": out, "yolo_ok": False, "clusters": [], "center_ratio": 0.50, "margin_ratio": 0.08}

    dbg = out.get("debug", {}) or {}
    detsrc = dbg.get("det_source", "")
    yolo_ok = detsrc in ("yolo_conf_0.25", "yolo_conf_0.10", "rembg")  # 你要不要把 rembg 算成功自行決定

    return {
        "out": out,
        "yolo_ok": yolo_ok,

    }


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

    # === NEW: 顏色誤判收集 ===
    color_errors = []  # 逐張錯誤清單
    color_confusion = defaultdict(int)  # (expected_key, predicted_key) → 次數

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

        for img_path in imgs:
            total_images += 1

            yolo_total += 1
            res = _run_single_image(img_path, det_model, exp_shape=exp_shape)
            out = res["out"]

            if not out or out.get("error"):
                continue
            if res["yolo_ok"]:
                yolo_success += 1
            # 取出結果
            texts = out.get("文字辨識", []) or []
            shape_ = (out.get("外型", "") or "").strip()
            colors = out.get("顏色", []) or []
            # Text correctness
            rec_concat = "".join(texts).upper().replace(" ", "")
            if none_expected:
                is_text_correct = True
            else:
                is_text_correct = (_tokens_match(rec_concat, f_tokens) or _tokens_match(rec_concat, b_tokens))
            if is_text_correct:
                text_success_total += 1
                total_success += 1

            # Shape correctness
            is_shape_correct = (shape_ == exp_shape) if exp_shape else False

            # Color correctness (order-insensitive with mapping)
            # Color correctness (order-insensitive, EXACT match, no near-color mapping)
            pred_color_set = _to_color_set_exact(colors)
            print(f"pred: {pred_color_set}")
            exp_color_set = _parse_expected_colors_exact(row.get("顏色", ""))  # 你的欄名依實際為準
            print(f"exp: {exp_color_set}")
            is_color_correct = (
                    exp_color_set and pred_color_set and len(pred_color_set.intersection(exp_color_set)) > 0)

            ###以下可刪###
            # Color correctness（嚴格集合）

            # === 顏色錯誤：記錄 + （可選）即時列印 ===
            if exp_color_set and (not pred_color_set or not bool(pred_color_set & exp_color_set)):

                # 原樣（保留順序）字串，便於人眼比對
                exp_list_raw = [p.strip() for p in str(row.get("顏色", "")).split("|") if p.strip()]
                pred_list_raw = colors or []

                # 集合差異（缺少 / 多出）
                missing = sorted(list(exp_color_set - pred_color_set))  # 期望有但未預測
                extra = sorted(list(pred_color_set - exp_color_set))  # 多預測出來

                # 收進列表（若你有 color_errors / color_confusion）
                try:
                    color_errors.append({
                        "用量排序": usage_order,
                        "學名": raw_name,
                        "圖片": str(img_path),
                        "期望顏色": "|".join(exp_list_raw) if exp_list_raw else "",
                        "預測顏色": "|".join(pred_list_raw) if pred_list_raw else "",
                        "缺少": "|".join(missing),
                        "多出": "|".join(extra),
                    })
                    exp_key = "|".join(sorted(exp_color_set)) if exp_color_set else "∅"
                    pred_key = "|".join(sorted(pred_color_set)) if pred_color_set else "∅"
                    color_confusion[(exp_key, pred_key)] += 1
                except NameError:
                    # 若你尚未宣告 color_errors/color_confusion，也不會噴錯
                    pass

                # === 即時列印（可用開關關閉）===
                if PRINT_COLOR_ERRORS:
                    print(f"\n[COLOR ❌] [{usage_order}] {raw_name}")
                    print(f"  期望：{'|'.join(exp_list_raw) if exp_list_raw else '∅'}")
                    print(f"  預測：{'|'.join(pred_list_raw) if pred_list_raw else '∅'}")
                    if missing:
                        print(f"  缺少：{', '.join(missing)}")
                    if extra:
                        print(f"  多出：{', '.join(extra)}")
                    print(f"  圖片：{img_path}")

                ###以上可刪###
            if is_text_correct:
                text_success_total += 1

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

    # 以下顏色辨識可刪##
    # === NEW: 列印部分誤判樣本 & 匯出 Excel ===
    if color_errors:
        print("\n🎨 顏色誤判樣本（最多列出前 30 筆）：")
        for e in color_errors[:30]:
            print(f"  [{e['用量排序']}] {e['學名']}")
            print(f"    期望：{e['期望顏色']} | 預測：{e['預測顏色']} | 缺少：{e['缺少']} | 多出：{e['多出']}")

        # 轉成 DataFrame
        err_df = pd.DataFrame(color_errors)
        # 混淆表
        cf_rows = [
            {"expected": ek, "predicted": pk, "count": v}
            for (ek, pk), v in color_confusion.items()
        ]
        cf_df = pd.DataFrame(cf_rows)
        if not cf_df.empty:
            cf_pivot = cf_df.pivot(index="expected", columns="predicted", values="count").fillna(0).astype(int)
        else:
            cf_pivot = pd.DataFrame()

        # 輸出到 reports/color_errors.xlsx
        os.makedirs("reports", exist_ok=True)
        out_xlsx = Path("reports/color_errors.xlsx")
        with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
            err_df.to_excel(writer, sheet_name="errors", index=False)
            if not cf_pivot.empty:
                cf_pivot.to_excel(writer, sheet_name="confusion")
        print(f"📝 顏色誤判已輸出：{out_xlsx}")
    else:
        print("\n🎨 顏色誤判：無（全部顏色都符合期望）。")
    # 以上顏色辨識可刪##
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
        acc = main(excel, root, start, end, report, write_report=False)  # 或 main(..., write_report=True)
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
