# Writeup: Asmoday's Lost 13 Cubical Protocol

> **Dokumen panitia.** Berisi flag dan solusi: jangan masuk attachment peserta, deskripsi, atau repo publik.

| | |
|---|---|
| Kategori | Miscellaneous (slot C) |
| Author | SancaPWN |
| Tipe | Service `nc` (TCP 13337), instance bersama, timeout 20 detik |
| Flag | `TecFest26{Unk0wn_G0d_Cub3s_g0Es_PuFf}` |
| Solver | `solve_stdlib.py` (stdlib saja), `solve.py` (versi numpy) |
| Penalaran lengkap | `MATH.md` |

## Ringkasan

Server menyadap 13 "kubus Rubik" dalam bentuk daftar pasangan `(c, R)` (format eigencube). Tidak ada kubus yang perlu di-*solve*. Data tersembunyi ada pada **putaran 4 keping center terhadap sumbunya sendiri**, yang tidak terlihat di warna tetapi tercatat di `R`. Tiap kubus membawa 1 karakter ASCII (4 center × 2 bit), 13 kubus membentuk token acak. Token dikirim balik dalam 20 detik untuk mendapat flag.

## Petunjuk bertingkat (siap dipakai lewat Open Ticket)

Isi `Clue.txt`, dari yang paling umum:

1. Video "Rubik's linear algebra": kubus sebagai matriks rotasi.
2. `1 cube = 1 char`
3. `Big-Endian`
4. `base4, 4 center`
5. `rotation of center pieces`

## Analisis

### 1. Lihat datanya

Koneksi `nc` memberi banner, satu baris JSON, lalu prompt:

```
[!] Active Channels (MSB to LSB):
    Channel 0 -> Right (+Y) (c = [0, 1, 0])
    Channel 1 -> Front (+X) (c = [1, 0, 0])
    Channel 2 -> Top (+Z) (c = [0, 0, 1])
    Channel 3 -> Left (-Y) (c = [0, -1, 0])
[!] Timeout: 20 seconds.
[!] Transmitting 13 spatial cube states...
{"channels": [...], "cubes": [{"cube_id": 0, "pieces": [{"c": [..], "R": [[..],[..],[..]]}, ...26 keping...]}, ...13 kubus]}
[?] Submit decoded token:
```

Pengamatan:

- 13 kubus, 26 keping per kubus (3×3×3 tanpa inti). Urutan keping **diacak**, jadi pencarian harus berdasarkan `c`.
- Hanya 4 keping yang `c`-nya muncul di `channels`. Cek sendiri: untuk keping lain, `R` selalu matriks identitas. Itu bukan petunjuk.
- Untuk keping channel, `R` bervariasi antar kubus. Di situlah datanya.
- Banner menulis "MSB to LSB", dan 13 = jumlah karakter, cocok dengan clue 2 dan 3.

### 2. Memahami `(c, R)`

`c` adalah alamat asal keping, `R` rotasi 3×3, posisi sekarang `p = R·c`. Pada kubus ini hanya center yang dimodifikasi, dan `c` center adalah vektor satuan `v` (mis. `[1,0,0]`).

Kunci pengamatan: `R` untuk center selalu salah satu dari 4 matriks yang memenuhi `R·v = v`. Artinya center **tidak berpindah, hanya berputar terhadap sumbunya** (0°, 90°, 180°, 270°). Itu 4 keadaan = 1 digit basis-4 (clue 4 dan 5).

Bentuk matriksnya (konvensi eigencube, searah jarum jam dilihat dari ujung `v`):

```
R = v vᵀ − d·[v]×        d = +1 untuk 90°,  −1 untuk 270°
```

Dari sini 4 kandidat per sumbu bisa dihitung, atau dibaca langsung seperti di bawah. Tabel `k=1` semua sumbu ada di `MATH.md` bagian 3.

### 3. Membaca digit `k` dari sebuah `R`

`R` hanyalah rotasi sebesar `θ = k·90°` di sekitar sumbu `v`, jadi cukup baca `cos θ` dan `sin θ` dari blok 2×2 yang tegak lurus sumbu itu. Misal `v` ada di indeks `a` (x=0, y=1, z=2) dengan tanda `s`; `p=(a+1)%3`, `q=(a+2)%3`:

```
cos θ = R[p][p]
sin θ = −s · R[q][p]
```

| (cos θ, sin θ) | (1, 0) | (0, 1) | (−1, 0) | (0, −1) |
|---|---|---|---|---|
| `k` | 0 | 1 | 2 | 3 |

Penurunan dan contoh hitung ada di `MATH.md` bagian 4.

