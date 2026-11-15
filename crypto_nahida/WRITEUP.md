# Writeup — Nahida (Cryptography E)

> Dokumen author. Berisi solusi. Jangan masuk attachment/deskripsi/repo publik.

## Ringkasan
Gateway memakai AES-128-CFB128 dengan `IV = SHA256(key)[:16]` yang **statis**
dan dipakai di kedua arah. Tanpa MAC, hanya CRC32 di header. Flag hanya keluar
dari layanan `vault` yang hidup (tidak ada di `capture.pcap`). Solusi penuh ada
di [`solve.py`](solve.py) dan terverifikasi end-to-end (lihat bagian Uji).

## Primitif yang tersedia
1. **Bocor K0.** `K0 = E(IV)` = keystream blok-0. Setiap frame dengan CRC salah
   (atau tujuan tak dikenal) dibalas 16 byte nol terenkripsi = `0 ^ E(IV) = K0`.
   Cukup kirim byte sampah lalu baca 16 byte pertama balasan. Karena IV statis,
   `K0` berlaku untuk blok-0 semua stream, dua arah.
2. **Oracle `E(x)`.** Tujuan `dbg` (10.0.0.99:1) mengembalikan payload hasil
   dekripsi **tanpa enkripsi**. Kirim `C0_dbg || x || 0^16`:
   - `P1 = x ^ E(C0_dbg)` (abaikan)
   - `P2 = 0 ^ E(x) = E(x)` ← diambil
   Header dbg disusun sendiri: `C0_dbg = header_dbg ^ K0` (CRC dihitung `zlib.crc32`
   atas 12 byte pertama, little-endian). Banyak query dibatch: `x1|0|x2|0|...`,
   `E(xi)` ada di blok output ganjil (indeks 1,3,5,...).

Dengan `K0` + oracle `E()`, peserta punya **enkripsi dan dekripsi CFB penuh**:
- dekripsi: `P0 = C0 ^ K0`, `Pi = Ci ^ E(C(i-1))` — semua `C(i-1)` diketahui, jadi
  bisa dibatch sekali jalan.
- enkripsi: `C0 = P0 ^ K0`, `Ci = Pi ^ E(C(i-1))` — sekuensial.

## Langkah
1. Bocorkan `K0`.
2. Reassemble pcap, dekripsi blok-0 tiap sesi dengan `K0`, temukan sesi ke
   `10.0.0.5:9000` yang balasannya diawali `200`.
3. Dekripsi penuh request vault itu via oracle → ambil baris `AUTH <token>`.
4. Susun request sendiri: `HELLO vault/1.0` + `AUTH <token>` + `CMD flag` + `END`,
   enkripsi CFB via oracle, kirim ke gateway (tujuan vault).
5. Balasan vault diawali `200 OK vault/1.0` lalu body berisi flag; dekripsi via
   `K0` + oracle.

Flag: ada di `secrets/flag` (default `TecFest26{cfb_st4t1c_1v_plus_crc_c0llaps3s_the_wh0le_chain}`).

## Jalur alternatif (patch, bukan craft)
Replay sesi vault terekam sambil mem-flip `CMD stat`→`CMD flag` di blok CMD.
Karena rantai CFB, blok `END` berikutnya ikut rusak → vault balas `400`. Harus
diperbaiki: `C_end' = P_end_diinginkan ^ E(C_cmd')`, `E(C_cmd')` dari oracle.
Sama-sama menuntut oracle; `solve.py` memakai jalur craft karena lebih bersih.

## Mengapa Hard (dan tahan jalan pintas) — terverifikasi
`qa_negative.py` mengonfirmasi:
- Balasan error **seragam**: CRC salah == tujuan tak dikenal == `K0`. Peserta
  tidak dapat umpan balik gratis soal penyebab gagal.
- **Replay apa adanya** sesi vault → `200 OK` + body `stat`, **bukan** flag.
  Mendekripsi pcap saja tidak cukup; harus bicara ke vault yang hidup.
- **Patch naif** `stat`→`flag` tanpa perbaikan blok → `400 BAD REQUEST`. Langkah
  oracle (paham rantai CFB) memang wajib.

Pembeda dari resep "keystream reuse" biasa: CFB membuat hanya blok-0 statis;
CRC32 menggagalkan bit-flip mentah; flag hanya di respons live dan balasannya
pun rantai CFB. (Catatan: kewajiban `END` hanya menggigit di jalur patch; jalur
craft-fresh — yang dipakai solver — melewatinya. Lihat REQUIREMENT.md §12.)

## Uji
```
python gen_secrets.py          # buat secrets/
python gen_capture.py          # buat capture.pcap
PORT=13338 python server.py &  # jalankan gateway (dev lokal; deploy pakai 10501)
python solve.py 127.0.0.1 13338
```
Solver mencetak K0, token, dan flag dalam ~8 oracle call, selesai < 2 detik.

## Gerbang AI — hasil
Blackbox test menembus seluruh rantai (`blackbox_testing/WRITEUP_blackbox.md`),
jadi soal **tidak** lolos gerbang anti-AI §8.2. Keputusan: **diterima as-is**
sebagai Hard yang fair (REQUIREMENT.md §12), bukan anchor anti-AI.
