# qr-art

Alat untuk membuat QR code artistik yang gambarnya **terbentuk dari titik-titik QR itu sendiri**, bukan logo yang ditempel di tengah. Ada dua mode:

| Skrip | Untuk | Cara kerja | Isi QR |
|---|---|---|---|
| `logo_qr.py` | Logo / grafis sederhana, isi berupa URL | QArt (Russ Cox): bit data bebas diatur lewat eliminasi Gauss sehingga modul membentuk logo | URL + ekor angka setelah `#` |
| `photo_qr.py` | Foto berwarna, isi apa saja **termasuk QRIS** | Foto utuh, hanya titik tengah tiap modul yang terang-gelapnya digeser seperlunya (kamuflase) | Tidak diubah sama sekali |
| `check.py` | Semua hasil | Uji decode galeri + simulasi kamera HP dengan ZXing dan WeChat | |

Contoh hasil `logo_qr.py`: [`examples/logo-qart-qilo-one.png`](examples/logo-qart-qilo-one.png) (warna logo asli) dan [`examples/logo-qart-kosewa-warna.png`](examples/logo-qart-kosewa-warna.png) (warna diganti lewat `--palette`).

## Instalasi

```bash
pip install -r requirements.txt
# Jika sudah ada opencv-python-headless biasa, hapus dulu (bentrok dengan versi contrib):
pip uninstall -y opencv-python-headless && pip install opencv-contrib-python-headless
```

## Cara pakai

### 1. QR logo (isi URL)

```bash
python3 logo_qr.py --prefix "https://qilo.one/#" --logo logo.png --out qr-logo.png --version 18
python3 check.py qr-logo.png --data-file qr-logo.png.txt
```

- `--version 18` (89x89 modul) cukup untuk simbol + tulisan. Versi 12 hanya cukup untuk simbol.
- Isi QR yang sebenarnya disimpan di `qr-logo.png.txt`: URL diikuti deretan angka panjang setelah `#`. Browser mengabaikan bagian setelah `#`, jadi yang terbuka tetap URL-nya.
- Logo terbaik: kontras tinggi, bentuk sederhana, latar transparan/putih.
- Level koreksi error L, jadi cetak minimal sekitar 4 cm.

#### Mengatur warna logo (`--palette`, `--bg-color`)

Secara default warna titik diambil dari warna logo, lalu digelapkan seperlunya supaya tetap terbaca, dan titik di luar logo berwarna navy. Masalahnya, logo yang warnanya sudah gelap (mis. navy `#0a2146`) jadi hampir hitam dan menyatu dengan titik QR di sekitarnya, sehingga logo tidak menonjol. Untuk itu ada dua opsi:

```bash
python3 logo_qr.py --prefix "https://kosewa.com/#" --logo logo-kosewa.png --out qr-kosewa.png \
  --version 18 --palette "#1f4fd1,#c8102e" --bg-color "#343842"
```

- `--palette`: daftar warna pengganti, dipisah koma. Tiap bagian logo memakai warna palet yang hue-nya paling dekat dengan warna aslinya (contoh di atas: navy diganti biru cerah, merah marun diganti merah cerah). Bagian logo yang hampir tak berwarna (hitam/abu) ikut dicocokkan ke hue terdekat, jadi untuk logo hitam cukup beri satu warna.
- `--bg-color`: warna titik QR di luar logo. Pilih warna netral (abu gelap) yang berbeda dari warna logo, supaya logo terlihat sebagai bentuk tersendiri.

**Aturan memilih warna:**

- Titik QR adalah modul "gelap", jadi semua warna palet dan `--bg-color` harus cukup gelap dibanding latar putih. Patokannya luminansi `0.299R + 0.587G + 0.114B` **maksimal sekitar 100** (skrip memberi PERINGATAN di atas 110).
- Contoh aman: biru `#1f4fd1` (±79), merah `#c8102e` (±74), hijau `#1b7f3a` (±89), ungu `#6b2fb3` (±80), abu `#343842` (±56).
- Hindari kuning, oranye terang, hijau muda, pink, dan pastel: luminansinya terlalu tinggi, pemindai melihatnya sebagai "putih".
- Penanda sudut tetap navy dengan titik biru, supaya selalu kontras.
- Setelah ganti warna, selalu jalankan `check.py`. Untuk contoh kosewa di atas: galeri 15/15 (ZXing dan WeChat), simulasi kamera ZXing 33/36 dan WeChat 30/36, setara versi warna asli (32/36 dan 31/36).

### 2. QR foto (termasuk QRIS)

**a. Ambil isi QRIS** dari screenshot QRIS asli:

