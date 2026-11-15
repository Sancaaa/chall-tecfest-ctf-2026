# Matematika di balik Ronova (HNP + lattice)

> **File AUTHOR — intended solution. JANGAN ke peserta.**
> Tujuan: memberi Sanca gambaran matematis utuh, sampai bisa mengikuti contoh angka kecil dengan tangan.
> Pasangannya: `toy.sage` (contoh kecil, bisa diotak-atik) dan `solve.sage` (versi penuh).

Notasi: kurva punya titik dasar `G` berorde `n` (prima). Private key `d`, public key `Q = dG`.
`h` = hash pesan (sebagai integer mod `n`).

---

## 1. Dari ECDSA ke satu persamaan linear

Rumus tanda tangan ECDSA:

$$ s \equiv k^{-1}(h + r\,d) \pmod n $$

`k` = nonce (rahasia, sekali pakai), `(r,s)` = tanda tangan. Kalikan `k`, lalu susun ulang untuk mengisolasi `k`:

$$ sk \equiv h + rd \;\Rightarrow\; k \equiv s^{-1}h + s^{-1}r\,d \pmod n $$

Definisikan dua besaran yang **bisa dihitung peserta** (karena `h, r, s, n` diketahui):

$$ a \equiv s^{-1}h \pmod n, \qquad t \equiv s^{-1}r \pmod n $$

Maka tiap tanda tangan memberi satu persamaan:

$$ \boxed{\,k_i \equiv a_i + t_i\, d \pmod n\,} $$

Hanya `d` (sama untuk semua) dan `k_i` (beda tiap tanda tangan) yang tak diketahui.

---

## 2. Kenapa nonce kecil membongkar kunci

Persamaan `k_i = a_i + t_i d mod n` punya **dua** hal tak diketahui per baris (`d` dan `k_i`). Kalau `k_i` boleh apa saja di `[0, n)`, maka untuk **tebakan `d` apa pun** selalu ada `k_i` yang pas. Tidak ada informasi. **Itulah sebabnya ECDSA normal aman.**

Yang berubah di Ronova: `k_i` **kecil**, `k_i < K` dengan `K \ll n`. Sekarang tiap persamaan menolak hampir semua `d`:

- Untuk `d` yang benar, `(a_i + t_i d) \bmod n = k_i < K` untuk **semua** `i`.
- Untuk `d` salah, `(a_i + t_i d) \bmod n` praktis acak di `[0,n)`, jadi peluang `< K` hanya `K/n`.

Kalau ada `m` tanda tangan, peluang `d` salah lolos semuanya `\approx (K/n)^m`. Dengan `K/n = 2^{-\ell_{\text{bocor}}}` ini jatuh sangat cepat. Jadi secara **informasi**, kunci sudah tertentu. Masalahnya tinggal: bagaimana menemukannya tanpa mencoba `2^{256}` kemungkinan `d`? → lattice.

---

## 3. Reformulasi: "cari d yang membuat semua k_i kecil"

Tulis `k_i = a_i + t_i d - c_i n` untuk suatu bilangan bulat `c_i` (itu arti "mod n"). Kita mencari `d` dan `c_i` sehingga semua `k_i` kecil. Ini **Hidden Number Problem (HNP)**: pulihkan bilangan tersembunyi `d` dari fakta bahwa `a_i + t_i d` dekat ke kelipatan `n`.

Trik lattice: susun sebuah **kisi (lattice)** — himpunan semua kombinasi bulat dari beberapa vektor basis — yang **memuat** vektor pendek `(k_1, \dots, k_m, \dots)`. Lalu algoritma reduksi (LLL/BKZ) mencari vektor pendek itu.

---

## 4. Apa itu lattice (secukupnya)

Lattice = `\{ \sum_i x_i \mathbf{b}_i : x_i \in \mathbb{Z} \}`, semua kombinasi **bulat** dari vektor basis `\mathbf{b}_i`. Dua fakta yang kita pakai:

1. **Vektor pendek itu istimewa.** Kebanyakan anggota lattice panjang; hanya sedikit yang pendek. Kalau kita tahu ada satu vektor sangat pendek dan tahu bentuknya memuat jawaban, menemukannya = menyelesaikan masalah.
2. **LLL/BKZ** menerima basis "jelek" (vektor panjang, hampir sejajar) dan mengembalikan basis "bagus" (pendek, hampir tegak lurus) untuk lattice **yang sama**. Vektor pertama hasilnya biasanya salah satu yang terpendek.

