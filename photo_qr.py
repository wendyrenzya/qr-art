"""photo_qr.py | QR foto berwarna dengan titik data yang disamarkan (gaya "kamuflase").

Isi QR tidak diubah sama sekali (aman untuk QRIS). Foto ditampilkan utuh; hanya bagian
tengah tiap modul yang terang-gelapnya digeser seperlunya, relatif terhadap rata-rata
sekitarnya, dengan warna (hue) foto tetap dipertahankan.

Contoh:
  python3 photo_qr.py --data-file qris.txt --image foto.jpg --out hasil.png
  python3 photo_qr.py --data "https://qilo.one" --image logo.png --out hasil.png
"""
import argparse
import numpy as np
import cv2
import qrcode
from qrcode import util
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from PIL import Image, ImageOps, ImageDraw, ImageFilter

ap = argparse.ArgumentParser(description="QR foto kamuflase")
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--data", help="isi QR (teks/URL)")
g.add_argument("--data-file", help="file berisi isi QR (mis. string QRIS)")
ap.add_argument("--image", required=True, help="foto/gambar sumber")
ap.add_argument("--out", required=True, help="file PNG hasil")
ap.add_argument("--ec", default="L", choices="LMQH", help="level koreksi error (default L: QR terkecil, titik terbesar)")
ap.add_argument("--crop", help="potongan foto x,y,ukuran (piksel; boleh negatif, latar diperluas otomatis)")
ap.add_argument("--zoom", type=float, default=1.15, help="perbesaran saat --crop tidak diisi")
ap.add_argument("--cy", type=float, default=0.42, help="posisi vertikal pusat potongan (0..1) saat --crop tidak diisi")
ap.add_argument("--alpha", type=float, default=80, help="selisih kecerahan titik dari rata-rata sekitar")
ap.add_argument("--dark-max", type=float, default=110, help="batas atas kecerahan titik gelap")
ap.add_argument("--light-min", type=float, default=160, help="batas bawah kecerahan titik terang")
ap.add_argument("--dot", type=float, default=0.45, help="diameter titik data (fraksi modul)")
ap.add_argument("--soft", type=float, default=0.25, help="kelembutan tepi titik")
ap.add_argument("--px", type=int, default=36, help="piksel per modul")
ap.add_argument("--square-finders", action="store_true", help="penanda sudut kotak membulat, bukan lingkaran")
a = ap.parse_args()

PAYLOAD = a.data if a.data is not None else open(a.data_file, encoding="utf-8").read().strip()
EC = {"L": ERROR_CORRECT_L, "M": ERROR_CORRECT_M, "Q": ERROR_CORRECT_Q, "H": ERROR_CORRECT_H}[a.ec]
P, B, C = a.px, 4, a.dot
LD, LL = 70, 200          # warna cincin alignment (gelap/terang)
HR, CR = 5.0, 4.0         # radius ruang putih di sekitar penanda sudut, radius sudut kanan-bawah (modul)
NAVY = (14, 16, 24)
lumw = np.array([0.299, 0.587, 0.114], np.float32)

qr = qrcode.QRCode(error_correction=EC, border=0)
qr.add_data(PAYLOAD.encode("utf-8"))
qr.make(fit=True)
m = np.array(qr.get_matrix(), dtype=bool)
n = len(m)
W = (n + 2 * B) * P

# ---------- foto
ph = Image.open(a.image).convert("RGB")
w, h = ph.size
if a.crop:
    x0, y0, s = (int(v) for v in a.crop.split(","))
    pad = Image.new("RGB", (w + 2 * s, h + 2 * s), ph.getpixel((2, 2)))
    pad.paste(ph, (s, s))
    ph, x0, y0 = pad, x0 + s, y0 + s
