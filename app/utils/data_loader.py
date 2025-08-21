import pandas as pd

VALID_COLORS = [
    "白色", "透明", "黑色", "棕色", "紅色", "橘色",
    "皮膚色", "黃色", "綠色", "藍色", "紫色", "粉紅色", "灰色"
]

VALID_SHAPES = ["圓形", "橢圓形", "其他"]


def generate_color_shape_dicts(df: pd.DataFrame, start_index=1, end_index=10000):
    color_dict = {color: [] for color in VALID_COLORS}
    shape_dict = {shape: [] for shape in VALID_SHAPES}
    invalid_colors = set()

    df_range = df[(df["用量排序"] >= start_index) & (df["用量排序"] <= end_index)]

    for _, row in df_range.iterrows():
        usage_order = row.get("用量排序")
        if pd.isna(usage_order):
            continue
        usage_order = int(usage_order)

        # === 外型分類 ===
        shape = str(row.get("形狀", "")).strip()
        if shape in shape_dict:
            shape_dict[shape].append(usage_order)
        else:
            shape_dict["其他"].append(usage_order)

        # === 顏色分類（支援多色）===
        raw_colors = str(row.get("顏色", "")).strip()
        for part in raw_colors.split("|"):
            color = part.strip()
            if color in color_dict:
                color_dict[color].append(usage_order)
            elif color:
                invalid_colors.add(color)

    return color_dict, shape_dict, sorted(invalid_colors)
