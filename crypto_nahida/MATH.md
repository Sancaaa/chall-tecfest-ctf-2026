# Math behind Nahida — derivasi + lab sheet manual

> Dokumen author. Pendamping [WRITEUP.md](WRITEUP.md). Berisi solusi.
> Tujuan: memahami aljabar di balik serangan dan mengerjakan **subset**-nya
> dengan tangan. Angka di bagian Lab diambil dari instance nyata (secrets saat
> dokumen ini dibuat); kalau `gen_secrets.py` dijalankan ulang, angkanya ganti —
> regenerasi dengan `scratchpad/dump_lab.py` atau hitung sendiri.

Notasi: `⊕` = XOR per-byte. Satu "blok" = 16 byte. `E_K(·)` = enkripsi AES
**satu blok** (fungsi satu-arah 128→128 bit yang kita pakai sebagai *black box*).
`D_K = E_K⁻¹`. Semua indeks blok mulai dari 0.

---

## 1. Objek dasar dan sifat XOR

XOR membentuk grup: `a⊕a=0`, `a⊕0=a`, komutatif & asosiatif. Konsekuensi yang
dipakai terus:

```
jika  C = P ⊕ S   maka   P = C ⊕ S   dan   S = C ⊕ P
```

Artinya begitu kita tahu dua dari {plaintext, ciphertext, keystream}, yang ketiga
langsung ketemu. Inilah satu-satunya "mesin" yang kita butuh di sisi tangan —
`E_K` tidak kita hitung manual, cukup kita minta nilainya (lihat §6).

---

## 2. Definisi CFB-128

Enkripsi (per blok, i ≥ 0), dengan umpan balik penuh 16 byte:

```
S_0 = E_K(IV)                 (keystream blok 0)
S_i = E_K(C_{i-1})   (i ≥ 1)  (keystream blok i = enkripsi ciphertext sebelumnya)
C_i = P_i ⊕ S_i
```

Dekripsi memakai **E_K juga, bukan D_K** (ini yang sering bikin bingung):

```
P_i = C_i ⊕ S_i = C_i ⊕ E_K(C_{i-1})     dengan  C_{-1} := IV
```

Dua fakta penting yang lahir dari sini:

1. **Keystream blok-0 hanya bergantung pada IV**, bukan pada data. Jadi kalau IV
   tetap, `S_0` tetap untuk semua koneksi.
2. **Keystream blok-i (i≥1) bergantung pada `C_{i-1}`** — ciphertext, yang publik.
   Jadi kalau kita punya cara menghitung `E_K(sesuatu)`, kita bisa menurunkan
   keystream blok manapun.

---

## 3. Kelemahan 1 — IV statis membocorkan `K0`

Server memakai `IV = SHA256(key)[:16]`, konstan. Definisikan

```
K0 := S_0 = E_K(IV)
```

Server membalas frame yang ditolak dengan **16 byte nol yang dienkripsi**. Balasan
itu dipakai sebagai blok-0 CFB pada cipher balasan yang juga mulai dari IV:

```
R_0 = 0 ⊕ E_K(IV) = E_K(IV) = K0
```

Jadi **balasan error = K0 gratis**. Tidak ada tebakan. Ini padanan "null bytes
leak" di soal aslinya. Karena IV statis, `K0` yang sama berlaku untuk blok-0
**setiap** stream, dua arah, selamanya (selama key tidak ganti).

Dengan `K0` kita bisa baca/forge blok-0 apa pun:

```
baca   :  P_0 = C_0 ⊕ K0
forge  :  C_0 = P_0 ⊕ K0        (pilih P_0, hasilkan C_0 yang mendekripsi ke situ)
```

Tapi **hanya blok-0**. Blok ≥1 butuh `E_K(C_{i-1})` yang belum kita punya → §6.

---

## 4. Kelemahan 2 — malleability & efek rantai

