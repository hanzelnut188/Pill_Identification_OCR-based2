# def read_image_safely(img_path):
#     from pathlib import Path
#     import cv2
#     import numpy as np
#     from PIL import Image, ImageOps
#
#     # 嘗試註冊 HEIF 支援（若未安裝 pillow-heif 也不會噴炸）
#     _heif_ok = False
#     try:
#         import pillow_heif
#         pillow_heif.register_heif_opener()
#         _heif_ok = True
#     except Exception:
#         _heif_ok = False
#
#     p = Path(img_path)
#     if not p.exists():
#         print(f"❗ 圖片路徑不存在：{p}")
#         return None
#
#     suffix = p.suffix.lower()
#     try:
#         # === HEIC/HEIF ===
#         if suffix in {".heic", ".heif"}:
#             if not _heif_ok:
#                 print("⚠️ 環境未安裝 pillow-heif，無法讀取 HEIC/HEIF")
#                 return None
#             print(f"📄 使用 PIL 讀取 HEIC/HEIF 圖片：{p}")
#             pil_img = Image.open(p)
#             # 修正 EXIF 方向並轉 RGB
#             pil_img = ImageOps.exif_transpose(pil_img).convert("RGB")
#             np_img = np.array(pil_img)
#             return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
#
#         # === 其他常見格式 ===
#         print(f"📄 使用 OpenCV 讀取圖片：{p}")
#         img = cv2.imread(str(p), cv2.IMREAD_COLOR)
#         if img is not None:
#             return img
#
#         # OpenCV 讀不到（如某些 WebP），改用 PIL 後再轉 BGR
#         print("⚠️ OpenCV 無法讀取此圖片，改用 PIL 讀取")
#         pil_img = Image.open(p)
#         pil_img = ImageOps.exif_transpose(pil_img).convert("RGB")
#         np_img = np.array(pil_img)
#         return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
#
#     except Exception as e:
#         print(f"❌ 圖片讀取錯誤：{p} ➜ {e}")
#         return None

def read_image_safely(img_path):
    from pathlib import Path
    from PIL import Image
    import cv2
    import numpy as np
    import pillow_heif
    # 必須註冊 HEIC 支援
    pillow_heif.register_heif_opener()
    try:
        img_path = Path(img_path)
        if not img_path.exists():
            print(f"❗ 圖片路徑不存在：{img_path}")
            return None

        suffix = img_path.suffix.lower()
        if suffix in {".heic", ".heif"}:
            print(f"📄 使用 PIL 讀取 HEIC 圖片：{img_path}")
            pil_img = Image.open(img_path).convert("RGB")
            np_img = np.array(pil_img)
            if np_img is None:
                print("⚠️ PIL 無法轉成 numpy")
            return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
        else:
            print(f"📄 使用 OpenCV 讀取圖片：{img_path}")
            img = cv2.imread(str(img_path))
            if img is None:
                print("⚠️ OpenCV 無法讀取此圖片")
            return img
    except Exception as e:
        print(f"❌ 圖片讀取錯誤：{img_path} ➜ {e}")
        return None
