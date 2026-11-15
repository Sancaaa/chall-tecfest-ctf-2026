# Rancangan Soal CTF Web Exploitation

## 1. Identitas Challenge

| Komponen | Detail |
|---|---|
| **Nama** | **I'm inside of inside of inside** |
| **Kategori** | Web Exploitation |
| **Tingkat kesulitan** | Medium |
| **Kerentanan utama** | Server-Side Request Forgery (SSRF) → SQL Injection (SQLi) |
| **Tipe SQLi** | Login bypass sederhana |
| **Flag** | `TecFest26{wh3n_yhH_b1s4_d1_d4l3m_h4t1_ny4_d14}` |
| **Target penyelesaian** | Menemukan layanan internal melalui SSRF, melakukan bypass login admin melalui SQLi, lalu menggunakan token admin untuk membaca flag |

> **Catatan panitia:** Dokumen ini adalah *design specification* internal. Jangan menyertakannya di lingkungan yang bisa diakses peserta. Deskripsi publik ada di bagian 2.

## 2. Deskripsi Challenge untuk Peserta

**I'm inside of inside of inside**

> Tim operasional sedang kesulitan memeriksa integrasi antar-layanan. Sebuah alat pengecek koneksi API disediakan agar pekerjaan mereka lebih mudah. Katanya, data internal tetap aman karena tidak bisa diakses dari luar. Ada catatan yang seharusnya tidak bisa kamu lihat. Bisakah kamu menemukannya?

**Diberikan:** URL website challenge. Tidak ada source code, kredensial, atau file tambahan.

**Tidak dicantumkan kepada peserta:** nama kerentanan, nama host internal, nama endpoint login, ataupun format token.

## 3. Konsep dan Intended Attack Chain

Tema *inside of inside of inside* menggambarkan perpindahan ke tiga lapisan akses:

1. **Luar:** website publik menyediakan alat pengecek koneksi API.
2. **Dalam:** SSRF memungkinkan server publik menghubungi layanan arsip yang hanya tersedia di jaringan internal.
3. **Lebih dalam:** SQLi pada autentikasi layanan internal menghasilkan hak admin; tokennya membuka data audit yang menyimpan flag.

```text
[Browser Peserta]
       |
       v
[Website Publik: RelayDesk]
  - halaman status integrasi
  - dokumentasi koneksi
  - fitur API Connection Tester
       |
       | SSRF via POST /api/check
       v
[Internal Service: archive-api.svc.local:8081]
  GET  /               → indeks / petunjuk dokumentasi
  GET  /docs           → kontrak API (tanpa password/token)
  POST /staff/session  → login rentan SQLi
       |
       | SQLi bypass → bearer token admin
       v
  GET  /staff/audit    → butuh Authorization: Bearer <token>
       |
       v
  Flag
```

**Syarat desain:** layanan internal *tidak dipublikasikan* melalui reverse proxy atau host port. Seluruh komunikasi ke layanan itu harus melalui fitur SSRF pada website publik. Login SQLi dilakukan lewat SSRF juga, bukan langsung dari browser peserta.

## 4. Desain Website Publik (RelayDesk)

### 4.1. Halaman dan fitur

| Halaman / endpoint | Fungsi | Informasi yang terlihat |
|---|---|---|
| `GET /` | Dashboard integrasi | Status koneksi, tautan ke penguji API, Status, dan Bantuan |
| `GET /tools/connection` | Form API Connection Tester | URL target, method `GET`/`POST`, headers, dan raw body |
| `POST /api/check` | Backend melakukan request ke URL pilihan pengguna | Status HTTP, headers yang aman ditampilkan, body respons, dan pesan error singkat |
| `GET /status` | Status integrasi | Menampilkan **alias** service `archive-api`, tetapi **bukan** URL lengkap |
| `GET /help/networking` | Bantuan konfigurasi | Menyebut konvensi host privat `*.svc.local` dan port `8081` untuk layanan arsip |

**Tujuan:** peserta perlu menggabungkan informasi dari **Status** dan **Bantuan** untuk membentuk `http://archive-api.svc.local:8081`. Kedua halaman dapat diakses melalui navigasi UI; jangan menuntut tebak path tanpa clue.

### 4.2. SSRF yang disengaja

API Connection Tester menerima input seperti berikut:

```http
POST /api/check HTTP/1.1
Content-Type: application/json

{
  "url": "http://archive-api.svc.local:8081/",
  "method": "GET",
  "headers": {
    "Accept": "application/json"
  },
  "body": ""
}
```

**Perilaku backend (vulnerable by design):**

