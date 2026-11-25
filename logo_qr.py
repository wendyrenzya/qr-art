"""logo_qr.py | QR yang logonya TERBENTUK dari modul QR itu sendiri (metode QArt, Russ Cox).

Isi QR = PREFIX + deretan angka "bit bebas". Bit bebas dipilih lewat eliminasi Gauss di GF(2)
supaya modul data mengikuti bentuk logo, dan QR tetap valid TANPA memakai koreksi error.
Hanya untuk isi yang boleh ditambah ekor (mis. URL dengan "#"); BUKAN untuk QRIS.

Contoh:
  python3 logo_qr.py --prefix "https://qilo.one/#" --logo logo.png --out hasil.png --version 18
"""
import argparse, random
import qrcode
from qrcode import util, base
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M
from PIL import Image, ImageDraw, ImageChops

ap = argparse.ArgumentParser(description="QR logo metode QArt")
ap.add_argument("--prefix", required=True, help='awal isi QR, mis. "https://domain/#"')
ap.add_argument("--logo", required=True, help="gambar logo (PNG transparan atau latar putih)")
ap.add_argument("--out", required=True, help="file PNG hasil (isi QR lengkap disimpan di <out>.txt)")
ap.add_argument("--version", type=int, default=18, help="versi QR; 18 cukup untuk logo + tulisan, 12 untuk simbol saja")
ap.add_argument("--ec", default="L", choices="LM")
ap.add_argument("--palette", help='warna pengganti warna logo, mis. "#1f4fd1,#c8102e"; tiap bagian logo memakai warna palet dengan hue terdekat')
ap.add_argument("--bg-color", default="#0f1f3a", help="warna titik QR di luar logo (default navy)")
a = ap.parse_args()
PREFIX, VERSION, OUT, LOGO = a.prefix, a.version, a.out, a.logo
LEVEL = {"L": ERROR_CORRECT_L, "M": ERROR_CORRECT_M}[a.ec]
random.seed(7)

n = VERSION * 4 + 17

# ---------- modul fungsi (tidak bisa diatur)
fn = [[False] * n for _ in range(n)]


def mark(r0, r1, c0, c1):
    for r in range(max(r0, 0), min(r1, n - 1) + 1):
        for c in range(max(c0, 0), min(c1, n - 1) + 1):
            fn[r][c] = True


mark(0, 8, 0, 8); mark(0, 8, n - 8, n - 1); mark(n - 8, n - 1, 0, 8)
for i in range(n):
    fn[6][i] = True; fn[i][6] = True
pos = util.PATTERN_POSITION_TABLE[VERSION - 1]
for r in pos:
    for c in pos:
        if (r, c) in ((pos[0], pos[0]), (pos[0], pos[-1]), (pos[-1], pos[0])):
            continue
        mark(r - 2, r + 2, c - 2, c + 2)
if VERSION >= 7:
    mark(0, 5, n - 11, n - 9); mark(n - 11, n - 9, 0, 5)

order = []
col, up = n - 1, True
while col > 0:
    if col == 6:
        col -= 1
    for r in (range(n - 1, -1, -1) if up else range(n)):
        for dc in (0, 1):
            if not fn[r][col - dc]:
                order.append((r, col - dc))
    up = not up
    col -= 2

# ---------- tata letak data: segmen byte (URL) + segmen numerik (bit bebas)
blocks = base.rs_blocks(VERSION, LEVEL)
D = sum(b.data_count for b in blocks)
T = sum(b.total_count for b in blocks)
cap = D * 8
byte_cnt_bits = 8 if VERSION < 10 else 16
num_cnt_bits = 10 if VERSION < 10 else (12 if VERSION < 27 else 14)
used = 4 + byte_cnt_bits + 8 * len(PREFIX) + 4 + num_cnt_bits
G = (cap - used) // 10          # jumlah grup 3 digit
NFREE = G * 9                   # bit teratas tiap grup = 0 supaya nilai <= 511


def digits_of(vals):
    return "".join(str(v).zfill(3) for v in vals)


# GF(256) + Reed-Solomon sendiri
EXP = [0] * 512; LOG = [0] * 256
x = 1
for i in range(255):
    EXP[i] = x; LOG[x] = i
    x <<= 1
    if x & 0x100:
        x ^= 0x11d
