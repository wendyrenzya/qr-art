---
name: qr-art
description: Buat QR code artistik yang gambarnya terbentuk dari titik QR itu sendiri: logo via QArt (isi URL) atau foto berwarna dengan titik kamuflase (isi apa saja, termasuk QRIS).
---

# qr-art

Pakai repo ini (README.md berisi histori keputusan lengkap). Ringkasnya:

## Yang diinginkan
- Gambar TERBENTUK dari titik QR, bukan logo ditempel di tengah, bukan gambar samar di belakang titik, bukan titik tambahan di atas QR.
- Kalau ada pendekatan baru, riset referensi dulu, jangan menebak.

## Pilih mode
- Isi URL + logo/grafis sederhana: `logo_qr.py` (QArt, versi 18, level L).
- Isi tidak boleh diubah (QRIS) atau gambar berupa foto: `photo_qr.py` (default sudah hasil terbaik).
  - Ambil isi QRIS dengan zxing-cpp dari screenshot, cek CRC (tag 63) valid.
  - Geser `--crop` supaya wajah ada di celah antar cincin alignment.

## Wajib sebelum kirim
1. `python3 check.py hasil.png --data-file isi.txt` : decode harus sama persis; bandingkan dengan QR asli di simulasi yang sama.
2. Lihat gambarnya sendiri.
3. Minta tes di aplikasi nyata: galeri dan kamera langsung; untuk QRIS bayar nominal kecil.

## Jangan
- Jangan hapus cincin alignment atau membuat titik terlalu samar: kamera gagal (terbukti 0-22/36).
- Jangan pakai gaya titik penuh/LED: terbaca tapi gambar rusak.
- Jangan tambahkan apa pun ke isi QRIS.
- Ingatkan izin bila memakai wajah orang untuk usaha.