- Server membuat HTTP request ke URL yang disuplai pengguna.
- Tidak ada pemblokiran host privat atau hostname jaringan internal sehingga terjadi SSRF.
- Method yang diizinkan: `GET` dan `POST`.
- Headers yang dapat diteruskan: minimal `Accept`, `Content-Type`, dan `Authorization`.
- Raw body diteruskan sesuai input; ini penting agar peserta dapat mengirim payload SQLi ke login internal.
- Hasil request dicerminkan ke pengguna dalam bentuk `status`, `body`, dan sebagian header. Respons **jangan hanya menampilkan “connection successful”**, karena peserta harus bisa membaca dokumen internal serta token hasil login.
- Hanya skema `http://` dan `https://` yang didukung; skema file/gopher tidak diperlukan untuk intended solution.
- Redirect boleh dinonaktifkan agar perilaku konsisten; tidak ada tahapan yang memerlukan redirect.
- Gunakan timeout, batas ukuran respons, dan rate limit yang wajar, tanpa membuat tahapan intended solution gagal.

Contoh tampilan respons tester:

```json
{
  "status": 200,
  "headers": {"content-type": "application/json"},
  "body": "{\"service\":\"Archive API\",\"docs\":\"/docs\"}"
}
```

**Kenapa fitur ini dipilih:** jika hanya menggunakan URL/image preview GET-only, peserta mungkin tidak bisa mengirim request `POST` dan header `Authorization` yang dibutuhkan tahap SQLi serta pengambilan flag. API Connection Tester menyelesaikan persoalan itu secara natural.

## 5. Desain Layanan Internal

**Hostname internal:** `archive-api.svc.local`  
**Port:** `8081`  
**Network:** hanya dapat diakses oleh container website publik melalui Docker network privat.

### 5.1. Daftar endpoint

| Method | Endpoint | Akses | Respons penting |
|---|---|---|---|
| `GET` | `/` | Internal tanpa autentikasi | Metadata service dan link `/docs` |
| `GET` | `/docs` | Internal tanpa autentikasi | Dokumentasi `POST /staff/session` dan `GET /staff/audit` |
| `POST` | `/staff/session` | Internal tanpa autentikasi | Jika berhasil, mengembalikan bearer token |
| `GET` | `/staff/audit` | Internal + role admin | Menampilkan catatan audit berisi flag |

Contoh `GET /`:

```json
{
  "service": "Archive API",
  "version": "1.2",
  "documentation": "/docs",
  "message": "Staff access required for audit records."
}
```

Konten `/docs` menunjukkan format login dengan field `username` dan `password`, tetapi tidak memberikan payload SQLi, kredensial, atau token. Contoh akun pada dokumen boleh memakai `admin` sebagai nama pengguna agar tidak ada tahap username guessing yang tidak perlu.

### 5.2. Kerentanan SQLi di login

Input login berupa JSON:

```json
{
  "username": "admin",
  "password": "example-password"
}
```

**Contoh implementasi yang sengaja rentan (SQLite):**

```sql
SELECT id, username, role
FROM users
WHERE username = '${username}' AND password = '${password}'
LIMIT 1;
```

Server menyusun query dengan interpolasi string **tanpa parameterized query**. Peserta dapat melakukan bypass sederhana pada kolom `username`.

**Contoh payload intended:**

```text
username: admin' -- 
password: bebas
```

Payload mengomentari pemeriksaan password. Dengan username `admin` yang memang ada, hasil query mengarah ke akun admin tanpa bergantung pada urutan baris. Bentuk SQLi umum lain boleh berhasil jika memang sesuai semantik query; jangan menambahkan blacklist khusus hanya untuk memaksa satu payload tertentu.

### 5.3. Token dan autentikasi

Setelah login menghasilkan record admin, endpoint merespons:

```json
{
  "access_token": "<token-acak-per-instance>",
  "token_type": "Bearer",
  "role": "admin"
}
```

**Aturan penting:**

- Token dikeluarkan oleh layanan internal dan dapat digunakan sebagai `Authorization: Bearer <token>`.
- Token harus diverifikasi server-side dan diasosiasikan dengan identitas + role akun yang berhasil login.
- Jangan mengandalkan cookie browser karena respons login diterima oleh backend SSRF, bukan oleh browser peserta.
- Token boleh berupa string acak yang tersimpan di memori server dan berlaku selama instance hidup. Tidak perlu sistem JWT kompleks untuk challenge ini.
- Akses ke `/staff/audit` tanpa token: `401`. Dengan token non-admin: `403`. Dengan token admin valid: `200`.

### 5.4. Penyimpanan flag

Flag hanya muncul di respons sukses `GET /staff/audit` ketika header Authorization mengandung token admin valid.

Contoh respons:

```json
{
  "record_id": "AUDIT-026",
  "classification": "internal",
  "note": "TecFest26{wh3n_yhH_b1s4_d1_d4l3m_h4t1_ny4_d14}"
}
```

Simpan nilai sebenarnya melalui environment variable **di container internal** (mis. `FLAG`) lalu injeksikan ke respons handler. Jangan memasukkan flag ke JavaScript publik, source map, HTML, log, `/docs`, atau contoh konfigurasi yang terbuka untuk peserta.

## 6. Walkthrough Intended Solution (Khusus Panitia)

**Langkah 1 — Recon publik.** Peserta membuka website, menemukan fitur API Connection Tester, lalu membaca Status (`archive-api`) dan Bantuan (`*.svc.local`, port `8081`).

**Langkah 2 — Validasi SSRF.** Peserta memasukkan `http://archive-api.svc.local:8081/` ke Connection Tester. Respons dari internal service terlihat di hasil pengujian. Endpoint tidak dapat diakses secara langsung dari internet.

**Langkah 3 — Enumerasi terarah.** Dari respons indeks, peserta menuju `/docs` lewat SSRF. Dokumentasi memperlihatkan endpoint autentikasi `/staff/session` dan endpoint audit `/staff/audit`.

**Langkah 4 — SQLi login bypass.** Peserta mengirim `POST` via Connection Tester ke `/staff/session` dengan header `Content-Type: application/json` dan body misalnya:

```json
{
  "username": "admin' -- ",
  "password": "anything"
}
```

Server login internal mengembalikan bearer token admin.

**Langkah 5 — Ambil flag.** Peserta mengirim `GET` via Connection Tester ke `http://archive-api.svc.local:8081/staff/audit` dengan header:

```http
Authorization: Bearer <access_token-dari-langkah-4>
```

Respons memuat flag `TecFest26{wh3n_yhH_b1s4_d1_d4l3m_h4t1_ny4_d14}`.

**Catatan:** contoh-contoh di bagian ini adalah untuk QA internal. Jangan ditampilkan kepada peserta.

## 7. Petunjuk Bertahap (*Optional Hint Release*)

Tidak semua hint harus dibuka sejak awal. Jika panitia ingin menyediakan hint setelah challenge berjalan, gunakan urutan berikut:

1. **Hint 1 (ringan):** “Saat melakukan tes koneksi, dari mana sebenarnya request tersebut dikirim?”
2. **Hint 2 (sedang):** “Status integrasi dan dokumentasi jaringan punya informasi yang saling melengkapi.”
3. **Hint 3 (kuat):** “Masuk ke layanan internal saja belum cukup; perhatikan bagaimana autentikasinya memproses input.”

Hindari hint publik yang menyebut host internal lengkap, payload SQLi, atau lokasi flag secara eksplisit. **Tidak perlu fake flag, direktori acak berlapis, atau melarang perintah `ls`.** Itu tidak meningkatkan kualitas SSRF → SQLi chain.

## 8. Mengurangi Risiko *One-Shot Solve* oleh AI Agent

Tujuan realistisnya **bukan** membuat challenge mustahil dipecahkan AI, melainkan menuntut eksplorasi HTTP dan penggabungan bukti sebelum chain berhasil.

**Disarankan:**

- Informasi hostname internal dipisah menjadi **alias** di halaman Status dan **pola DNS/port** di halaman Bantuan, keduanya tetap mudah ditemukan manusia.
- URL endpoint internal tidak tersimpan lengkap di HTML atau JavaScript publik.
- Endpoint login dan audit baru dapat diketahui secara wajar setelah SSRF menuju service internal dan membaca `/docs`.
- SQLi sengaja sederhana, tetapi baru bisa dijalankan setelah memahami bahwa API Tester mendukung POST, body, dan custom header.
- Token diperoleh secara dinamis melalui autentikasi dan tidak diberikan sebagai konstanta di source frontend.

**Jangan dilakukan:**

- Memasang prompt injection untuk “mengelabui AI” sebagai mekanisme keamanan atau syarat solve.
- Membuat puzzle path guessing panjang tanpa petunjuk, blacklist SQLi arbitrer, atau puluhan fake flag.
- Menambahkan CAPTCHA yang menghambat peserta normal namun bisa dibypass oleh otomatisasi lain.
- Menganggap satu AI gagal solve sebagai bukti soal pasti Medium.

**Kalibrasi:** lakukan blind test dengan setidaknya dua peserta manusia yang memahami dasar HTTP/SQLi serta satu AI agent yang hanya diberi URL + deskripsi publik. Catat apakah mereka menemukan intended chain, bagian yang membuat tersesat, dan keberadaan bypass tak disengaja. Ubah clue bila discovery terlalu mudah atau terlalu bergantung pada tebakan.