Karena `C_i = P_i ⊕ S_i` dan `S_i` tak bergantung `P_i`, mengubah ciphertext =
mengubah plaintext secara terkendali **pada blok yang sama**:

```
C_i' = C_i ⊕ Δ   ⇒   P_i' = C_i' ⊕ S_i = (C_i ⊕ S_i) ⊕ Δ = P_i ⊕ Δ
```

Jadi untuk menukar `stat`→`flag` di blok-i: `Δ = (s⊕f, t⊕l, a⊕a, t⊕g)` di posisi
byte yang tepat. **Tapi** `S_{i+1} = E_K(C_i)`, dan kita baru saja mengubah `C_i`.
Maka:

```
P_{i+1}' = C_{i+1} ⊕ E_K(C_i')   dengan C_i' ≠ C_i   ⇒  acak / rusak
```

Satu blok setelah titik edit **selalu hancur**. Blok i+2 dst aman (umpan baliknya
`C_{i+1}`, `C_{i+2}`, … tak berubah). Inilah sebab patch naif `stat`→`flag`
merusak blok `END` → vault balas `400`. Untuk memperbaikinya kita harus menyetel
`C_{i+1}` ulang, dan itu butuh `E_K(C_i')` → lagi-lagi §6.

---

## 5. CRC32 itu affine (kenapa ia menggagalkan bit-flip mentah)

CRC32 bukan kriptografis. Sebagai fungsi atas GF(2) ia **affine**:

```
CRC(x) = L(x) ⊕ k₀        L linear,  k₀ = CRC(0...0) konstan
⇒  CRC(x ⊕ Δ) = CRC(x) ⊕ L(Δ) = CRC(x) ⊕ (CRC(Δ) ⊕ k₀)
```

Jadi kalau kamu mem-flip header dengan `Δ` **tanpa** memperbarui field CRC, CRC
tidak lagi cocok → frame ditolak. Dua cara benar:

- **(dipakai di solver)** Karena `K0` sudah membuka `P_0` seluruhnya, kita tahu
  header plaintext apa adanya; tinggal susun `P_0'` yang baru dan hitung ulang
  `crc32(P_0'[:12])` dengan pustaka biasa, lalu `C_0' = P_0' ⊕ K0`. Linearitas tak
  perlu.
- **(bonus, kalau P_0 tak diketahui)** Pakai sifat affine di atas untuk mengoreksi
  4 byte CRC: `field_crc' = field_crc ⊕ L(Δ)`. Berguna di soal CFB lain yang tak
  membocorkan blok-0.

Catatan endian: di frame, CRC disimpan **little-endian** atas `P_0[0:12]`. Lihat
Lab: nilai `crc32 = 0x7db22d1f` disimpan sebagai byte `1f 2d b2 7d`.

---

## 6. Oracle `E_K(x)` dari tujuan `dbg`

`dbg` mendekripsi stream klien lalu **mengirim balik plaintext mentah (tanpa
dienkripsi)**. Kirim stream: blok-0 = header dbg valid `C0'`, lalu blok-blok
pilihan kita. Server mendekripsi:

```
input  :  C0'            || x              || 0^16
dekrip :  P0'(=header)   || P1             || P2
          P1 = x   ⊕ E_K(C0')      ← bergantung C0', buang
          P2 = 0^16 ⊕ E_K(x) = E_K(x)   ← inilah yang kita mau
```

Jadi **blok plaintext yang dikembalikan tepat setelah blok yang kita isi `x`
adalah `E_K(x)`**. Batch: `x1 || 0 || x2 || 0 || …` → `E_K(x_j)` muncul di blok
output ganjil (indeks 1, 3, 5, …).

Header dbg kita susun sendiri (§3): `P0'(dbg)` dengan ip=10.0.0.99, port=1, CRC
benar, lalu `C0' = P0'(dbg) ⊕ K0`.

**Sekarang kita punya `E_K` sebagai fungsi yang bisa dievaluasi di titik manapun.**
Itu mengubah CFB dari "satu arah" jadi dua arah penuh.

