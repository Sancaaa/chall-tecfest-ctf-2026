# Warm-up Web Exploitation — Diluc

**Author:** SancaPWN
**Difficulty:** Warm-up (sangat mudah)

## Konsep

Static site 3 file (`index.html`, `style.css`, `script.js`), masing-masing menyimpan
1 bagian flag di komentar. Tidak ada vulnerability sungguhan — murni latihan "View Page
Source" / DevTools Network & Sources tab, pemanasan sebelum chall Web beneran yang butuh
exploitasi server-side.

## Intended Solution

1. Buka halaman, klik kanan -> View Page Source -> lihat komentar HTML:
   `<!-- Flag part 1/3: TecFest26{DP5_d1Luc_ -->`
2. Buka DevTools -> Sources/Network -> buka `style.css`, baris pertama komentar:
   `/* Flag part 2/3: pAl1Ng_ */`
3. Buka `script.js`, baris pertama komentar: `// Flag part 3/3: 5AK1t}`
4. Gabungkan ketiganya berurutan.

## Flag

`TecFest26{DP5_d1Luc_pAl1Ng_5AK1t}`

## File author

- `site/` — isi web (identik dengan yang di-deploy), termasuk `site/dawn-winery.jpg`
  (screenshot Dawn Winery dari Genshin Impact, dipakai sebagai hero banner)
- `Dockerfile`, `docker-compose.yml` — hosting (nginx:alpine static)
- `flag.txt` — flag asli (jangan di-upload; tidak dipakai server, flag ada langsung di source)

## Revisi desain (2026-11-08)

Ditambah hero banner pakai gambar Dawn Winery (`dawn-winery.jpg`) dengan overlay
gradient gelap + judul & tagline menumpuk di atasnya (CSS `position: absolute` +
`object-fit: cover`), lalu card deskripsi di bawahnya. Fragmen flag di
HTML/CSS/JS **tidak diubah** (posisi dan isinya tetap sama persis).

Bug yang ditemukan & difix saat testing lewat Docker: `.hero-overlay` sempat pakai
shorthand CSS `inset: 0` yang entah kenapa tidak ke-apply di browser pane yang
dipakai untuk preview (computed style balik ke `position: static`) — diganti ke
`top/right/bottom/left: 0` eksplisit, langsung normal. `.hero` juga diubah dari
`max-height` ke `height` tetap + `object-fit: cover` di `<img>` supaya gambar
konsisten dipotong rapi di rasio berapa pun layar peserta.

Saat verifikasi visual, browser pane sempat nge-cache versi lama `index.html`/
`style.css` secara persisten walau server sudah menyajikan versi baru (dikonfirmasi
lewat `curl` dan `fetch(..., {cache:'no-store'})` langsung ke container — selalu
benar). Workaround: akses lewat `http://localhost:8090` alih-alih
`http://127.0.0.1:8090` (key cache browser beda per hostname). Ini murni masalah
cache tool preview, bukan bug di web yang di-deploy.

## Hasil test Docker (2026-11-08)

- `docker compose up -d --build` awalnya **gagal** (`Restarting`, crash loop):
  `cap_drop: ALL` membuat entrypoint `nginx:alpine` resmi tidak bisa `chown
  /var/cache/nginx/client_temp` ke user `nginx` (uid 101) -> `Operation not permitted`.
  Fix: tambah `cap_add: [CHOWN, SETUID, SETGID]` (minimal yang dibutuhkan proses
  master nginx untuk setup cache dir lalu drop privilege ke worker non-root),
  `cap_drop: ALL` tetap dipertahankan untuk capability lainnya.
- Setelah fix: container `Up` stabil, `GET /index.html`, `/style.css`, `/script.js`
  semua `200 OK` lewat `curl` ke `127.0.0.1:8090`, isi persis sama dengan `site/`.
  `GET /nonexistent.txt` -> `404` (bukan directory listing). File di dalam container
  read-only untuk semua user (`-r-xr-xr-x`, tidak ada bit `w`).