```bash
python3 -c "import zxingcpp,cv2;print(zxingcpp.read_barcodes(cv2.imread('qris.png'))[0].text)" > qris.txt
```

Isi QRIS diakhiri checksum CRC (tag `63`). Jangan diubah satu karakter pun.

**b. Buat QR-nya:**

```bash
python3 photo_qr.py --data-file qris.txt --image foto.jpg --out qris-foto.png
```

**c. Atur potongan foto** supaya wajah tidak tertutup cincin penanda:

```bash
python3 photo_qr.py --data-file qris.txt --image foto.jpg --out qris-foto.png --crop 69,-25,1127
```

`--crop x,y,ukuran` dalam piksel foto asli; nilai negatif boleh (latar diperluas otomatis). Lihat posisi cincin di hasil pertama, lalu geser/perbesar foto supaya mata-hidung-mulut berada di celah antar cincin.

**d. Uji, lalu tes nyata:**

```bash
python3 check.py qris-foto.png --data-file qris.txt
```

Setelah lolos `check.py`, tetap tes di aplikasi bank sungguhan (scan dari galeri **dan** kamera langsung), lalu bayar nominal kecil sebelum dipasang.

Parameter yang bisa diubah: `--alpha` (kontras titik terhadap sekitar, default 80), `--dark-max` (110), `--light-min` (160), `--dot` (0.45), `--square-finders`. Nilai default adalah titik tengah terbaik dari pengujian di bawah; menurunkan kontras membuat titik lebih samar tapi kamera cepat gagal.

## Histori pendekatan dan alasan keputusan

Proyek ini dimulai dari pembuatan QR dengan logo Qilo One "seperti contoh QR Pizza Hut / Starbucks / KFC", yaitu gambar yang tersusun dari titik QR, bukan logo yang ditempel. Lalu dikembangkan ke QRIS dengan foto. Urutannya:

1. **Logo ditempel di tengah** (mengandalkan koreksi error level H). Terbaca, tapi bukan yang dimaksud. **Ditolak.**
2. **Logo samar di belakang titik (overlay)**, lalu **halftone 3x3 dengan titik tambahan**. Masih terasa seperti gambar ditumpuk, bukan terbentuk dari titik. **Ditolak.**
3. **Memaksa modul mengikuti logo dalam jatah koreksi error.** Logo mulai terbentuk dari modul, tapi samar karena jatahnya kecil (sekitar 85% kapasitas koreksi), dan QR jadi rapuh.
4. **QArt (riset Russ Cox).** Setelah mencari referensi: blok Reed-Solomon bersifat linear, jadi bit "bebas" di ekor data bisa dipilih lewat eliminasi Gauss sehingga modul membentuk gambar **tanpa memakai koreksi error sama sekali**. Hasilnya bersih, sekitar 86% modul data mengikuti logo. **Dipakai untuk mode logo** (`logo_qr.py`). Catatan: `pyqart` tidak bisa dipasang di lingkungan kerja, dan `qrcode.util.create_data` error `glog(0)` saat data nol, jadi encoder GF(256)/Reed-Solomon ditulis sendiri.
5. **QRIS tidak bisa memakai QArt.** Isi QRIS berstruktur TLV dan diakhiri CRC; menambah karakter membuatnya ditolak aplikasi bank. Jalan aman: **halftone 3x3** (Chu dkk., 2013): sub-titik tengah tiap modul membawa data apa adanya, 8 sub-titik lain membentuk foto. Isi QRIS tidak berubah sama sekali. Berhasil dibaca aplikasi bank **dari galeri**.
6. **Kotak alignment kecil dianggap mengganggu, lalu dihapus.** Dari galeri tetap terbaca, tapi **kamera langsung gagal** (simulasi kamera: 3/36). Dari riset: pemindai memakai pola alignment untuk mengoreksi gambar yang miring/melengkung, dan riset QR artistik (mis. ArtCoder, CVPR 2021) sengaja mempertahankan pola finder dan alignment. **Keputusan: alignment wajib ada.**
7. **Kenapa contoh Pizza Hut cuma punya 1 penanda kecil:** isinya URL pendek, jadi QR-nya versi kecil. Isi QRIS ±235 karakter butuh QR versi 7 ke atas, yang wajib punya 6 penanda alignment. Ini batas dari panjang isi, bukan dari metode.
8. **Bentuk penanda.** 13 lingkaran hitam: terbaca tapi jelek. Penanda dari titik tengah yang diperbesar: kamera gagal (11-22/36). **Keputusan:** QR sekecil mungkin (versi 8, 6 penanda), cincin bulat yang warnanya diambil dari foto di sekitarnya.
9. **Gaya foto utuh (riset Lin dkk., paten US9760820, Visualead).** Daripada dithering hitam-putih, foto ditampilkan utuh dan hanya blok tengah modul yang terang-gelapnya disesuaikan. Library otomatis menyimpan angka QRIS dalam mode numerik, sehingga QR jadi versi 8 (49x49) dengan titik besar. Simulasi kamera: 36/36.
10. **Kamuflase (gaya final).** Tujuan: mata melihat foto, kamera melihat kode. Prinsip yang dipakai:
    - mata bekerja seperti filter low-pass, sedangkan pemindai (ZXing) hanya mengambil sampel piksel tengah tiap modul;
    - titik hanya diubah **kalau perlu** dan **relatif terhadap rata-rata sekitar** (cara binarizer pemindai), bukan ke hitam/putih mutlak;
    - warna (hue) dipertahankan, hanya terang-gelap yang digeser;
    - tepi titik bergradasi (modulasi Gaussian).

    Tanpa batas mutlak (`--dark-max`, `--light-min`), titik nyaris tak terlihat tapi kamera gagal (0-12/36). Dengan batas: kamera 33-34/36, sedikit di atas QRIS asli di simulasi yang sama (WeChat 29/36).