else:
    s = int(min(w, h) / a.zoom)
    cx, cy = w // 2, int(h * a.cy)
    x0, y0 = max(0, min(cx - s // 2, w - s)), max(0, min(cy - s // 2, h - s))
ph = ph.crop((x0, y0, x0 + s, y0 + s))
ph = ImageOps.autocontrast(ph, cutoff=1)
ph = ph.resize((n * P, n * P), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2, percent=80))
img = np.asarray(ph).astype(np.float32).copy()


def set_lum(block, mode, target):
    """Geser luminansi ke <= target (gelap) atau >= target (terang); hue dipertahankan."""
    L = block @ lumw
    if mode == "dark":
        k = np.where(L > target, target / np.maximum(L, 1), 1.0)
        return block * k[..., None]
    need = np.clip((target - L) / np.maximum(255 - L, 1), 0, 1)
    return block + (255 - block) * need[..., None]


finder = lambda r, c: (r < 8 and c < 8) or (r < 8 and c >= n - 8) or (r >= n - 8 and c < 8)
pos = util.PATTERN_POSITION_TABLE[qr.version - 1]
aligns = [(p, q) for p in pos for q in pos if (p, q) not in ((pos[0], pos[0]), (pos[0], pos[-1]), (pos[-1], pos[0]))]
alignset = {(p + i, q + j) for p, q in aligns for i in range(-2, 3) for j in range(-2, 3)}

# ---------- titik data: relatif ke rata-rata lokal (mirip cara binarizer pemindai)
LOCAL = cv2.blur(img @ lumw, (P * 5, P * 5))
c0 = int(P * (1 - C) / 2)
c1 = P - c0
yy, xx = np.mgrid[0:c1 - c0, 0:c1 - c0]
rr = (c1 - c0) / 2
dist = np.sqrt((yy + 0.5 - rr) ** 2 + (xx + 0.5 - rr) ** 2) / rr
WDISK = np.clip((1.0 - dist) / max(a.soft, 1e-3), 0, 1)
for r in range(n):
    for c in range(n):
        if finder(r, c) or (r, c) in alignset:
            continue
        ys, xs = r * P, c * P
        mode = "dark" if m[r][c] else "light"
        mloc = float(LOCAL[ys + P // 2, xs + P // 2])
        tgt = min(mloc - a.alpha, a.dark_max) if mode == "dark" else max(mloc + a.alpha, a.light_min)
        sub = img[ys + c0:ys + c1, xs + c0:xs + c1]
        new = set_lum(sub, mode, float(np.clip(tgt, 0, 255)))
        sub[:] = sub + (new - sub) * WDISK[..., None]

out = Image.new("RGB", (W, W), "white")
out.paste(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)), (B * P, B * P))

# ---------- bentuk: ruang putih melingkar di sekitar penanda sudut, sudut kanan-bawah membulat
yy2, xx2 = np.mgrid[0:W, 0:W].astype(np.float32)
mx, my = xx2 / P - B, yy2 / P - B
keep = (mx >= 0) & (mx < n) & (my >= 0) & (my < n)
for fx, fy in ((3.5, 3.5), (n - 3.5, 3.5), (3.5, n - 3.5)):
    keep &= (mx - fx) ** 2 + (my - fy) ** 2 > HR * HR
ccx = ccy = n - CR
keep &= ~((mx > ccx) & (my > ccy) & ((mx - ccx) ** 2 + (my - ccy) ** 2 > CR * CR))
arr = np.asarray(out).copy()
arr[~keep] = 255
out = Image.fromarray(arr)
d = ImageDraw.Draw(out)

# ---------- penanda sudut (finder)
for (r0, cc0) in [(0, 0), (0, n - 7), (n - 7, 0)]:
    X, Y = (cc0 + B) * P, (r0 + B) * P
    fx, fy = X + 3.5 * P, Y + 3.5 * P
    if a.square_finders:
        d.rounded_rectangle([X, Y, X + 7 * P - 1, Y + 7 * P - 1], radius=P * 0.8, fill=NAVY)
        d.rounded_rectangle([X + P, Y + P, X + 6 * P - 1, Y + 6 * P - 1], radius=P * 0.5, fill="white")
        d.rounded_rectangle([X + 2 * P, Y + 2 * P, X + 5 * P - 1, Y + 5 * P - 1], radius=P * 0.4, fill=NAVY)
    else:
        for rad, col in ((3.5, NAVY), (2.5, "white"), (1.5, NAVY)):
            d.ellipse([fx - rad * P, fy - rad * P, fx + rad * P, fy + rad * P], fill=col)

# ---------- penanda alignment: cincin bulat berwarna foto di sekitarnya
for p, q in aligns:
    X, Y = (q + B + 0.5) * P, (p + B + 0.5) * P
    region = img[(p - 2) * P:(p + 3) * P, (q - 2) * P:(q + 3) * P]
    avg = region.reshape(-1, 3).mean(0)
    L = float(avg @ lumw)
    dk = tuple(int(v) for v in avg * min(1.0, LD / max(L, 1)))
    lt = tuple(int(v + (255 - v) * max(0.0, (LL + 25 - L) / max(255 - L, 1))) for v in avg)
    for rad, col in ((2.5, dk), (1.5, lt), (0.5, dk)):
        d.ellipse([X - rad * P, Y - rad * P, X + rad * P, Y + rad * P], fill=col)

out.save(a.out)
print(f"{a.out} | versi {qr.version}, {n}x{n} modul, {W}px")