---

## 7. Enkripsi & dekripsi CFB penuh dengan `K0` + oracle

**Dekripsi** ciphertext apa pun `C_0 C_1 … C_n` (mis. request vault di pcap):

```
P_0 = C_0 ⊕ K0
P_i = C_i ⊕ E_K(C_{i-1})      i ≥ 1
```

Semua `C_{i-1}` sudah diketahui di muka → semua query oracle bisa **dibatch sekali
jalan** (paralel). Dari sini kita panen token `AUTH …`.

**Enkripsi** plaintext pilihan `P_0 P_1 … P_m` (request `CMD flag` buatan sendiri):

```
C_0 = P_0 ⊕ K0
C_i = P_i ⊕ E_K(C_{i-1})      i ≥ 1
```

Ini **sekuensial**: `C_i` butuh `E_K(C_{i-1})`, dan `C_{i-1}` baru ada setelah
langkah sebelumnya. Jadi enkripsi m blok = m−1 query oracle berurutan.

Balasan vault (`200 OK…` + body berisi flag) juga CFB: dekripsi dengan rumus yang
sama (`R_0⊕K0`, lalu `R_i⊕E_K(R_{i-1})`), semua `R_i` diketahui → batch.

Itulah seluruh serangannya: **K0 (dari §3) + oracle E_K (dari §6) ⇒ enkripsi dan
dekripsi penuh ⇒ minta vault `CMD flag` lalu baca jawabannya.**

---

## 8. Lab sheet — kerjakan dengan tangan

Semua nilai hex. XOR per-byte. `E_K(·)` tidak dihitung tangan — ambil dari tabel
oracle yang disediakan (di soal sungguhan kamu memperolehnya lewat §6).

### Diberikan

```
IV       = 78f749e068b2fc52a37d1b5f10413504
K0=E(IV) = 71c214aa4d8d0578c520bd2431a6c629
```

Request vault terekam (dari pcap), blok ciphertext:

```
C0 = 70c31eaa4d8826509611f9652e8b7454
C1 = da4a006a599e9ae049ffd6b0cde01738
C2 = c61523b214f2a5f8f019a56862f61856
```

Tabel oracle (nilai E_K pada titik yang kamu butuhkan di latihan ini):

```
E_K(C0) = 920f4c2616beec813c93a29ffcce2732
E_K(C1) = 874077fa34c792c8937a975053c42064
E_K(x)  = cac689d66f711ba1eb0732d6d00591f1   untuk x = 00112233445566778899aabbccddeeff
```

### Latihan

**L1 (baca header).** Hitung `P0 = C0 ⊕ K0`. Lalu uraikan byte: `[0]=ver`,
`[1]=cmd`, `[2:6]=ip`, `[6:8]=port(big-endian)`, `[8:12]=sid(ASCII)`,
`[12:16]=crc`. Tujuannya ke mana?

**L2 (dekripsi blok rantai).** Hitung `P1 = C1 ⊕ E_K(C0)` dan
`P2 = C2 ⊕ E_K(C1)`. Terbaca ASCII apa? (gabungkan P1‖P2).

**L3 (forge header).** Kamu ingin membuat frame yang mendekripsi ke header dengan
ip=10.0.0.99, port=1, ver=cmd=1, sid=`ATK0`. (a) Susun 12 byte pertama `P0'`,
(b) hitung `crc32` atas 12 byte itu dan tempel little-endian jadi `P0'` lengkap
(butuh kalkulator CRC; jawaban diberikan), (c) hitung `C0' = P0' ⊕ K0`.

**L4 (malleability).** Di request terekam, misterikan `P2` memuat `AUTH 570cc281282`.
Kalau kamu mem-flip 1 byte pertama `C2` dengan `Δ=0x20` (`C2' = C2 ⊕ 2000…00`),
jadi apa byte pertama `P2`? Dan apa yang terjadi pada `P3` (byte-byte setelahnya)?

