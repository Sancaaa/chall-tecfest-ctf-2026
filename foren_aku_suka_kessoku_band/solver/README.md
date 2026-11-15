# Intended Solution — Aku Suka Kessoku Band

**Kategori:** Forensic  
**Difficulty:** Easy–Medium  
**Flag:** `TecFest26{1_LQv3_mU51c_4nD_BOCHI!}`

---

## Ringkasan

Challenge ini menggunakan file audio FLAC yang menyembunyikan flag dalam **dua tempat berbeda**:

1. **Part 1** — Tersembunyi di dalam audio sebagai spectrogram (visualisasi frekuensi).
2. **Part 2** — Tersembunyi di metadata field `COMMENT`, di-encode Base64 sebanyak 7 kali.

---

## Langkah Penyelesaian

### Part 1 — Spectrogram

**Konsep:** Steganografi audio menggunakan spectrogram. Teks yang dirender sebagai sinyal audio akan terlihat ketika audio ditampilkan sebagai spectrogram (visualisasi frekuensi vs waktu).

**Tools:** [Sonic Visualiser](https://www.sonicvisualiser.org/), Audacity, atau `sox`.

**Langkah:**

1. Buka file `kessoku_band.flac` dengan **Sonic Visualiser**.
2. Tambahkan layer: **Layer → Add Spectrogram**.
3. Scroll ke **bagian akhir** audio.
4. Lihat secara visual — teks flag part 1 akan terlihat di spectrogram.

Alternatif dengan Python:
```python
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np

y, sr = librosa.load("kessoku_band.flac", sr=None)
D = librosa.stft(y)
S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

plt.figure(figsize=(20, 6))
librosa.display.specshow(S_db, sr=sr, x_axis='time', y_axis='hz')
plt.colorbar()
plt.title('Spectrogram')
plt.tight_layout()
plt.savefig("spectrogram.png", dpi=150)
```

**Result Part 1:** `TecFest26{1_LQv3_mU51c_`

---

### Part 2 — Metadata COMMENT (Base64 x7)

**Konsep:** Field metadata `COMMENT` pada file FLAC berisi string yang di-encode Base64 sebanyak 7 kali. Peserta perlu mengekstrak metadata lalu decode berulang kali.

**Langkah:**

1. Baca metadata FLAC:

```bash
# Menggunakan metaflac
metaflac --list --block-type=VORBIS_COMMENT kessoku_band.flac

# Atau menggunakan ffprobe
ffprobe -v quiet -print_format json -show_format kessoku_band.flac

# Atau ExifTool
exiftool kessoku_band.flac
```

2. Ambil nilai field `COMMENT`:
```
Vm0wd2VFMUhSWGhYV0d4VFltczFWVmx0ZUV0WFJteDBUbFZPYW1KR1dubFdiVFZMWWtaYWRWRnNjRnBOUmxweVYxWmtTMUl4VG5KaFJscHBWMFZLVFZaclpIcGxSbHBZVTJ0V1VtSkhVbkJWYlhSM1YwWmtjMVp0Um1waVZscEhWREZXVjFWdFNsaGxSemxWVm14YU0xcEZXbUZXTVhCSlkwVTVWMkV6UWtsV2EyUXdXVmRHUmsxWVVtaFRSa3BZVm0xNFIwMHhVWGhTVkd4UlZWUXdPUT09
```

3. Decode Base64 sebanyak **7 kali**:

```python
import base64

encoded = "Vm0wd2VFMUhSWGhYV0d4VFltczFWVmx0ZUV0WFJteDBUbFZPYW1KR1dubFdiVFZMWWtaYWRWRnNjRnBOUmxweVYxWmtTMUl4VG5KaFJscHBWMFZLVFZaclpIcGxSbHBZVTJ0V1VtSkhVbkJWYlhSM1YwWmtjMVp0Um1waVZscEhWREZXVjFWdFNsaGxSemxWVm14YU0xcEZXbUZXTVhCSlkwVTVWMkV6UWtsV2EyUXdXVmRHUmsxWVVtaFRSa3BZVm0xNFIwMHhVWGhTVkd4UlZWUXdPUT09"

result = encoded
for i in range(7):
    result = base64.b64decode(result).decode('utf-8')
    print(f"Decode x{i+1}: {result}")
```

**Result Part 2:** `4nD_BOCHI!}`

---

### Menyusun Flag

Gabungkan kedua part:

| Part | Nilai |
|------|-------|
| Part 1 (Spectrogram) | `TecFest26{1_LQv3_mU51c_` |
| Part 2 (Metadata) | `4nD_BOCHI!}` |
| **Flag Lengkap** | `TecFest26{1_LQv3_mU51c_4nD_BOCHI!}` |

---

## Estimasi Kesulitan

**Easy–Medium.** Teknik spectrogram steganography dan Base64 adalah teknik forensic yang cukup umum di CTF. Tantangan utama adalah:
- Mengetahui harus melihat spectrogram (bukan hanya mendengarkan).
- Mengenali bahwa Base64 perlu di-decode lebih dari satu kali.

## Potensi Unintended Solution

- Peserta mungkin langsung brute-force decode metadata tanpa menyadari ada 2 part.
- Jika spectrogram terlalu mudah terlihat, peserta mungkin tidak menelusuri metadata sama sekali.
