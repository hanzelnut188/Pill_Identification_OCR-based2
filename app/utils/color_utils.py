COMBINED_COLOR_MAP = {
    "橘色與黃色": ["橘色", "黃色"],
    "紅色與紅粉色": ["紅色", "粉紅色"],
}

def expand_colors(selected_colors):
    expanded = []
    for c in selected_colors:
        expanded += COMBINED_COLOR_MAP.get(c, [c])
    return expanded

# 將比對結果的單一色 collapse 回前端的組合色
def collapse_colors(matched_colors):
    collapsed = []
    for combined, parts in COMBINED_COLOR_MAP.items():
        if all(p in matched_colors for p in parts):
            collapsed.append(combined)
            # remove these parts from matched_colors so we don't double-count
            for p in parts:
                if p in matched_colors:
                    matched_colors.remove(p)
    # add any remaining colors that were not part of combined mapping
    collapsed += matched_colors
    return collapsed