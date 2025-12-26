# --- 1. 準備 ---
!wget -q https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml
import cv2
import os
import numpy as np
from PIL import Image

# --- 2. 設定 ---
INPUT_IMAGE_FILE = "Image_fx - 2025-11-10T132107.643.jpg"  # 画像ファイル名

# --- 3. 改良版OpenCVリサイズ関数 ---
def opencv_smart_resize_v2(image_path, target_width, target_height):
    if not os.path.exists(image_path):
        print(f"❌ 画像なし: {image_path}")
        return

    # OpenCVで読み込み
    img_cv = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    orig_w, orig_h = pil_img.size
    
    print(f"\n--- {target_width}x{target_height} 処理開始 (OpenCV V2) ---")

    # 顔認識
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    center_x, center_y = orig_w / 2, orig_h / 2 # デフォルトは画像の中心

    if len(faces) > 0:
        print(f"👀 顔を {len(faces)} つ発見。全体の中心を計算します。")
        # 全ての顔を含むバウンディングボックスを計算
        min_x = np.min(faces[:, 0])
        min_y = np.min(faces[:, 1])
        max_x = np.max(faces[:, 0] + faces[:, 2])
        max_y = np.max(faces[:, 1] + faces[:, 3])
        
        # そのボックスの中心点を求める
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
    else:
        print("👀 顔が見つかりませんでした。画像の中央を使います。")

    # --- ここからリサイズ処理 ---
    # 1. カバー戦略でリサイズ倍率を決定
    scale = max(target_width / orig_w, target_height / orig_h)
    resized_w, resized_h = int(orig_w * scale), int(orig_h * scale)
    img_resized = pil_img.resize((resized_w, resized_h), Image.LANCZOS)
    
    # 2. 中心座標もリサイズ後の世界に合わせて計算
    center_x_scaled = center_x * scale
    center_y_scaled = center_y * scale
    
    # 3. 切り抜く左上の座標を計算
    left = center_x_scaled - (target_width / 2)
    top = center_y_scaled - (target_height / 2)
    
    # 4. 画像からはみ出さないように補正（クランプ処理）
    # ここが重要：計算上の中心が端すぎると、強制的に端に寄せられます
    left = max(0, min(left, resized_w - target_width))
    top = max(0, min(top, resized_h - target_height))
    
    # 5. クロップ実行
    final_img = img_resized.crop((left, top, left + target_width, top + target_height))
    
    save_name = f"cv2_{target_width}x{target_height}.jpg"
    final_img.save(save_name)
    print(f"✅ 保存完了: {save_name}")

# --- 4. 実行 ---
targets = [
    (1080, 1080),
    (1920, 1080),
    (600, 400)
]

for w, h in targets:
    opencv_smart_resize_v2(INPUT_IMAGE_FILE, w, h)