Tidak perlu tahu arah putar yang "benar" dari awal: kalau arah tertukar, token yang keluar **bukan alfanumerik sama sekali** (dari 62 karakter yang mungkin, tidak satu pun tetap alfanumerik setelah 1↔3 ditukar di semua channel). Jadi kesalahan arah langsung ketahuan, tinggal dibalik.

### 4. Digit → karakter

Channel 0 adalah digit terbesar (big-endian, clue 3):

```
ASCII = 64·k₀ + 16·k₁ + 4·k₂ + k₃
```

Token hanya `[A-Za-z0-9]` (ASCII 48–122), jadi `k₀ ∈ {0,1}`. Ini cara cepat memeriksa bahwa channel 0 sudah benar: ia tidak pernah bernilai 2 atau 3.

Contoh kubus 0 dari `sample_transmission.json`: `(k₀..k₃) = (1,2,1,1)` → `64+32+4+1 = 101` → `'e'`. Keseluruhan sample menghasilkan `eIg3nCuB3_3Nc`.

### 5. Kenapa harus pakai script

Token berubah tiap koneksi, dan timeout 20 detik tidak cukup untuk membaca 13 kubus dengan tangan. Peserta harus menulis solver yang mengambil JSON, mendekode, lalu membalas dalam satu koneksi.

## Solusi

```python
import json, socket, sys

def read_k(v, R):
    a = next(i for i in range(3) if v[i] != 0)  # indeks sumbu v
    p, q = (a + 1) % 3, (a + 2) % 3             # (a, p, q) urutan siklik x -> y -> z
    cos = R[p][p]
    sin = -v[a] * R[q][p]
    return {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}[(cos, sin)]

def decode_transmission(data):
    token = ""
    for cube in data["cubes"]:
        by_c = {tuple(p["c"]): p["R"] for p in cube["pieces"]}
        k = [read_k(ch["c"], by_c[tuple(ch["c"])]) for ch in data["channels"]]
        token += chr(64 * k[0] + 16 * k[1] + 4 * k[2] + k[3])
    return token

s = socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=20)
f = s.makefile("rwb")
line = f.readline()
while line and not line.startswith(b"{"):
    line = f.readline()
token = decode_transmission(json.loads(line))
f.write((token + "\n").encode()); f.flush()
print(f.read().decode())
```

Versi lengkap (dengan mode offline) ada di `solve_stdlib.py`. Menjalankannya:

```bash
python solve_stdlib.py HOST 13337
```

Keluaran: `[+] FLAG: TecFest26{Unk0wn_G0d_Cub3s_g0Es_PuFf}`.

## Jebakan umum

- **Mencari keping lewat indeks list.** Urutan diacak per kubus; harus berdasarkan `c`.
- **Urutan channel.** Bit tertinggi adalah channel 0 (urutan di JSON `channels`), bukan urutan sumbu X, Y, Z atau urutan nama.
- **Channel tiap koneksi berbeda.** 4 dari 6 sumbu dipilih acak per koneksi, jadi jangan mengunci sumbu tertentu.
- **Arah putar.** Menebak arah salah menghasilkan token non-alfanumerik; membalik 1↔3 memperbaikinya.
- **Mencoba menyelesaikan kubus.** Semua keping sudah "solved" menurut warna; tidak ada yang perlu disusun. Simulator eigencube publik (`smolkaj/eigencube`) hanya berguna untuk memahami format `(c, R)`.
- **Token dibawa antar koneksi.** Token hanya berlaku untuk koneksi yang sama.

## Catatan untuk penilai write-up

Write-up peserta yang baik minimal memuat:

1. Pengamatan bahwa hanya 4 center yang `R`-nya non-identitas (atau bahwa informasi ada di putaran center terhadap sumbunya).
2. Pemetaan 4 kemungkinan `R` ke digit 0..3, termasuk konvensi arah.
3. Aturan penggabungan: big-endian, MSB = channel 0, 1 kubus = 1 karakter ASCII.
4. Penjelasan bahwa token acak per koneksi sehingga solver harus otomatis dalam satu koneksi.

Kreativitas: pembacaan cos dan sin sudut putar seperti di atas, atau menurunkan 4 kandidat dari rumus rotasi, sama-sama sah. Solusi yang hanya menempelkan JSON ke AI tanpa solver tidak bisa lolos karena timeout; tautan chat AI wajib dilampirkan pada submit.

## Verifikasi

`python -m unittest test_challenge` (dari folder ini) menjalankan 23 tes: tabel matriks, aturan baca, contoh kubus 0, sample, serta perilaku server (token terpotong, tanpa newline, timeout, 40 koneksi paralel, batas koneksi). Test solve oleh orang lain (non-author) dari deskripsi dan `nc` saja belum dilakukan.