## 9. Arsitektur Deployment dan Isolasi

Rekomendasi minimal: **dua container aplikasi** dalam satu jaringan khusus challenge.

```text
Internet
   |
   v
[reverse proxy / port publik]
   |
   v
[relaydesk-web :3000] ------- [Docker network privat]
                                       |
                                       v
                           [archive-api :8081]
                           [SQLite lokal/container]
                           [FLAG dari env internal]
```

Implementasi Docker Compose dapat menggunakan dua network: `edge` untuk trafik ke aplikasi publik dan `challenge_private` dengan `internal: true` untuk komunikasi ke `archive-api`.

**Ketentuan deployment:**

- Hanya `relaydesk-web` yang mempunyai port yang dipublikasikan; `archive-api` **tidak memiliki `ports:`**.
- Beri `archive-api` alias DNS `archive-api.svc.local` di network privat.
- `relaydesk-web` terhubung ke network yang diperlukan agar bisa menerima trafik publik dan menjangkau internal service.
- Batasi outbound SSRF di tingkat jaringan challenge agar tidak menjangkau internet bebas, host, metadata cloud, atau container layanan lain milik panitia.
- Jangan gunakan Docker socket mount, `network_mode: host`, atau container `privileged`.
- Jalankan proses non-root, batasi CPU/memori/koneksi dan ukuran request/response. Pertimbangkan `read_only`, `tmpfs`, dan `no-new-privileges` sesuai kebutuhan runtime.
- Database SQLi bersifat lokal dan berisi akun fiktif. Jangan menyambungkannya dengan database sistem lomba yang asli.
- Gunakan instance terpisah per tim jika memungkinkan. Jika memakai shared instance, pastikan token dan state tidak menyebabkan satu tim bisa mengganggu tim lain.

**Catatan teknis:** `internal: true` membantu membatasi konektivitas keluar dari Docker network, tetapi jangan menganggapnya otomatis cukup untuk melindungi setiap host atau layanan lain pada server. Uji aturan jaringan di host dan lakukan verifikasi dari dalam container.

## 10. Checklist Pengujian Sebelum Rilis

### Validasi intended solution

- [ ] Website publik bisa diakses tanpa akses ke alamat internal secara langsung.
- [ ] Halaman Status dan Bantuan sama-sama ditemukan lewat navigasi biasa.
- [ ] Backend API Tester bisa melakukan GET dan membaca body JSON internal.
- [ ] Backend API Tester bisa meneruskan POST, JSON body, serta header `Content-Type`.
- [ ] Login dengan password salah ditolak.
- [ ] Login menggunakan SQLi sederhana `admin' -- ` berhasil sebagai admin.
- [ ] Response login memunculkan token di output API Tester.
- [ ] API Tester bisa meneruskan header `Authorization` ke endpoint audit.
- [ ] Endpoint audit tanpa token menghasilkan `401`, dan token bukan admin menghasilkan `403`.
- [ ] Token admin valid mengembalikan flag yang **persis** sesuai format.

### Uji bypass / unintended solve

- [ ] Flag tidak muncul pada source HTML/JS, source map, static asset, atau halaman dokumentasi.
- [ ] Flag tidak tersedia lewat `/flag.txt`, `/robots.txt`, URL publik lain, atau error trace.
- [ ] Endpoint internal tidak bisa diakses langsung dari internet, termasuk lewat reverse proxy yang salah konfigurasi.
- [ ] Endpoint audit tidak bisa dibuka tanpa autentikasi meskipun dipanggil lewat SSRF.
- [ ] SQLi tidak memberi akses baca file, command execution, ataupun akses database di luar instance challenge.
- [ ] URL Tester tidak bisa mengakses host/hypervisor, Docker API, cloud metadata, atau layanan panitia lain.
- [ ] API Tester tetap bisa menyelesaikan alur intended sesudah rate limit dan pengamanan deployment diterapkan.

## 11. Kesimpulan Desain

**Kesulitan target: Medium**, karena peserta harus mengidentifikasi SSRF, menemukan tujuan internal lewat dua petunjuk yang masuk akal, memanfaatkan SSRF untuk request POST login, lalu memakai bearer token yang diperoleh agar bisa mengambil flag lewat SSRF lagi.

SQLi tidak dibuat sulit: bypass satu kondisi autentikasi sudah cukup. Tantangan utamanya adalah memahami **boundary jaringan dan alur request HTTP**. Tingkat kesulitan final perlu divalidasi lewat playtest, bukan hanya dari jumlah tahap atau banyaknya endpoint.
