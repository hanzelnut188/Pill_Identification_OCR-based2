import easyocr
from rembg import remove
import argparse
import cv2
import numpy as np


def process_image(image_path):

    # 載入圖片、轉換為灰階並稍微模糊
    ori = image_path
    rem_ori = image_path + "_removed"

    # 造一個新的OCR reader.
    reader = easyocr.Reader(["en"])

    # Step 1: 進行去背
    # 讀取圖片並去除背景
    input_img = cv2.imread(ori)
    rembg_img = remove(input_img)

    # 檢查圖片是否有alpha通道（透明度）
    if rembg_img.shape[2] == 4:
        alpha_channel = rembg_img[:, :, 3]

        # 對 alpha 通道進行輕微模糊，減少噪點的影響
        alpha_channel = cv2.GaussianBlur(alpha_channel, (5, 5), 0)

        # 建立一個遮罩，將透明度大於門檻值的像素視為非透明區域
        _, mask = cv2.threshold(alpha_channel, 50, 255, cv2.THRESH_BINARY)

        # 找出非透明區域的輪廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 取得最大輪廓的邊界框（或前幾大輪廓的合併範圍）
        if contours:
            # 根據面積排序輪廓，只保留最大的一個
            contours = sorted(contours, key=cv2.contourArea, reverse=True)

            # 使用最大輪廓來計算邊界框
            x, y, w, h = cv2.boundingRect(contours[0])

            # 將影像裁切至該邊界框
            cropped_img = rembg_img[y : y + h, x : x + w]

            # 儲存裁切後的影像
            cv2.imwrite(rem_ori, cropped_img)
        else:
            print("No non-transparent regions found.")
    else:
        print("The image does not have an alpha channel.")

    # Step 2: 先進行影像增強處理再使用easyOCR辨識文字
    # 初始化陣列以提供待會儲存辨識出的文字
    processed_bounds = []

    def enhance_contrast(img, clip_limit, alpha, beta):
        # 轉換到 LAB 色彩空間並分離通道
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        # 應用 CLAHE 到 L 通道
        clahe = cv2.createCLAHE(clip_limit, (8, 8))
        cl = clahe.apply(l_channel)
        # 合併 CLAHE 增強的 L 通道與 a 和 b 通道
        limg = cv2.merge((cl, a, b))
        # 將增強的 LAB 圖像轉換回 BGR 色彩空間
        enhance_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        # 使用高斯模糊
        blurred = cv2.GaussianBlur(enhance_img, (91, 91), 100)
        # 創建遮罩並合併
        return cv2.addWeighted(enhance_img, alpha, blurred, beta, 0)

    def desaturate_image(img):
        # 將增強對比度的圖片轉換為 HSV 色彩空間並調整飽和度
        hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv_img)
        s.fill(0)  # 將飽和度設置為 0
        return cv2.cvtColor(cv2.merge([h, s, v]), cv2.COLOR_HSV2BGR)

    def process_bounds(img):
        # 處理 OCR 結果，將文字格式化
        bounds = reader.readtext(img, detail=0)
        print(bounds)
        for bound in bounds:
            bound = (
                bound.upper()
                .replace(" ", "")
                .replace("-", "")
                .replace("_", "")
                .replace("!", "")
                .replace("'", "")
                .replace("O", "0")
            )
            processed_bounds.append(bound)

    # 主程式流程，共生成4種處理後的影像
    final_img_1 = enhance_contrast(cropped_img, 1.5, 1.5, -0.5)
    final_img_2 = desaturate_image(final_img_1)
    final_img_3 = enhance_contrast(cropped_img, 5.5, 2.0, -1.0)
    final_img_4 = desaturate_image(final_img_3)

    # 處理文字格式化並合併
    process_bounds(final_img_1)
    process_bounds(final_img_2)
    process_bounds(final_img_3)
    process_bounds(final_img_4)
    print(processed_bounds)

    # Step 3: 藥品判斷系統
    def identify(texts=[], colors=[], shape="N/A"):
        if ("CM" or "CC06") in texts:
            return [
                "text medicine",
                "none",
                "none",
                "none",
            ]
        if ("511" in texts) or (
            ("Yellow" in colors) and ("Black" in colors) and (shape == "capsule")
        ):
            return [
                "Soma Capsules",
                "關節、神經肌肉等疼痛之緩解",
                "1.使用本藥品後，代謝物可能引起尿液變色（罕見）。此為正常藥效作用反應，請按時服藥。2.本藥服用後可能會想睡覺，請多加注意。",
                "暈眩、視覺模糊、嘔吐、緊張不安、頭昏等。",
            ]
        if ("128" in texts) or (("Pink" in colors) and (shape == "circle")):
            return [
                "Diclofenac Potassium",
                "鎮痛、消炎劑（退燒解熱）",
                "使用本品可能發生罕見但嚴重之皮膚不良/過敏反應，如用藥後發生喉痛、口腔/黏膜潰爛、皮疹等症狀，應考慮可能為藥品不良反應，宜立即就醫並考慮停藥。",
                "眩暈、胃腸道不適、過敏症狀等等，以上大約(1%-10%)發生率。",
            ]
        if (("CH" or "33" or "HJ") in texts) or (
            ("White" in colors) and (shape == "circle")
        ):
            return [
                "Famotidine",
                "胃潰瘍、十二指腸潰瘍、胃食道逆流症",
                "本品會降低某些抗黴菌藥之療效。",
                "便秘、腹瀉、頭痛、暈眩",
            ]
        if (("NYR" or "NY" or "MY" or "MR") in texts) or (
            ("Yellow" in colors) and (shape == "circle")
        ):
            return [
                "Exforge",
                "治療高血壓",
                "1.服藥期間應避免使用葡萄柚及其相關食品，以免交互作用發生。2.高血壓且懷孕之婦女不建議使用本藥。",
                "低血壓(<1%)、周邊水腫(5.4%)、眩暈(2.1%)、鼻咽炎(4.3%)、上呼吸道感染(2.9%)發生率。",
            ]
        if (("ST" or "427" or "51") in texts) or (
            ("White" in colors) and (shape == "capsule")
        ):
            return [
                "Gliclazide MR",
                "降血糖藥",
                "1.本品為持續性藥效錠， 不可以磨粉但可剝半。2.請勿和酒精一起使用。3.和苦瓜併用會增加降血糖作用,導致低血糖發生,必要時要監測血糖值。4.高警訊藥品",
                "下痢，噁心嘔吐，偏頭痛，疲倦，腹痛等等，以上大約(0.1%-1%) 發生率。",
            ]
        if (("MB,S0E" or "MB50" or "MB50E" or "MBS0E" or "MB50=") in texts) or (
            ("Red" in colors) and (shape == "capsule")
        ):
            return [
                "Mecobalamin",
                "維生素B12、改善末梢性神經障礙",
                "室溫避光保存",
                "厭食、噁心、嘔吐、下痢等等，以上大約(0.1%-5%) 發生率。",
            ]
        if (("CTA23" or "GTA23" or "GTA231" or "CTA231") in texts) or (
            ("Red" in colors) and (shape == "capsule")
        ):
            return [
                "Silymarin",
                "慢性肝病，肝硬變及脂肪肝之佐藥",
                "服藥期間有任何問題，請打用藥諮詢專線",
                "偶而有輕瀉或利尿的作用。",
            ]
        if (("20" or "ATV") in texts) or (("White" in colors) and (shape == "circle")):
            return [
                "atorvastatin",
                "降血脂藥、高膽固醇血症、高三酸甘油脂血症",
                "不可與葡萄柚汁同時服用",
                "胸痛、噁心、鼻咽炎、關節炎、周邊水腫等等，以上大約(2%) 發生率。",
            ]
        if (("S10PHUT" or "SHNPHAR" or "S1NPHAT") in texts) or (
            ("White" in colors) and (shape == "capsule")
        ):
            return [
                "Acetaminophen",
                "退燒、止痛",
                "1.建議一天(24小時)使用劑量不要超過4000毫克。2.服藥期間請勿喝酒或酒精類飲料",
                "發疹、發紅、噁心、嘔吐、食慾不振、頭暈等等，以上大約(1-10%)左右。",
            ]
        if (("VPC" or "PC" or "VR" or "44" or "445") in texts) or (
            ("White" in colors) and (shape == "circle")
        ):
            return [
                "MAGnesium Oxide",
                "軟便、緩解胃部不適或灼熱感、或胃炎、食道炎所伴隨之胃酸過多",
                "服藥期間有任何問題, 請打用藥諮詢專線",
                "輕微腹瀉",
            ]
        if (("39" or "89" or "68" or "EEP" or "ECP") in texts) or (
            ("White" in colors) and (shape == "capsule")
        ):
            return [
                "Metformin HCL",
                "降血糖藥",
                "1.請依醫師指示按時服用。2.和苦瓜併用會增加降血糖作用,導致低血糖發生,必要時要監測血糖值。",
                "下痢、消化不良、脹氣、噁心嘔吐等。",
            ]
        if (("STD" or "28" or "8" or "12") in texts) or (
            ("Pink" in colors) and (shape == "capsule")
        ):
            return [
                "Diphenidol Hcl",
                "眩暈症候群",
                "可能會有口乾、便秘及減少出汗等情形，可適度補充水分以緩解不適。",
                "口渴，胸部灼熱感，散瞳等等→以上大約(0.1%-1%) 發生率。",
            ]
        else:
            return False

    # Step 4: 透過辨識出來的編號判斷是否有對應藥品，若有則程式直接結束
    result = identify(processed_bounds)

    if result:
        name = result[0]  # 假設 result[0] 是藥品名稱
        symptoms = result[1]  # 假設 result[1] 是適應症狀
        precautions = (
            result[2].split(";") if isinstance(result[2], str) else []
        )  # 假設注意事項以分號分隔
        side_effects = (
            result[3].split(";") if isinstance(result[3], str) else []
        )  # 假設副作用以分號分隔

        print(
            "藥品學名："
            + name
            + "\n適應症狀："
            + symptoms
            + "\n注意事項："
            + "\n- ".join(precautions)
            + "\n副作用："
            + "\n- ".join(side_effects)
        )
        print("\n辨識成功，結束執行！")

        # 根據 result 的內容生成 JSON 物件
        result_data = {
            "name": name,
            "symptoms": symptoms,
            "precautions": precautions,  # 確保 precautions 是 list
            "side_effects": side_effects,  # 確保 side_effects 是 list
        }
        return result_data  # 返回動態生成的結果

    # Step 5: 若沒有成功對應到藥品編號則開始辨識顏色跟形狀
    # 載入圖片
    image = cv2.imread(rem_ori)
    # image = cv2.imread("/content/drive/MyDrive/removed/IMG_7037.jpg")

    # 將圖片轉換為HSV色彩空間
    hsvFrame = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 定義不同顏色的範圍並建立掩膜（array順序：BGR）

    pink_mask = cv2.inRange(
        hsvFrame, np.array([50, 50, 150], np.uint8), np.array([250, 250, 255], np.uint8)
    )
    red_mask = cv2.inRange(
        hsvFrame, np.array([0, 50, 50], np.uint8), np.array([10, 170, 200], np.uint8)
    )

    # 黃色
    yellow_mask = cv2.inRange(
        hsvFrame, np.array([15, 200, 200], np.uint8), np.array([30, 255, 255], np.uint8)
    )

    # 黑色
    black_mask = cv2.inRange(
        hsvFrame, np.array([2, 2, 2], np.uint8), np.array([50, 50, 50], np.uint8)
    )

    # 白色
    white_mask = cv2.inRange(
        hsvFrame,
        np.array([200, 200, 150], np.uint8),
        np.array([255, 255, 255], np.uint8),
    )

    # 定義 kernel 並應用形態學操作
    kernel = np.ones((5, 5), "uint8")

    # Dilation 操作
    red_mask = cv2.dilate(red_mask, kernel)
    pink_mask = cv2.dilate(pink_mask, kernel)
    yellow_mask = cv2.dilate(yellow_mask, kernel)
    black_mask = cv2.dilate(black_mask, kernel)
    white_mask = cv2.dilate(white_mask, kernel)

    # Bitwise_and 運算
    res_red = cv2.bitwise_and(image, image, mask=red_mask)
    res_pink = cv2.bitwise_and(image, image, mask=pink_mask)
    res_yellow = cv2.bitwise_and(image, image, mask=yellow_mask)
    res_black = cv2.bitwise_and(image, image, mask=black_mask)
    res_white = cv2.bitwise_and(image, image, mask=white_mask)

    # 定義顏色辨識的輪廓並列出主顏色
    main_color = []

    def detect_color(mask, color_name, image, box_color):
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 10000:
                main_color.append(color_name)
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(image, (x, y), (x + w, y + h), box_color, 2)
                cv2.putText(
                    image, color_name, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, box_color
                )

    # 辨識顏色
    detect_color(red_mask, "Red", image, (0, 0, 255))
    detect_color(pink_mask, "Pink", image, (100, 100, 255))
    detect_color(yellow_mask, "Yellow", image, (0, 255, 255))
    detect_color(black_mask, "Black", image, (0, 165, 255))
    detect_color(white_mask, "White", image, (255, 255, 255))

    # 顯示結果
    # cv2.imshow("after", image)
    # cv2.waitKey(0)  # Wait for a key press
    # cv2.destroyAllWindows()  # Close all windows

    # 辨識形狀
    # 載入已去背處理過的圖片（帶透明背景的圖像）
    image = cv2.imread(rem_ori, cv2.IMREAD_UNCHANGED)
    # image = cv2.imread("/content/drive/MyDrive/removed/IMG_6934.jpg", cv2.IMREAD_UNCHANGED)

    # 確保圖像是 RGB 或 RGBA 格式，將其轉換為灰階
    if image.shape[2] == 4:  # 如果是 RGBA
        # 忽略透明通道，轉換為灰階
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        # 如果是 RGB，直接轉換為灰階
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 高斯模糊來減少雜訊
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # 將圖片轉換為二值化圖像
    _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)

    # 找出輪廓
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 假設只需要辨識最大的輪廓
    if contours:
        c = max(contours, key=cv2.contourArea)

        # 計算周長並近似多邊形
        peri = cv2.arcLength(c, True)

        # 調整這個值來控制精度
        approx = cv2.approxPolyDP(c, 0.0225 * peri, True)

        # 計算外接矩形的長寬比
        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = w / float(h)

    # 辨識形狀
    if len(approx) == 8:
        shape = "capsule"  # 辨識八邊型
    elif 0.2 < aspect_ratio < 0.5:  # 一個合理的膠囊形狀長寬比範圍
        shape = "capsule"  # 辨識膠囊形狀
    elif len(approx) > 8:
        shape = "circle"  # 辨識圓形
    else:
        shape = "unidentified"

    # Step 6: 透過辨識出來的顏色和形狀判斷是否有對應藥品，若有則程式直接結束
    result = identify([], main_color, shape)
    if result:
        print(
            "藥品學名："
            + result[0]
            + "\n適應症狀："
            + result[1]
            + "\n注意事項："
            + result[2]
            + "\n副作用："
            + result[3]
        )
        print("\n辨識成功，結束執行！")

        # 將資訊轉換為 JSON 格式
        result_data = {
            "name": result[0],  # 藥品學名
            "symptoms": result[1],  # 適應症狀
            "precautions": (
                result[2].split(";") if isinstance(result[2], str) else []
            ),  # 注意事項轉為列表
            "side_effects": (
                result[3].split(";") if isinstance(result[3], str) else []
            ),  # 副作用轉為列表
        }
        return result_data  # 返回 JSON 物件

    return True