11. **Batas yang tidak bisa ditembus:** titik tidak bisa hilang total. Kamera membaca beda terang-gelap, dan mata manusia paling peka justru pada beda terang-gelap. Ukuran titik QR pada cetakan normal juga berada di frekuensi yang paling terlihat mata. Versi yang lebih samar selalu gagal di kamera.
12. **Gaya titik penuh (dot-matrix/LED)** dicoba agar titik data bersembunyi di antara titik hiasan. Terbaca 36/36 bahkan tanpa cincin alignment, tapi gambarnya rusak dan sulit dikenali. **Ditinggalkan.**
13. **Penanda sudut bulat** dan potongan foto melingkar di sekitarnya, sudut kanan-bawah membulat. Keterbacaan tetap (kamera 33/36 ZXing, 34/36 WeChat).
14. **Penempatan foto:** posisi cincin alignment tetap, jadi foto yang digeser/diperbesar (`--crop`) supaya wajah berada di celah antar cincin.
15. **Warna logo yang lebih mencolok (`--palette`).** Pada QR logo kosewa, tangan navy terlihat hampir hitam dan menyatu dengan titik QR di luar logo. Penyebabnya: warna asli sudah sangat gelap, lalu masih digelapkan lagi, dan titik di luar logo juga navy. Pemindai hanya butuh titik yang cukup gelap dibanding putih, bukan hitam, jadi warna logo bisa diganti versi yang lebih cerah (biru `#1f4fd1`, merah `#c8102e`) dan titik di luar logo dibuat abu netral. Keterbacaan tetap setara. Konsekuensinya, warna tidak lagi sama persis dengan logo resmi.

## Batasan dan catatan

- Uji `check.py` adalah simulasi. Selalu tes di aplikasi bank/e-wallet nyata. Pada satu uji coba, aplikasi bank menampilkan "QR tidak sesuai" untuk QRIS halftone yang menurut ZXing isinya identik dengan aslinya; penyebabnya belum dipastikan. Uji scan QRIS asli di aplikasi yang sama sebagai pembanding.
- Scan dari galeri selalu lebih mudah daripada kamera ke layar (pantulan, pola layar). Uji juga pada hasil cetak.
- QRIS punya ketentuan tampilan dari penyedia/Bank Indonesia; cek sebelum dipakai di kasir.
- Memakai wajah orang lain (apalagi artis) untuk usaha butuh izin.
- QRIS asli, isi QRIS, dan foto orang tidak disertakan di repo ini.

## Referensi

- Russ Cox, *QArt Codes*: https://research.swtch.com/qart
- Chu dkk., *Halftone QR Codes*, SIGGRAPH Asia 2013: https://cgv.cs.nthu.edu.tw/projects/Recreational_Graphics/Halftone_QRCodes
- Su dkk., *ArtCoder*, CVPR 2021: https://arxiv.org/abs/2011.07815
- *Stylize Aesthetic QR Code* (catatan sampling ZXing): https://arxiv.org/abs/1803.01146
- *Scanning-robust aesthetic QR codes* (penyesuaian luminansi per modul): https://arxiv.org/abs/1803.02280
- Paten US9760820, *Method for generating color QR code*
- Paten US10755153 (modulasi Gaussian pada modul)