Intuisi reduksi (kasus 2D, bisa tangan): kalau punya dua vektor `\mathbf{u}, \mathbf{v}`, ganti `\mathbf{v} \leftarrow \mathbf{v} - \lfloor \tfrac{\mathbf{u}\cdot\mathbf{v}}{\mathbf{u}\cdot\mathbf{u}} \rceil \mathbf{u}` (kurangi proyeksi, bulatkan). Ulangi tukar-menukar sampai tak memendek lagi. Hasilnya dua vektor terpendek. LLL = perumuman ini ke dimensi tinggi.

---

## 5. Konstruksi matriks (inti)

Pakai `m` tanda tangan dengan batas seragam `k_i < K`. Susun basis `(m+2) \times (m+2)` (baris = vektor basis):

$$
M=\begin{pmatrix}
n & & & & \\
 & n & & & \\
 & & \ddots & & \\
 & & & n & & \\
t_1 & t_2 & \cdots & t_m & K/n & 0\\
a_1 & a_2 & \cdots & a_m & 0 & K
\end{pmatrix}
$$

Baca per bagian:
- **`m` baris pertama** (`n` di diagonal): mewakili "kebebasan mod `n`", yaitu suku `-c_i n`. Mengurangkan `c_i \times` baris ke-`i` = mengurangi kelipatan `n` pada kolom `i`.
- **Baris ke-`m` (`t_i`)**: koefisien `d`. Mengambil `d \times` baris ini = menaruh `t_i d` di tiap kolom `i`. Pojoknya `K/n`.
- **Baris ke-`m+1` (`a_i`)**: suku konstan `a_i`. Pojoknya `K`.

---

## 6. Vektor target: kenapa ia anggota lattice DAN pendek

Ambil kombinasi bulat: `d \times (\text{baris } t) + 1 \times (\text{baris } a) - \sum_i c_i \times (\text{baris } i)`.

Kolom `i` (untuk `i=1..m`) menjadi:

$$ t_i d + a_i - c_i n = k_i \quad (\text{kecil!, } < K) $$

Dua kolom terakhir menjadi `d\cdot(K/n)` dan `1\cdot K`. Jadi lattice memuat vektor

$$ \mathbf{v} = \big(k_1, k_2, \dots, k_m,\; dK/n,\; K\big). $$

**Panjangnya** `\approx K\sqrt{m+2}`: tiap `k_i < K`, pojok `dK/n < K` (karena `d<n`), pojok `K`. Semua entri seukuran `K`. Inilah vektor pendek yang dicari LLL. Semua entri yang tadinya seukuran `n` (jauh lebih besar dari `K`) sudah "ditelan" oleh pengurangan kelipatan `n`.

---

## 7. Kenapa LLL benar-benar menemukannya (syarat jumlah tanda tangan)

Volume (determinan) lattice: dari struktur blok `M`,

$$ \det(L) = n^{m}\cdot \frac{K}{n}\cdot K = n^{m-1}K^2. $$

**Heuristik Gaussian**: vektor terpendek yang "diharapkan" di lattice berdimensi `dim=m+2` berukuran `\approx \det(L)^{1/\dim}`. Supaya target kita `\mathbf{v}` (berukuran `\approx K`) benar-benar **lebih pendek** dari vektor acak lain (jadi menonjol dan ditemukan), perlu

$$ K \lesssim \big(n^{m-1}K^2\big)^{1/(m+2)}. $$

Ambil log basis 2: tulis `n \approx 2^{B}` (di secp256k1, `B=256`) dan `K \approx 2^{\ell}` (jadi bit bocor `= B-\ell`). Pertidaksamaan menjadi

$$ \ell \;<\; \frac{(m-1)B + 2\ell}{m+2} \;\Longrightarrow\; \ell\,m < (m-1)B \;\Longrightarrow\; (B-\ell) \;>\; \frac{B}{m}. $$

Artinya: **total bit yang bocor harus melebihi ukuran kunci**:

$$ \boxed{\, m \times (\text{bit bocor per tanda tangan}) \;>\; B \,} $$

Untuk Ronova: `B=256`, bit bocor `~5..13`, maka butuh `m \gtrsim 256/8 \approx 32`. Kita pakai `m=70` → ada margin, tapi tipis → perlu reduksi kuat (BKZ), bukan sekadar LLL. Ini sebabnya angka 70 di `solve.sage`.

