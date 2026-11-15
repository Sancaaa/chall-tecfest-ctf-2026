# Requirement — Ronova (Cryptography F, Hard)

> **Dokumen author. JANGAN dibagikan ke peserta.** Berisi desain dan intended solution.
> Status kebenaran tetap di `../Challenge CTF TecFest 2026 - Chall.csv` (filter `Author = SancaPWN`).
> Author: Sanca (`SancaPWN`). Dibuat 5 Nov 2026. Diperbarui 15 Nov 2026.

> **STATUS KEPUTUSAN (15 Nov 2026).** Ronova **diterima sebagai Hard "teknik dikenal, eksekusi bersih"**, BUKAN soal anti-AI. Uji blackbox dari 4 file attachment (lihat `blackbox_test/`) membuktikan soal ini **solvable ~2 detik dengan LLL biasa** (scaling per-kolom + recentering + Kannan embedding, python-flint) — target "tidak bisa 2–3 shot AI" **TIDAK tercapai**, dan itu kita terima. Beban anti-AI dipikul **Nahida (Cryptography E)**. Koreksi: klaim lama "butuh BKZ / solver naive gagal" (Bagian 3 & 6) keliru — berasal dari pembanding strawman (tanpa recentering/bobot); sudah dikoreksi di bawah. Catatan file: attachment convo sekarang `session-*.jsonl` (bukan `chat-ai.txt`); folder peserta ada di `dist/`. Bagian 8–9 yang masih menyebut `chat-ai.txt` / "uji one-shot wajib gagal" sudah usang.

---

## 1. Ringkasan

| Hal | Nilai |
|---|---|
| Kategori / slot | Cryptography F |
| Difficulty | Hard |
| Topik | ECDSA biased nonce → Hidden Number Problem → lattice (LLL/BKZ) |
| Butuh service | **Tidak.** Murni attachment, offline. Aman dari larangan scanning/fuzzing. |
| Flag | `TecFest26{...}` (tetapkan di CSV, jangan di sini) |
| Attachment peserta | `capture.json` (data tanda tangan) + `chat-ai.txt` (convo AI) + `flag.enc` |
| File author | `gen.sage`, `solve.sage`, `WRITEUP.md`, `kunci.txt` |

**Satu kalimat:** peserta diberi banyak tanda tangan ECDSA yang nonce-nya bocor sebagian lewat sebuah sinyal sampingan, harus menyaring tanda tangan yang tepat, menyusun lattice HNP berbobot, menjalankan reduksi lattice untuk memulihkan private key, lalu mendekripsi flag.

---

## 2. Kenapa harus lebih sulit dari soal crypto lain

Lineup crypto TecFest:

| Slot | Topik | Serangan |
|---|---|---|
| A (Easy) | Encoding & XOR berlapis | manual |
| C (Medium) | RSA Common Modulus | satu rumus (Bézout) |
| E (Hard) | RSA Partial `d` (LSB leaked) | Coppersmith / lattice RSA |
| **F (Hard)** | **ECDSA biased nonce** | **HNP + lattice, multi-langkah** |

E dan F sama-sama Hard dan sama-sama lattice. Supaya F terasa sebagai puncak kategori, F harus menuntut **lebih dari sekadar menjalankan satu solver**: peserta harus menafsirkan sumber bias, menyaring data, lalu menyetel lattice sendiri. Lihat bagian 4.

---

## 3. Ancaman model: AI boleh dipakai (dan realitasnya)

Guidebook mengizinkan model whitelist (GPT-5.6 Instant, Claude Sonnet 5.5, Gemini 3.6 Flash, DeepSeek-V3.2) **tanpa agent/MCP**. Target desain awal adalah "tidak bisa selesai dalam 2–3 prompt".

### 3.1 Realitas: target itu TIDAK tercapai, dan kita terima

