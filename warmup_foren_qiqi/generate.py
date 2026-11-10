"""
Generator attachment Forensic Warm-up - Qiqi.
Revisi: overlay flag LANGSUNG di atas gambar asli (images (5).jpg), tanpa teks
lain/gimmick apapun. Hasilnya disalin ke dist/ dengan EKSTENSI .pdf (byte isinya
tetap gambar -- peserta harus cek magic bytes buat sadar ini bukan PDF asli).

Jalankan: python generate.py
"""
from PIL import Image, ImageDraw, ImageFont
import shutil
import os

FLAG = "TecFest26{I_PULL3d_A_qIQi_l057_fIf7Y_FiF7Y}"
SRC_IMAGE = "images (5).jpg"

img = Image.open(SRC_IMAGE).convert("RGB")
draw = ImageDraw.Draw(img, "RGBA")
W, H = img.size

try:
    font = ImageFont.truetype("consola.ttf", 20)
except Exception:
    font = ImageFont.load_default()

# Ukur teks supaya box background pas, lalu taruh flag persis di tengah gambar.
bbox = draw.textbbox((0, 0), FLAG, font=font)
text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
pad = 12
box = [
    (W - text_w) / 2 - pad,
    (H - text_h) / 2 - pad,
    (W + text_w) / 2 + pad,
    (H + text_h) / 2 + pad,
]
draw.rectangle(box, fill=(0, 0, 0, 160))
draw.text(((W - text_w) / 2, (H - text_h) / 2 - bbox[1]), FLAG, fill=(255, 255, 255, 255), font=font)

os.makedirs("dist", exist_ok=True)
png_path = "qiqi_overlay.png"
img.save(png_path)

# Salin byte PNG apa adanya, cuma ganti nama ekstensi -> ini intinya challenge.
pdf_disguise = os.path.join("dist", "qiqi_catatan_resep.pdf")
shutil.copyfile(png_path, pdf_disguise)

print(f"PNG asli (author only): {png_path}")
print(f"Attachment peserta    : {pdf_disguise}  (isi sebenarnya PNG)")
