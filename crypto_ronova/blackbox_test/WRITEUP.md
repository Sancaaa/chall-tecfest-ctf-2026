# Ronova — Write-up (Cryptography, Hard)

**Flag:** `TecFest26{ROnov4aAa4a4a4Aaa44AAA4a4A}`

> Catatan panitia: file ini dan `solve.py` ditaruh di folder `dist` hanya karena sesi solve dibatasi ke folder ini. **Pindahkan keluar dari `dist` sebelum soal dibagikan ke peserta.**

---

## 1. Kenali dulu 4 attachment-nya

| File | Isi | Artinya buat kita |
|---|---|---|
| `Desc.txt` | Flag dikunci dengan kunci privat penanda tangan; kunci tidak bocor | Targetnya: **pulihkan kunci privat `d`** dari data yang bocor |
| `capture.json` | Kurva secp256k1, `public_key`, dan 1500 tanda tangan `(h, r, s, hint)` | Bahan mentah. Ada field aneh bernama `hint` |
| `session-*.jsonl` | Chat engineer dengan AI yang menulis kode signer | **Bocoran source code** — di sinilah bug-nya |
| `flag.enc` | AES-256-CBC, `kdf: sha256(d_be32)` | Kuncinya = `SHA256(d dalam 32 byte big-endian)`. Jadi kalau dapat `d`, selesai |

Pola soal crypto "blackbox" yang normal: (1) pahami skema, (2) cari bug di implementasi, (3) petakan ke serangan yang dikenal, (4) buktikan dengan verifikasi, (5) pakai hasilnya untuk dekripsi.

## 2. Baca sesi yang bocor — cari bug

Fungsi `sign` yang di-review AI:

```python
nbytes = entropy_available()          # "kadang < 32"
k = int.from_bytes(os.urandom(nbytes), 'big') % n
...
s = k^-1 * (h + d*r) mod n
```

Dua hal yang menonjol:

1. Nonce `k` dibuat dari `nbytes` byte, dan `nbytes` **kadang kurang dari 32**. Jadi `k` bisa jauh lebih kecil dari `n` (~2^256). AI bilang "output tetap valid" — benar, tanda tangan tetap valid, tapi **nonce yang bias itu fatal** untuk ECDSA.
2. Di langkah terakhir engineer minta menambahkan field `hint` = `k.bit_length()` ke tiap entri. Artinya setiap tanda tangan **membocorkan batas atas nonce-nya**: `0 ≤ k < 2^hint`.

Intuisinya: ECDSA aman hanya kalau `k` uniform dan rahasia. Kalau kita tahu `k` "pendek", kita tahu bit-bit atas `k` adalah nol. Satu tanda tangan saja bocor sedikit, tapi **banyak tanda tangan menumpuk jadi cukup untuk membongkar `d`**. Ini keluarga serangan *biased/short nonce* → **Hidden Number Problem (HNP)**.

## 3. Ubah jadi persamaan yang bisa diserang

Dari `s = k^-1 (h + d r)`:

```
k_i ≡ (r_i/s_i)·d + (h_i/s_i)  (mod n)
k_i ≡ t_i·d + a_i             (mod n),   dengan 0 ≤ k_i < 2^hint_i
```

`t_i` dan `a_i` kita tahu semua (dari `r, s, h`). Yang tidak diketahui: `d` (satu angka 256-bit) dan `k_i` (kecil). Ini persis HNP: "ada kombinasi linear dari `d` yang hasilnya mod `n` ternyata kecil". Persoalan seperti ini diselesaikan dengan **lattice (LLL/BKZ)**.

## 4. Lihat distribusi `hint` — pilih tanda tangan terbaik

Distribusi `hint` pada 1500 tanda tangan: sebagian besar 254–256 (hampir tidak bocor), tapi ada yang turun sampai 243. Catatan file sendiri bilang *"most are useless"*. Betul: `hint=256` bocor 0 bit, `hint=250` bocor 6 bit.

Strategi: **buang yang tak berguna, pakai yang bocornya besar.** Saya ambil 100 tanda tangan dengan `hint` paling kecil (semua `hint ≤ 252`) → total bocor sekitar **592 bit**, jauh di atas 256 bit yang dibutuhkan untuk `d`. Lebih sedikit baris juga membuat lattice kecil dan cepat.

## 5. Bangun lattice

Karena tiap baris punya batas berbeda (`B_i = 2^hint_i`), tiap kolom diskalakan `c_i = 2^256 / B_i` supaya semua koordinat target sama besar (~2^255). Lalu pakai embedding Kannan (dimensi m+2, m = 100):

```
baris i  (i<m): n·c_i pada kolom i
baris m       : (t_1·c_1, …, t_m·c_m, 1, 0)
baris m+1     : ((a_i − B_i/2)·c_i ..., 0, W)      W = 2^255
```

Vektor pendek yang kita cari adalah `(c_i·(k_i − B_i/2), d, W)`: semua koordinatnya ≲ 2^255, jauh lebih pendek daripada vektor acak di lattice ini. Jalankan **LLL**, cari baris yang koordinat terakhirnya `±W`, baca koordinat `d`-nya.

## 6. Verifikasi, lalu dekripsi

Jangan percaya hasil lattice mentah — cek dengan kunci publik: `d·G == public_key`. Cocok.

```
d = 66268924296893516064056641400348082869369850984197942484080456634752492483571
```

Kunci AES = `sha256(d.to_bytes(32, 'big'))`, IV dari `flag.enc`, mode CBC:

```
TecFest26{ROnov4aAa4a4a4Aaa44AAA4a4A}   (+ padding PKCS7)
```

## 7. Solver

`solve.py` (di folder yang sama). Dependensi: `python-flint` (LLL), `pycryptodome`.

```
python solve.py . 252 100
#              ^ folder  ^ hint maksimum  ^ jumlah tanda tangan
```

Selesai dalam ~2 detik. Tidak butuh scanning/brute force apa pun terhadap server — murni analisis offline.

## 8. Pelajaran

- Tanda tangan yang **valid** ≠ tanda tangan yang **aman**. Nonce ECDSA wajib uniform di `[1, n-1]`; nonce pendek/bias membocorkan `d`.
- Gunakan RFC 6979 (nonce deterministik) atau CSPRNG penuh 32+ byte.
- Jangan pernah log metadata nonce (`hint`) — sekalipun "buat debug". Bahkan tanpa `hint`, nonce yang bias masih bisa diserang (hanya lebih mahal).
- Jawaban AI "tanda tangannya masih valid" menyesatkan; jangan percaya review keamanan dari asisten kode tanpa dipikirkan sendiri.