Biased-nonce ECDSA → HNP → lattice adalah salah satu serangan crypto CTF **paling terkenal** (repo publik `joflucki/ecdsa-attacks` bahkan ada di folder ini). Model frontier mengenalinya seketika, dan `session-*.jsonl` memang sengaja menyerahkan kerentanannya (nonce pendek + `hint` = panjang bit). Uji blackbox di `blackbox_test/` membuktikan: dari 4 file saja, solver standar (saring `hint` kecil → lattice **scaling per-kolom + recentering** → **LLL biasa**) memulihkan `d` dan membuka flag dalam **~2 detik**. Jadi Ronova **praktis one-shot** untuk solver kompeten.

Keputusan: **terima** Ronova sebagai Hard teknik-dikenal (eksekusi bersih, write-up bagus), dan serahkan properti anti-AI ke **Nahida (slot E)** yang dirancang sebagai rantai non-textbook. Dua slot Hard crypto tidak harus dua-duanya tahan AI.

### 3.2 Koreksi klaim lama (penting untuk tidak diulang)

Draf sebelumnya mengklaim "lima lever anti one-shot", terutama bahwa **butuh BKZ** dan "solver naive gagal". **Itu keliru.** Klaim itu lahir dari pembanding strawman: solver "naive" yang diuji memakai `B` seragam **dan tanpa recentering**, jadi wajar gagal. Solver kompeten memakai **scaling per-kolom + recentering** (higiene lattice standar) dan **LLL biasa sudah cukup** — BKZ tak perlu. Tidak ada "tembok BKZ". Jangan jadikan recentering/scaling sebagai andalan kesulitan; keduanya diketahui semua solver.

> Bagian 4–7 di bawah tetap berlaku sebagai **deskripsi desain** (cara data dibuat, kurva, format). Yang gugur hanya narasi "anti-AI"-nya.

---

## 4. Spesifikasi teknis

### 4.1 Kurva

- **Gunakan secp256k1 atau P-256** (256-bit), bukan P-384. Dua alasan: (a) menjauh dari template repo kuliah; (b) 256-bit membuat lattice lebih kecil sehingga BKZ cepat, jadi peserta yang benar tetap bisa solve < 1 menit.
- Parameter kurva ditulis lengkap di attachment supaya tidak ada tebak-tebakan.

### 4.2 Pembuatan nonce (inti kerentanan)

Nonce **tidak** seragam. Usulan: RNG cacat yang menghasilkan nonce dengan **panjang bit bervariasi dan sebagian besar pendek**, meniru RNG yang gagal mengisi byte teratas. Contoh pola (final ditentukan saat build):

```
# cacat: hanya mengisi sejumlah byte acak, sisanya nol → panjang bit bocor
nbytes = pilih_dari_distribusi_berat_ke_kecil()   # mis. sering 24–28 byte dari 32
k = int.from_bytes(os.urandom(nbytes), "big")
```

- Yang bocor = **panjang bit** `k` (karena byte atas nol). Ini yang menjadikannya HNP.
- Distribusi dibuat agar hanya sebagian tanda tangan yang nonce-nya cukup pendek untuk berguna → memaksa langkah penyaringan.
- **Jangan** sampai ada dua nonce identik (nonce reuse) — itu jalan pintas non-lattice. Cek saat generate.

### 4.3 Sinyal sampingan (pengganti timing Minerva)

Tiap entri di `capture.json` menyertakan field yang **berkorelasi** dengan panjang nonce tapi tidak langsung membocorkannya, misalnya penghitung iterasi internal atau "seed length hint" yang masuk akal dari cerita soal (lihat tema di 4.6). Peserta memakai field ini untuk memilih ~60–80 tanda tangan dengan nonce terpendek. **Bukan** `elapsed_ns`.

### 4.4 Data yang diberikan ke peserta (`capture.json`)

```json
{
  "curve": "secp256k1",
  "G": [gx, gy], "n": ..., "p": ...,
  "public_key": [qx, qy],
  "signatures": [
    {"h": ..., "r": ..., "s": ..., "hint": ...},
    ... (banyak, mis. 1200–1600 entri)
  ]
}
```

