# app/scripts/fit_color_rules.py
import json, os
import numpy as np
import pandas as pd
from pathlib import Path

CSV_PATH = Path("reports/color_debug.csv")
OUT_PATH = Path("config/color_rules.json")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# 你系統的中文顏色名稱
NEUTRALS = {"白色", "灰色", "透明", "皮膚色", "黑色"}
CHROMA_ORDER = ["紅色", "橘色", "黃色", "綠色", "藍色", "紫色", "粉紅色"]


def q(a, p):
    a = np.asarray(a, dtype=float)
    a = a[~np.isnan(a)]
    if a.size == 0: return None
    return float(np.percentile(a, p))


def main():
    assert CSV_PATH.exists(), f"找不到 {CSV_PATH}"
    df = pd.read_csv(CSV_PATH)
    # 只用主群 (hsv0_*)
    df = df.dropna(subset=["hsv0_h", "hsv0_s", "hsv0_v"], how="any")
    df["pred_color1"] = df["pred_color1"].fillna("").astype(str).str.strip()
    df = df[df["pred_color1"] != ""]

    # 每類彙整
    rules = {}

    # --- 白色：S 小、V 大 ---
    # 允許把「低飽和且高亮」但被預測為 黃/粉/灰 的樣本併入白色估計，打破偏差
    near_white_mask = (
            (df["pred_color1"]=="白色") |
            ((df["pred_color1"].isin(["黃色","粉紅色","灰色"])) & (df["hsv0_s"]<=40) & (df["hsv0_v"]>=200))
    )
    s_white = df.loc[near_white_mask, "hsv0_s"].to_numpy(float)
    v_white = df.loc[near_white_mask, "hsv0_v"].to_numpy(float)

    if s_white.size > 0 and v_white.size > 0:
        s_max_est = q(s_white, 90)  # 放寬一點
        v_min_est = q(v_white, 10)

        rules["white"] = {
            # 至少允許到 ~38，避免太嚴；若數據更寬也會跟著長大
            "s_max": int(max(38, round(s_max_est if s_max_est is not None else 38))),
            # 最高不超過 ~210（越低越寬），避免被拉到 230+ 的過嚴值
            "v_min": int(min(210, round(v_min_est if v_min_est is not None else 210))),
        }


# --- 灰色：S 小、V 中低（依你資料再調）---
    s_gray = df.loc[df["pred_color1"] == "灰色", "hsv0_s"].to_numpy(float)
    v_gray = df.loc[df["pred_color1"] == "灰色", "hsv0_v"].to_numpy(float)
    if s_gray.size > 0 and v_gray.size > 0:
        s_max_g = q(s_gray, 80)
        v_max_g = q(v_gray, 80)
        rules["gray"] = {
            # 灰允許比白更高的飽和度，但也別太低
            "s_max": int(max(40, round(s_max_g if s_max_g is not None else 40))),
            # 至少放到 180，避免把大量米灰排除
            "v_max": int(max(180, round(v_max_g if v_max_g is not None else 180))),
        }


# --- 透明 & 皮膚色（如有樣本才學，否則給保守預設）---
    s_tr = df.loc[df["pred_color1"] == "透明", "hsv0_s"].to_numpy(float)
    v_tr = df.loc[df["pred_color1"] == "透明", "hsv0_v"].to_numpy(float)
    if s_tr.size > 0 and v_tr.size > 0:
        rules["transparent"] = {"s_max": round(q(s_tr, 80)), "v_min": round(q(v_tr, 20))}
    else:
        rules["transparent"] = {"s_max": 25, "v_min": 200}

    s_skin = df.loc[df["pred_color1"] == "皮膚色", "hsv0_s"].to_numpy(float)
    v_skin = df.loc[df["pred_color1"] == "皮膚色", "hsv0_v"].to_numpy(float)
    h_skin = df.loc[df["pred_color1"] == "皮膚色", "hsv0_h"].to_numpy(float)
    if s_skin.size > 0 and v_skin.size > 0 and h_skin.size > 0:
        rules["skin_like"] = {
            "h_min": round(q(h_skin, 10)),
            "h_max": round(q(h_skin, 90)),
            "s_max": round(q(s_skin, 80)),
            "v_min": round(q(v_skin, 20)),
        }
    else:
        rules["skin_like"] = {"h_min": 10, "h_max": 40, "s_max": 120, "v_min": 150}

    # --- 彩色：用 H 的中位數定中心，分位數定 S/V 下限 ---
    hue_centers = []
    hue_svmins = {}
    for cname in CHROMA_ORDER:
        sub = df.loc[df["pred_color1"] == cname]
        if sub.empty: continue
        H = sub["hsv0_h"].to_numpy(float);
        S = sub["hsv0_s"].to_numpy(float);
        V = sub["hsv0_v"].to_numpy(float)
        h_med = q(H, 50);
        s_min = q(S, 25);
        v_min = q(V, 10)  # S/V 下限寬鬆些
        if h_med is None: continue
        hue_centers.append((cname, h_med))
        hue_svmins[cname] = {"s_min": int(round(s_min or 35)), "v_min": int(round(v_min or 0))}
        # 彩色的 s_min 不要太高（≤80），讓淡黃/淡紅也能被納入
        hue_svmins[cname]["s_min"] = min(hue_svmins[cname]["s_min"], 80)

# 若資料不足，就給保守預設
    if not hue_centers:
        hue_centers = [("紅色", 0), ("橘色", 20), ("黃色", 45), ("綠色", 120), ("藍色", 210), ("紫色", 275),
                       ("粉紅色", 320)]
        hue_svmins = {c: {"s_min": 35, "v_min": 0} for c, _ in hue_centers}

    # 依中心排序並產生區間（圓環型）
    hue_centers.sort(key=lambda x: x[1])  # 依中心角度排序
    ranges = []
    centers_only = [h for _, h in hue_centers]
    names_only = [n for n, _ in hue_centers]

    def mid(a, b):
        # 角度中點（考慮 360 wrap）
        d = (b - a) % 360
        return (a + d / 2) % 360

    # 計算各色的 h_min/h_max 為「相鄰中心的中點」
    for i, name in enumerate(names_only):
        h_c = centers_only[i]
        h_prev = centers_only[i - 1] if i > 0 else centers_only[-1]
        h_next = centers_only[(i + 1) % len(centers_only)]
        h_min = mid(h_prev, h_c)
        h_max = mid(h_c, h_next)
        # 紅色可能跨 360 → 交給 get_basic_color_name 的“跨界”判斷（h_min>h_max 視為跨 360）
        r = {
            "name": name,
            "h_min": int(round(h_min)),
            "h_max": int(round(h_max)),
            "s_min": hue_svmins[name]["s_min"],
            "v_min": hue_svmins[name]["v_min"],
        }
        ranges.append(r)

    # 特別處理：確保紅色涵蓋 350~360 與 0~10（若你的資料中心在 0° 左右）
    # 若你要更硬性，可在這裡追加第二段紅色 例如 {"name":"紅色","h_min":350,"h_max":360,...}

    out = {
        "white": rules.get("white", {"s_max": 40, "v_min": 190}),
        "gray": rules.get("gray", {"s_max": 40, "v_max": 180}),
        "transparent": rules.get("transparent", {"s_max": 25, "v_min": 200}),
        "skin_like": rules.get("skin_like", {"h_min": 10, "h_max": 40, "s_max": 120, "v_min": 150}),
        "hue_ranges": ranges,
    }

    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出: {OUT_PATH}")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
