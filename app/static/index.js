// 獲取 DOM 元素
const uploadInput = document.getElementById('uploadInput');
const customFileButton = document.getElementById('customFileButton');
const fileInput = document.getElementById('fileInput');

customFileButton.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];  // 獲取選擇的圖片文件
    if (file) {
        // 讀取圖片文件
        const reader = new FileReader();
        reader.onload = async function(e) {
            const imageData = e.target.result;  // 轉換為 base64 格式的圖片數據
            // 將圖片發送到後端進行辨識
            Detection(imageData);
        };

        // 開始讀取圖片
        reader.readAsDataURL(file);
    } else {
        alert('請選擇一張圖片！');
    }
});

// 上傳按鈕事件處理
uploadInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const base64Image = e.target.result;
            Detection(base64Image);  // 調用上傳函數
        };
        reader.readAsDataURL(file);  // 讀取檔案並轉換為 base64
    } else {
        console.error('No file selected');
    }
});


async function Detection(imageData) {
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });

        const responseData = await response.text();
        let result;
        try {
            const parsedData = JSON.parse(responseData);  // 解析回應
            result = parsedData.result;  // 提取 result 部分
        } catch (error) {
            alert('Error parsing JSON: ' + error.message);  // 顯示解析錯誤
            return;
        }

        if (result && result.name) {
            const symptoms = Array.isArray(result.symptoms) ? result.symptoms.join(', ') : result.symptoms || '無資料';
            const precautions = Array.isArray(result.precautions) ? result.precautions.join(', ') : result.precautions || '無資料';
            const sideEffects = Array.isArray(result.side_effects) ? result.side_effects.join(', ') : result.side_effects || '無資料';
            const message = `
                藥品學名：${result.name}
                適應症狀：${symptoms}
                注意事項：${precautions}
                副作用：${sideEffects}
            `;
            alert(message);
        } else {
            alert('辨識失敗，未找到藥品資訊。');
        }

        if (result.processed_image) {
            const processedImage = new Image();
            processedImage.src = result.processed_image;
            document.body.appendChild(processedImage);
        }
    } catch (error) {
        alert('Error processing image: ' + error.message);  // 顯示錯誤訊息
    }
}