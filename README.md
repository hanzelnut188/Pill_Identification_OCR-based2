# AI-Based Pill Image Recognition System

This project implements an AI-driven pill image recognition system capable of identifying medications based on **OCR text extraction**, **YOLO-based shape detection**, and **HSV-based color analysis**.  
It is designed to assist users—especially elderly patients—in quickly and safely identifying pills from images.

---

## 🔧 Features
- **OCR text extraction** (OpenOCR / Tesseract)
- **YOLOv8 pill shape detection**
- **Color detection using HSV + K-Means**
- **Multi-modal fusion** of text, shape, and color
- **Flask-based web interface**
- Supports PNG, JPEG, HEIC input images

---

## 📌 Requirements
This project **must be run on Python 3.10**.

Recommended environment setup:

```sh
conda create -n pill_env python=3.10
conda activate pill_env
```

## 📦 Installation
1. Install all required dependencies:

```sh
pip install -r requirements.txt
```
2. Run the Flask backend:

```sh
python main.py
```

## 👥 Authors
- **Shanzelig Putra Wijaya**  
- **Rushikesh Sontakke**
- **黃至曄**
