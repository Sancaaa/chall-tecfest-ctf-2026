# Warm-up Forensic — Qiqi

**Author:** SancaPWN
**Difficulty:** Warm-up (sangat mudah)

## Konsep

File `qiqi_catatan_resep.pdf` sebenarnya adalah gambar (PNG) yang disimpan dengan
ekstensi `.pdf`. Tidak ada enkripsi/steganografi — murni pengenalan magic bytes.
Flag di-overlay **langsung** di atas gambar asli (`images (5).jpg`, screenshot
Qiqi), tanpa teks/gimmick lain — begitu gambarnya kebuka, flag langsung kelihatan.

## Intended Solution

1. Coba buka file dengan PDF reader -> gagal / rusak.
2. Cek magic bytes (`file qiqi_catatan_resep.pdf`, atau buka di hex editor /
   HxD / `xxd`): 4 byte awal `89 50 4E 47` = signature PNG, bukan `%PDF`.
3. Ganti ekstensi jadi `.png`, buka seperti gambar biasa.
4. Flag langsung terlihat di overlay gambar.

## Flag

`TecFest26{I_PULL3d_A_qIQi_l057_fIf7Y_FiF7Y}`

## File author

- `images (5).jpg` — gambar sumber (nanti di-rename ke nama lebih rapi)
- `generate.py` — overlay flag ke gambar + penyamaran ekstensi (`python generate.py`)
- `qiqi_overlay.png` — PNG hasil overlay (author only, jangan dibagikan ke peserta)
- `dist/qiqi_catatan_resep.pdf` — attachment peserta (isi PNG, ekstensi .pdf)
- `flag.txt` — flag (jangan di-upload)
