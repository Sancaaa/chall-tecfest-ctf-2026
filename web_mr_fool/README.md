# Mr. Fool

| Parameter | Value |
|---|---|
| **Kategori** | web |
| **Author** | VascoZ |
| **Difficulty** | medium |
| **Estimasi solve** | ~30-45 menit |
| **Tested by** | Subagent Hydrogen |

## Flag

```
TecFest26{h34rtb34t_h34rtbr34k_4ll_0v3r_g4l4u_p4r4h_b4ng3t}
```

## Deskripsi (peserta)

Salin dari `challenge.yml`.

## Handout

Soal ini **blackbox**. Tidak ada source code atau artefak yang dibagikan ke peserta; seluruh attack surface harus ditemukan dari service web yang berjalan.

## Ide Soal

Rangkaian 5 mini-challenge web berantai, dibungkus sebagai "Sequence" bertema *Lord of the Mysteries*. Peserta wajib menyelesaikan Sequence 9 sampai 3 secara berurutan (state tersimpan di Flask session), lalu membuka Sequence finale (S0) yang menampilkan flag:

| Seq | Nama | Kelas Kerentanan |
|-----|------|-------------------|
| S9 | Seer | Info disclosure (robots.txt, hidden page, response header) |
| S8 | Clown | SQL injection (UNION-based, skema tabel dibocorkan pada error) |
| S7 | Magician | Mass assignment (field `approved` diterima via JSON body) |
| S6 | Faceless | Broken auth (token JWT-like tanpa verifikasi signature) |
| S3 | Scholar of Yore | Path traversal / LFI (traversal langsung ke `../secrets/lfi_token.txt`) |
| S0 | The Fool | Finale flag delivery (dibuka setelah 5 sequence tercerna) |

## Writeup

1. **S9: Seer**: Request `GET /s9/seer` mengembalikan header `X-Hint`. Buka `GET /s9/seer/robots.txt` yang melarang path `/s9/seer/hidden`. Kunjungi `/s9/seer/hidden` untuk membaca komentar HTML yang memuat token potion: `seer_sees_all`. Submit ke `POST /complete/S9`.

2. **S8: Clown**: Endpoint `POST /s8/clown/joke` mengevaluasi input user langsung ke query SQL. Skema tabel dan kolom dapat diakses di `/s8/clown/schema`. Kirim payload UNION SELECT:
   ```sql
   x' UNION SELECT id, secret_code, name FROM potion_secrets--
   ```
   Ekstrak token `laughing_error_s8` dan kirim ke `POST /complete/S8`.

3. **S7: Magician**: Endpoint `POST /s7/magician/api/spells/create` memproses pembuatan objek `Spell` dari body JSON tanpa validasi whitelist. Sertakan properti `"approved": true`:
   ```json
   {"name": "Fireball", "type": "evocation", "approved": true}
   ```
   Server merespons dengan pesan approval yang membocorkan token `unauthorized_spell`. Submit ke `POST /complete/S7`.

4. **S6: Faceless**: Token autentikasi menggunakan format sederhana `base64(payload).base64(signature)`. Server hanya membaca payload JSON dan mengecek `username == 'admin'` atau `role == 'admin'`, tanpa memverifikasi tanda tangan. Buat payload forged:
   ```json
   {"username": "admin", "role": "admin"}
   ```
   Encode payload ke base64 urlsafe, gabungkan dengan dummy signature (`.fakesig`), lalu kirim header `Authorization: Bearer <token>` ke `GET /s6/faceless/admin`. Respons memberikan token `forged_identity`. Submit ke `POST /complete/S6`.

5. **S3: Scholar of Yore**: Endpoint `GET /s3/scholar/view` menerima parameter `scroll`. Traversal path standar diperbolehkan selama berada di dalam boundary `/opt/ctf/`. Gunakan payload:
   ```
   /s3/scholar/view?scroll=../secrets/lfi_token.txt
   ```
   Server mengembalikan isi token `scholar_reading_deep`. Submit ke `POST /complete/S3`.

6. **S0: The Fool**: Setelah kelima Sequence terselesaikan, akses endpoint finale `GET /s0/fool` untuk mendapatkan flag resmi TecFest 2026:
   `TecFest26{h34rtb34t_h34rtbr34k_4ll_0v3r_g4l4u_p4r4h_b4ng3t}`.

## Solver

Solver berjalan deterministik dalam hitungan detik tanpa dependency C-extension:

```bash
pip install requests
cd solver && python solve.py http://localhost:13400
```

## Catatan Deploy

- Port default: `13400:5000` (single-container Docker `tecfest-web-mr-fool`).
- Wajib set env var `FLAG` sebelum `docker compose up`.
- State per peserta disimpan di SQLite ephemeral (`/tmp/mr_fool.db`) dan Flask session cookie.
