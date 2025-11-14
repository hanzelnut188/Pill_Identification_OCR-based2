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
COMBINED_COLOR_MAP = { 
    "橘色與黃色": ["橘色", "黃色"],
    "紅色與紅粉色": ["紅色", "粉紅色"],
}

def collapse_colors(matched_colors):
    """
    Collapse single colors into combined color names for frontend display.
    Handles extra colors gracefully.
    """
    matched_set = set(matched_colors)
    collapsed = []

    # 1️⃣ Merge combined colors first
    for combined, parts in COMBINED_COLOR_MAP.items():
        if all(p in matched_set for p in parts):
            collapsed.append(combined)
            # remove matched parts so they don't appear again
            matched_set -= set(parts)

    # 2️⃣ Add remaining unmatched single colors
    # Sort alphabetically for consistent frontend display
    collapsed.extend(sorted(matched_set))

    return collapsed