for i in range(255, 512):
    EXP[i] = EXP[i - 255]


def gmul(a, b):
    return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]


GEN = {}


def gen(k):
    if k not in GEN:
        g = [1]
        for i in range(k):
            g2 = [0] * (len(g) + 1)
            for j, co in enumerate(g):
                g2[j] ^= co
                g2[j + 1] ^= gmul(co, EXP[i])
            g = g2
        GEN[k] = g
    return GEN[k]


def rs(data, k):
    g = gen(k)
    rem = list(data) + [0] * k
    for i in range(len(data)):
        co = rem[i]
        if co:
            for j in range(1, len(g)):
                rem[i + j] ^= gmul(g[j], co)
    return rem[len(data):]


def stream(vals):
    bits = "0100" + format(len(PREFIX), "0%db" % byte_cnt_bits) + "".join(format(ch, "08b") for ch in PREFIX.encode())
    bits += "0001" + format(3 * len(vals), "0%db" % num_cnt_bits) + "".join(format(v, "010b") for v in vals)
    bits += "0" * min(4, cap - len(bits))
    bits += "0" * ((8 - len(bits) % 8) % 8)
    data = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
    pad = [0xEC, 0x11]
    while len(data) < D:
        data.append(pad[(len(data) - len(bits) // 8) % 2])
    dblocks, eblocks, o = [], [], 0
    for b in blocks:
        chunk = data[o:o + b.data_count]; o += b.data_count
        dblocks.append(chunk); eblocks.append(rs(chunk, b.total_count - b.data_count))
    cw = []
    for i in range(max(len(x) for x in dblocks)):
        for x in dblocks:
            if i < len(x): cw.append(x[i])
    for i in range(max(len(x) for x in eblocks)):
        for x in eblocks:
            if i < len(x): cw.append(x[i])
    s = 0
    for b in cw:
        s = (s << 8) | b
    return s, len(cw) * 8


base_vals = [0] * G
s0, L = stream(base_vals)
assert L == T * 8


def bitpos(i):          # posisi bit ke-i (dari depan) di integer stream
    return L - 1 - i


# A[p] = bitmask variabel bebas yang mempengaruhi bit stream ke-p
A = [0] * L
for g in range(G):
    for j in range(9):
        vals = base_vals[:]
        vals[g] = 1 << j
        s, _ = stream(vals)
        diff = s ^ s0
        k = g * 9 + j
        while diff:
            low = diff & -diff
            b = low.bit_length() - 1
            A[L - 1 - b] |= 1 << k
            diff ^= low
base_bit = [(s0 >> bitpos(i)) & 1 for i in range(L)]

# ---------- target dari logo
lg = Image.open(LOGO).convert("RGBA")
flat = Image.new("RGBA", lg.size, (255, 255, 255, 255)); flat.alpha_composite(lg); flat = flat.convert("RGB")
flat = flat.crop(ImageChops.difference(flat, Image.new("RGB", flat.size, "white")).getbbox())
inner = n - 2   # logo memenuhi hampir seluruh area
sc = inner * 8 / max(flat.size)  # perbesar/perkecil agar logo memenuhi area (thumbnail tidak bisa memperbesar)
flat = flat.resize((max(1, round(flat.width * sc)), max(1, round(flat.height * sc))), Image.LANCZOS)
canvas = Image.new("RGB", (n * 8, n * 8), "white")
canvas.paste(flat, ((n * 8 - flat.width) // 2, (n * 8 - flat.height) // 2))
mod = canvas.resize((n, n), Image.BOX)
ink = [[(1 - min(mod.getpixel((c, r))) / 255) > 0.3 for c in range(n)] for r in range(n)]


def edge(r, c):
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < n and 0 <= cc < n and ink[rr][cc] != ink[r][c]:
            return True
    return False


def solve(mask_id):
    mf = util.mask_func(mask_id)
    pri = []
    for i in range(L):
        r, c = order[i]
        if edge(r, c):
            p = 0
        elif ink[r][c]:
            p = 1
        else:
            near = any(ink[rr][cc] for rr in range(max(0, r - 2), min(n, r + 3)) for cc in range(max(0, c - 2), min(n, c + 3)))
            p = 2 if near else 3
        pri.append((p, random.random(), i))
    pri.sort()
    piv = {}
    hit = 0
    for _, _, i in pri:
        r, c = order[i]
        want = 1 if ink[r][c] else 0
        rhs = want ^ base_bit[i] ^ (1 if mf(r, c) else 0)
        row = A[i]
        while row:
            b = (row & -row).bit_length() - 1
            if b in piv:
                prow, prhs = piv[b]
                row ^= prow; rhs ^= prhs
            else:
                break
        if row:
            piv[b] = (row, rhs)
            hit += 1
        elif rhs == 0:
            hit += 1
    X = 0
    for b in sorted(piv, reverse=True):
        row, rhs = piv[b]
        v = rhs ^ (bin((row & ~(1 << b)) & X).count("1") & 1)
        if v:
            X |= 1 << b
    return X, hit


best = None
for mid in range(8):
    X, hit = solve(mid)
    if best is None or hit > best[1]:
        best = (X, hit, mid)
X, hit, MASK = best
vals = [sum(((X >> (g * 9 + j)) & 1) << j for j in range(9)) for g in range(G)]
text = PREFIX + digits_of(vals)

# ---------- bangun QR asli dengan library, lalu cek cocok dengan prediksi
qr = qrcode.QRCode(version=VERSION, error_correction=LEVEL, border=0, mask_pattern=MASK)
qr.add_data(util.QRData(PREFIX.encode(), mode=util.MODE_8BIT_BYTE))
qr.add_data(util.QRData(digits_of(vals), mode=util.MODE_NUMBER))
qr.make(fit=False)
m = qr.get_matrix()
match = sum(1 for (r, c) in order[:L] if m[r][c] == ink[r][c])
print(f"v{VERSION} n={n} bebas={NFREE} mask={MASK} cocok={match}/{L} ({100*match/L:.0f}%)")

# ---------- render
import colorsys

NAVY = (15, 31, 58); EYE = (0, 85, 215)
hexrgb = lambda h: tuple(int(h.strip().lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
lumof = lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
BG = hexrgb(a.bg_color)
PALETTE = [hexrgb(x) for x in a.palette.split(",")] if a.palette else []
for col in PALETTE + [BG]:
    if lumof(col) > 110:
        print(f"PERINGATAN: warna {col} terlalu terang (luminansi {lumof(col):.0f} > 110); pemindai bisa gagal")
hue = lambda c: colorsys.rgb_to_hsv(*(v / 255 for v in c))[0]
P, B = 20, 4
W = (n + 2 * B) * P
img = Image.new("RGB", (W, W), "white")
d = ImageDraw.Draw(img)


def circle(cx, cy, rad, col):
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=col)


def color_at(r, c):
    R, Gc, Bc = mod.getpixel((c, r))
    if min(R, Gc, Bc) > 230:
        return BG
    if PALETTE:
        h0 = hue((R, Gc, Bc))
        return min(PALETTE, key=lambda p: min(abs(hue(p) - h0), 1 - abs(hue(p) - h0)))
    lum = 0.299 * R + 0.587 * Gc + 0.114 * Bc
    k = min(1.0, 95 / max(lum, 1))
    return (int(R * k), int(Gc * k), int(Bc * k))


corner = lambda r, c: (r < 8 and c < 8) or (r < 8 and c >= n - 8) or (r >= n - 8 and c < 8)
for r in range(n):
    for c in range(n):
        if corner(r, c) or not m[r][c]:
            continue
        circle((c + B + .5) * P, (r + B + .5) * P, P * 0.47, color_at(r, c))
for (r0, c0) in [(0, 0), (0, n - 7), (n - 7, 0)]:
    cx, cy = (c0 + B + 3.5) * P, (r0 + B + 3.5) * P
    circle(cx, cy, 3.5 * P, NAVY); circle(cx, cy, 2.5 * P, "white"); circle(cx, cy, 1.5 * P, EYE)
img.save(OUT)
open(OUT + ".txt", "w").write(text)
print(OUT, W, "len teks", len(text))