- `h` = hash pesan (sertakan `h` langsung supaya tidak ada ambiguitas skema hash).
- `hint` = sinyal sampingan dari 4.3.
- Public key diberikan supaya peserta bisa memverifikasi kandidat kunci (`d·G == Q`).

### 4.5 Enkripsi flag (`flag.enc`)

- Kunci AES = `SHA256(d_bytes)` dengan `d` private key. Tanpa `d`, flag tertutup → tidak ada solve tanpa lattice.
- Simpan `flag.enc` + sedikit metadata (IV/mode) sehingga begitu `d` ketemu, dekripsi lugas.

### 4.6 Attachment `chat-ai.txt` (convo AI)

Isi: percakapan "developer × AI" yang membocorkan cara nonce dibuat, dibungkus narasi Ronova. Syarat:

- Menampilkan potongan kode RNG cacat (4.2) **tanpa** menjelaskan eksploitasinya.
- AI dalam percakapan **tidak** menyebut "hidden number problem" atau "lattice" — kalau disebut, peserta tinggal menyalin. Cukup sampai "fungsi sign-nya begini, nonce-nya begitu".
- Tujuannya memberi peserta bahan untuk **menyimpulkan** berapa bit bocor dan bagaimana `hint` berhubungan dengan panjang nonce.

---

## 5. Intended solution (ringkas, untuk author)

1. Baca `chat-ai.txt`, simpulkan nonce dibuat dari byte acak sebagian → byte atas nol → panjang bit `k` bocor, dan `hint` menandai nonce pendek.
2. Dari `capture.json`, untuk tiap sig: `t_i = r_i · s_i⁻¹`, `a_i = h_i · s_i⁻¹ (mod n)`, sehingga `k_i ≡ a_i + t_i · d (mod n)`.
3. Urutkan berdasarkan `hint`, ambil subset nonce terpendek (mis. 60–80).
4. Susun lattice HNP **berbobot per-kolom** (skala `2^{bit_i}` berbeda tiap kolom, gaya Minerva) — bukan satu `B` seragam.
5. Reduksi: BKZ block size naik bertahap `[5,15,20,...,50]`, cek tiap baris hasil; terima `d` bila `d·G == Q` atau `(n−d)·G == Q`.
6. `key = SHA256(d)`, dekripsi `flag.enc`.

Detail penuh + skrip di `solve.sage` dan `WRITEUP.md` (dibuat saat build).

---

## 6. Parameter (TERUKUR, prototipe jalan)

Prototipe `gen.sage` + `solve.sage` sudah dibuat dan diuji (Sage 10.7, secp256k1).

| Parameter | Nilai terpakai | Catatan |
|---|---|---|
| Kurva | secp256k1 (256-bit) | tetap |
| Total tanda tangan | 1500 | hanya ~80 berguna → memaksa penyaringan |
| Subset pendek disuntik | 80 | solver memakai 70 terpendek |
| Bias (bit bocor di subset) | **5–13 bit** (nonce 243–251 bit) | sengaja tipis, dekat margin |
| Reduksi | **LLL biasa sudah cukup** | scaling per-kolom + recentering; BKZ tak perlu |

**Hasil uji (terverifikasi, lihat `blackbox_test/`):**
- Solver standar (saring `hint≤252`, ~100 sig, lattice scaling+recentering, **LLL** via python-flint): **berhasil ~2 detik**, `d` cocok `d·G=public_key`, flag terbuka.
- `solve.sage` (versi lama, berbobot + BKZ): juga berhasil, tapi BKZ-nya **tidak diperlukan** — LLL sudah cukup.
- Klaim lama "solver naive gagal" sudah dicoret (Bagian 3.2): pembandingnya strawman tanpa recentering.

> **Tombol kesulitan hanya menggeser biaya, bukan membuat tahan-AI.** Mengecilkan bias (`SHORT_BITS`) atau `M_SEL` menaikkan dimensi/compute, tapi solver tinggal naik ke BKZ — serangannya tetap teknik dikenal. Jangan berharap tuning menjadikannya anti-one-shot.

