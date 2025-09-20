import itertools


# LCS 相似度計算（忽略大小寫）
def lcs_score(a: str, b: str) -> float:
    a = a.lower()
    b = b.lower()
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m):
        for j in range(n):
            if a[i] == b[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(dp[i][j + 1], dp[i + 1][j])
    lcs_len = dp[-1][-1]
    return lcs_len / max(m, n)


def match_ocr_to_front_back_by_permuted_ocr(ocr_texts, df, threshold=0.8):
    best_front = {"score": 0.0, "text": "", "match": None, "row": None}
    best_back = {"score": 0.0, "text": "", "match": None, "row": None}

    # === 特例：藥袋內容快速比對 ===
    combined_all = ''.join(ocr_texts).upper()
    keywords = {"ACETYLCYSTEINE", "ACTEIN"}
    if any(kw in combined_all for kw in keywords):
        # print("🚀 偵測到藥袋特例（ACETYLCYSTEINE 或 ACTEIN），直接比對學名")#註解SSS
        matched_rows = df[df["文字"].str.contains("ACETYLCYSTEINE|ACTEIN", case=False, na=False)]
        if not matched_rows.empty:
            match_row = matched_rows.iloc[0]
            return {
                "front": {
                    "score": 1.0,
                    "text": "藥袋特例",
                    "match": "ACETYLCYSTEINE / ACTEIN",
                    "row": match_row
                }
            }

    # === 正常流程：排列 OCR 結果再逐一比對 ===
    permutations = itertools.permutations(ocr_texts)
    for perm in permutations:
        combined_ocr = ''.join(perm).upper()

        for _, row in df.iterrows():
            text_field = str(row.get("文字", "")).strip()
            parts = text_field.split('|')

            front_text = ""
            back_text = ""

            for p in parts:
                if ':' in p:
                    k, v = p.split(':', 1)
                    key = k.strip().upper()
                    val = v.strip().upper()
                    if key == "F":
                        front_text = val
                    elif key == "B":
                        back_text = val

            # 比對 F
            if front_text:
                score_f = lcs_score(combined_ocr, front_text)
                # print(f"[DEBUG-F] 比對 {combined_ocr} ↔ {front_text} ➜ score = {score_f:.3f}")
                if score_f > best_front["score"]:
                    best_front.update({"score": score_f, "text": combined_ocr, "match": front_text, "row": row})

            # 比對 B
            if back_text:
                score_b = lcs_score(combined_ocr, back_text)
                # print(f"[DEBUG-B] 比對 {combined_ocr} ↔ {back_text} ➜ score = {score_b:.3f}")
                if score_b > best_back["score"]:
                    best_back.update({"score": score_b, "text": combined_ocr, "match": back_text, "row": row})

    # === 判斷是否達門檻 ===
    result = {}
    if best_front["score"] >= threshold:
        # print("最佳正面比對結果：", best_front["match"], f"(score={best_front['score']:.3f})")
        result["front"] = best_front
    if best_back["score"] >= threshold:
        # print("最佳背面比對結果：", best_back["match"], f"(score={best_back['score']:.3f})")
        result["back"] = best_back

    # === 不達門檻時，取分數最高的結果 ===
    if not result:
        if best_front["score"] >= 0.5:
            # print("⚠沒有達門檻，但採用最接近的 FRONT 結果")
            result["front"] = best_front
        elif best_back["score"] >= 0.5:
            # print("⚠沒有達門檻，但採用最接近的 BACK 結果")
            result["back"] = best_back

    return result if result else None

def match_top_n_ocr_to_front_back(ocr_texts, df, threshold=0.8, top_n=3):
    results = []

    combined_all = ''.join(ocr_texts).upper()
    keywords = {"ACETYLCYSTEINE", "ACTEIN"}
    if any(kw in combined_all for kw in keywords):
        matched_rows = df[df["文字"].str.contains("ACETYLCYSTEINE|ACTEIN", case=False, na=False)]
        if not matched_rows.empty:
            match_row = matched_rows.iloc[0]
            return [{
                "score": 1.0,
                "text": "藥袋特例",
                "match": "ACETYLCYSTEINE / ACTEIN",
                "row": match_row,
                "side": "front"
            }]

    permutations = itertools.permutations(ocr_texts)
    for perm in permutations:
        combined_ocr = ''.join(perm).upper()

        for _, row in df.iterrows():
            text_field = str(row.get("文字", "")).strip()
            parts = text_field.split('|')

            front_text, back_text = "", ""

            for p in parts:
                if ':' in p:
                    k, v = p.split(':', 1)
                    key = k.strip().upper()
                    val = v.strip().upper()
                    if key == "F":
                        front_text = val
                    elif key == "B":
                        back_text = val

            # 比對 F
            if front_text:
                score_f = lcs_score(combined_ocr, front_text)
                if score_f >= 0.5:
                    results.append({
                        "score": score_f,
                        "text": combined_ocr,
                        "match": front_text,
                        "row": row,
                        "side": "front"
                    })

            # 比對 B
            if back_text:
                score_b = lcs_score(combined_ocr, back_text)
                if score_b >= 0.5:
                    results.append({
                        "score": score_b,
                        "text": combined_ocr,
                        "match": back_text,
                        "row": row,
                        "side": "back"
                    })

    # 優先保留高於 threshold 的，再補滿 top_n
    filtered = [r for r in results if r["score"] >= threshold]
    if len(filtered) >= top_n:
        return sorted(filtered, key=lambda r: -r["score"])[:top_n]
    else:
        return sorted(results, key=lambda r: -r["score"])[:top_n]