---

## 8. Ekstraksi d

Setelah LLL, cari baris yang berbentuk `\pm\mathbf{v}`. Dari dua entri terakhirnya:

$$ \text{entri}_{-1} = \pm K, \qquad \text{entri}_{-2} = \pm dK/n. $$

Maka `d = \text{entri}_{-2}\cdot n / K \bmod n`. Coba kedua tanda dan juga `n-d`, verifikasi dengan `dG = Q`. Lalu kunci AES `= \text{SHA256}(d)` membuka flag.

---

## 9. Contoh angka kecil (ikuti dengan tangan) — dari `toy.sage`

Pakai `n=10007`, `K=128`, dan **rahasia** `d=1234`, `k=(42,7,88)`, `t=(5915,2134,8201)`.

**Langkah A — hitung `a_i`** (ini yang peserta lakukan dari `h,r,s`; di toy kita set langsung):
`a_i = (k_i - t_i d) \bmod n`:
$$ a = (6042,\; 8499,\; 7138). $$
Cek: `(a_i + t_i\cdot 1234) \bmod 10007 = (42, 7, 88)` ✓ — persamaan Bagian 1 berlaku.

**Langkah B — susun `M` (5×5):**
```
[ 10007      0      0        0     0 ]
[     0  10007      0        0     0 ]
[     0      0  10007        0     0 ]
[  5915   2134   8201  128/10007   0 ]
[  6042   8499   7138        0   128 ]
```

**Langkah C — LLL** (dijalankan Sage). Hasil baris ke-2:
```
[ 42   7   88   157952/10007   128 ]
```
Kenali: `(42, 7, 88) = (k_1,k_2,k_3)`, lalu `157952/10007 = 1234\cdot128/10007 = dK/n`, lalu `128 = K`. Persis `\mathbf{v}` di Bagian 6.

**Langkah D — ekstrak `d`:**
$$ d = \frac{157952/10007 \times 10007}{128} = \frac{157952}{128} = 1234. \checkmark $$

(Baris lain hasil LLL, mis. `(0,0,0,-128,0)`, memberi `d=0` — itu vektor pendek "palsu" dari kolom `K` saja; makanya kita verifikasi tiap kandidat dengan `dG=Q`.)

> **Latihan buatmu:** buka `toy.sage`, ganti `d`, `k`, `t` (jaga `k_i < K`), jalankan lagi. Lihat baris target selalu muncul. Lalu coba naikkan `K` mendekati `n` (bias mengecil) — pada titik tertentu LLL **gagal** menemukan `d`: itu batas Bagian 7 yang kamu rasakan sendiri.

---

## 10. Dari toy ke soal asli: dua tambahan

**(a) Bias bervariasi → pembobotan.** Di soal asli tiap `k_i` punya batas beda `K_i = 2^{\text{hint}_i}`. Satu `K` seragam jadi longgar. Perbaikan: kalikan kolom `i` dengan bobot `w_i = 2^{L-\text{hint}_i}` (`L = \max \text{hint}`) sehingga `w_i K_i \approx 2^L` seragam. Di `solve.sage` ini baris `w = [...]` dan `Mx[i,i]=n^2 w_i`, `Mx[m,i]=n t_i w_i`, dst. (versi integer, dikali `n`, agar bisa BKZ).

**(b) Margin tipis → BKZ.** Karena `m\times\text{bocor}` hanya sedikit di atas `B`, LLL sering meleset. BKZ dengan `block_size` naik bertahap memeriksa lebih banyak kombinasi → menemukan `\mathbf{v}` yang LLL lewatkan. Terbukti di uji: 8/8 seed sukses di `block_size` 10–20, sedangkan LLL (bs=2) gagal.

---

## 11. Peta ringkas (data → flag)

```
capture.json ──(saring hint terkecil)──► 70 tanda tangan ter-bias
      │ hitung a_i=s⁻¹h, t_i=s⁻¹r (mod n)
      ▼
k_i = a_i + t_i d (mod n), k_i kecil        ← Hidden Number Problem
      │ susun lattice berbobot (Bagian 5+10a)
      ▼
BKZ bertahap ──► vektor pendek v=(k_1..k_m, dK/n, K)
      │ d = v[-2]·n/K mod n ; verifikasi dG=Q
      ▼
d ──► SHA256(d) = kunci AES ──► dekripsi flag.enc ──► TecFest26{...}
```
