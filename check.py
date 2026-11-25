"""check.py | Uji keterbacaan QR artistik sebelum dicetak.

Dua uji, keduanya membandingkan hasil decode dengan isi yang diharapkan (harus sama persis):
1. galeri : gambar diperkecil (1400..450 px), diburamkan, dikompres JPEG;
2. kamera : simulasi foto HP (miring perspektif, buram, gradasi cahaya, noise, JPEG).
Dekoder: ZXing (zxing-cpp, dipakai banyak aplikasi Android) dan WeChat (OpenCV contrib).

Contoh:
  python3 check.py hasil.png --data-file qris.txt
  python3 check.py hasil.png --data-file hasil.png.txt      # untuk output logo_qr.py
"""
import argparse
import numpy as np
import cv2
import zxingcpp

ap = argparse.ArgumentParser()
ap.add_argument("images", nargs="+")
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--data")
g.add_argument("--data-file")
a = ap.parse_args()
want = a.data if a.data is not None else open(a.data_file, encoding="utf-8").read().strip()
wc = cv2.wechat_qrcode_WeChatQRCode()


def ok(im):
    z = zxingcpp.read_barcodes(im)
    q = wc.detectAndDecode(im)[0]
    return (bool(z) and z[0].text == want), (bool(q) and q[0] == want)


def jpeg(im, q):
    _, e = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.imdecode(e, 1)


def camera(img, size, tilt, blur, seed):
    r = np.random.default_rng(seed)
    h, w = img.shape[:2]
    canvas = np.full((int(h * 1.3), int(w * 1.3), 3), 235, np.uint8)
    o = int(h * 0.15)
    canvas[o:o + h, o:o + w] = img
    H, W = canvas.shape[:2]
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    dst = src + r.uniform(-tilt * W, tilt * W, (4, 2)).astype(np.float32)
    out = cv2.warpPerspective(canvas, cv2.getPerspectiveTransform(src, dst), (W, H), borderValue=(200, 200, 200))
    out = cv2.GaussianBlur(cv2.resize(out, (size, size), interpolation=cv2.INTER_AREA), (0, 0), blur)
    grad = np.linspace(0.75, 1.1, size)[None, :, None]
    out = np.clip(out * grad + r.normal(0, 8, out.shape), 0, 255).astype(np.uint8)
    return jpeg(out, 70)


for f in a.images:
    img = cv2.imread(f)
    gal = [ok(jpeg(cv2.GaussianBlur(cv2.resize(img, (s, s), interpolation=cv2.INTER_AREA), (0, 0), b) if b else
                   cv2.resize(img, (s, s), interpolation=cv2.INTER_AREA), 75))
           for s in (1400, 1000, 800, 600, 450) for b in (0, 1.0, 1.6)]
    cam = [ok(camera(img, s, t, b, k)) for s in (1000, 800, 650) for t in (0.03, 0.06) for b in (0.8, 1.4) for k in range(3)]
    print(f"{f}")
    print(f"  galeri : ZXing {sum(x for x, _ in gal)}/{len(gal)}  WeChat {sum(y for _, y in gal)}/{len(gal)}")
    print(f"  kamera : ZXing {sum(x for x, _ in cam)}/{len(cam)}  WeChat {sum(y for _, y in cam)}/{len(cam)}")