**L5 (enkripsi 1 blok).** Kamu mau blok plaintext `P = "HELLO vault/1.0\n"`
(=`48454c4c4f207661756c742f312e300a`) jadi blok-0 sebuah stream. Hitung
`C = P ⊕ K0`. (Ini kebalikan L1.)

### Kunci jawaban

<details>
<summary>buka setelah mencoba</summary>

**L1.** `P0 = 01010a0000052328533144411f2db27d`
→ ver=1, cmd=1, ip=`0a 00 00 05`=**10.0.0.5**, port=`2328`=**9000** (vault),
sid=`53314441`=`"S1DA"`, crc=`1f2db27d`. Verifikasi: `crc32(P0[:12])=0x7db22d1f`,
little-endian = byte `1f 2d b2 7d` ✓. **Tujuan: vault 10.0.0.5:9000.**

**L2.** `P1 = 48454c4c4f207661756c742f312e300a` = `"HELLO vault/1.0\n"`.
`P2 = 41555448203537306363323831323832` = `"AUTH 570cc281282"`.
(token berlanjut di blok berikutnya.)

**L3.** (a) `P0'[:12] = 01 01 0a 00 00 63 00 01 41 54 4b 30`.
(b) `crc32 = 0xccaba597` → little-endian byte `97 a5 ab cc`, jadi
`P0' = 01010a000063000141544b3097a5abcc`.
(c) `C0' = P0' ⊕ K0 = 70c31eaa4dee05798474f614a6036de5`.

**L4.** Byte pertama `P2` semula `0x41`('A') → `0x41⊕0x20=0x61`('a'). Jadi "aUTH…".
Tapi `S3 = E_K(C2)` berubah (karena `C2` berubah) → **seluruh `P3` menjadi acak**.
Itulah efek rantai: edit di blok i menghancurkan blok i+1.

**L5.** `C = P ⊕ K0 = 398758e602ad7319b04cc90b0088f623`.
(cek: `C ⊕ K0` kembali ke `48454c…300a` ✓)

</details>

---

## 9. Mana yang manual, mana yang tidak

| Bagian | Bisa tangan? | Kenapa |
|---|---|---|
| Semua relasi XOR (§1,3,4,7) | **Ya** | hanya XOR per-byte |
| Baca/forge header, patch, prediksi efek rantai | **Ya** | konsekuensi langsung definisi CFB |
| CRC32 (hitung / koreksi affine) | setengah | linear tapi 32-bit; pakai kalkulator/skrip |
| `E_K(x)` (AES satu blok) | **Tidak** | 10 ronde AES-128; diperlakukan black box / oracle |
| Reassembly pcap | otomatis | mekanis, bukan matematis |

Intinya: **struktur serangan sepenuhnya aljabar XOR + satu black box `E_K`.**
Keamanan AES tidak disentuh; yang bobol adalah *cara pakai*-nya (IV statis, tanpa
MAC, ada reflektor plaintext). Ini pola klasik "misuse, not break".

---

## 10. Lanjutan untuk didalami (opsional)

- Buktikan sendiri: pada CTR (bukan CFB), IV/nonce statis membuat **seluruh**
  keystream dipakai ulang (`S_i` tak bergantung ciphertext), sehingga dua plaintext
  bocor via `C⁽¹⁾⊕C⁽²⁾ = P⁽¹⁾⊕P⁽²⁾`. Bandingkan kenapa CFB "hanya" blok-0.
- CRC sebagai elemen `GF(2)[x]/g(x)`: turunkan matriks `L` dan konstanta `k₀`,
  lalu lihat bahwa "fix CRC setelah flip" = satu perkalian matriks.
- Kalau `dbg` tidak ada: bisakah oracle dibangun dari balasan status vault
  (`200/400/401`) saja? (petunjuk: itu jadi soal yang jauh lebih sulit — bahan
  untuk varian "harder" di REQUIREMENT.md §8.4.)
