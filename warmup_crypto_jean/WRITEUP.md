# Warm-up Cryptography — Jean

**Author:** SancaPWN
**Difficulty:** Warm-up (sangat mudah)

## Konsep

XOR single-key sederhana, key terlihat jelas di script enkripsi (`KEY = b"MONDSTADT"`).
Tidak ada layer encoding tambahan — sengaja agar bisa diselesaikan read-only (baca script,
tulis ulang XOR-nya, atau pakai CyberChef "XOR" dengan key teks `MONDSTADT`).

**Revisi (2026-11-08):** `enc.py` sengaja ditulis lebih verbose/eksplisit (loop manual
+ komentar panjang menjelaskan tiap langkah, bukan one-liner generator expression)
supaya lebih intuitif dibaca peserta yang baru belajar — tetap fungsinya sama persis,
cuma gaya penulisannya diubah untuk warm-up.

## Intended Solution

1. Baca `enc.py` -> ketemu `KEY = b"MONDSTADT"` dan fungsi `xor_encrypt`.
2. XOR itu involutif (`A ^ B ^ B = A`), jadi dekripsi = enkripsi ulang dengan key yang sama.
3. Jalankan ulang fungsi yang sama terhadap `output.enc` -> dapat flag plaintext.

## Flag

`TecFest26{kL33_570p_80m_1k4n_d1_D4N4U}`

## File author

- `enc.py` — script enkripsi (sama persis dengan yang dibagikan ke peserta)
- `flag.txt` — flag asli (jangan di-upload)
- `dist/jean_attachment.zip` — attachment peserta (isi: `enc.py` + `output.enc`)