### 6.1 Sisa pekerjaan sebelum final (prototipe → soal lomba)
- [ ] Ganti `FLAG` placeholder di `gen.sage` dengan flag asli; catat di CSV (bukan di repo).
- [ ] Hapus `set_random_seed` / pakai seed rahasia untuk data lomba.
- [ ] Perhalus `chat-ai.txt` (masih placeholder) — pastikan tak menyebut "HNP"/"lattice".
- [ ] `hint` saat ini = panjang bit `k` persis. Pertimbangkan beri derau ringan agar lebih realistis (akan mempersulit solver — uji ulang bila diubah).
- [ ] Uji one-shot ke model whitelist (Bagian 9).

---

## 7. Checklist anti unintended-solve

- [ ] Tidak ada nonce reuse (dua `r` sama) — jalan pintas non-lattice.
- [ ] `d` tidak kecil, tidak dekat `n`.
- [ ] Flag tidak bisa didapat tanpa `d` (kunci AES = KDF(`d`)).
- [ ] Tidak ada byte teratas nol yang terbaca langsung dari `r`/`s` (bias hanya di `k`, bukan bocor eksplisit).
- [ ] Solver seragam (satu `B`, LLL polos, pakai semua sig) **gagal** — konfirmasi dengan menjalankannya.
- [ ] Solver benar **berhasil** di ≥5 seed berbeda.

---

## 8. Deliverables & tata letak folder author

```
crypto_ronova/
├── REQUIREMENT_RONOVA.md      (dokumen ini)
├── gen.sage                   (generator: kunci, tanda tangan cacat, enkripsi flag, tulis attachment)
├── solve.sage                 (intended solver, end-to-end)
├── WRITEUP.md                 (langkah solve + penjelasan lattice)
├── kunci.txt                  (d + flag, author only)
└── attachment/                (yang dibagikan ke peserta)
    ├── capture.json
    ├── chat-ai.txt
    └── flag.enc
```

`attachment/` harus bersih: tanpa `d`, tanpa solver, tanpa path lokal, tanpa `.git`.

---

## 9. Definition of done (map ke checklist 1.6 CHALLENGE_DAN_HOSTING)

- [ ] Nama, topik, kategori, difficulty di CSV sesuai slot Crypto F.
- [ ] Deskripsi peserta ditulis (tanpa bocor solusi).
- [ ] Flag `TecFest26{...}` tercatat di kolom `Flag` CSV.
- [ ] Intended solution di kolom `Intended Solution` CSV.
- [ ] `solve.sage` jalan end-to-end, diverifikasi ≥5 seed.
- [ ] Attachment bersih (bagian 8).
- [ ] **Tester bukan author** berhasil solve hanya dari attachment + deskripsi.
- [ ] **Uji one-shot AI:** tempel `capture.json` + `chat-ai.txt` ke tiap model whitelist, 2–3 prompt. Harus **gagal**. Kalau tembus, kecilkan bias / perbanyak noise / kurangi petunjuk di convo.
- [ ] Hint bertingkat disiapkan (mis. "perhatikan field hint" → "panjang nonce bervariasi" → "Hidden Number Problem berbobot").
- [ ] Dipasang ke CTFd tipe `tecart`, dites ulang dari akun peserta.

---

## 10. Pertanyaan terbuka untuk Sanca

1. Kurva: secp256k1 atau P-256? (Saya condong secp256k1 — lebih sering muncul di CTF, beda dari repo kuliah yang P-384.)
2. Sinyal sampingan `hint` dibungkus sebagai apa dalam narasi Ronova? (penghitung iterasi? "panjang seed"? sesuatu yang in-universe.)
3. Ronova masuk Wave 1 atau Wave 2, dan apakah salah satu dari 5 Bounty First Blood?
4. Nilai poin (mengikuti difficulty Hard).
