# NativeNote (dibungkus jadi "Joker's Flagged Confession")

| Parameter | Value |
|---|---|
| **Kategori** | Web Exploitation, slot E |
| **Author** | LeleWeb |
| **Difficulty** | Hard |
| **Port kompetisi** | `50501` (skema `K CC W I` = kategori 5, slot E=05, resmi=0, instance=1) — Homelab 8GB |

## Asal berkas

Diadaptasi dari submission `NativeNote.zip` (asal author: Dimas Maulana, format
`challenge.yml` ala rCTF/rCDS dengan `DynamicContainer` + flag per-tim). Diubah untuk
cocok dengan infra TecFest (CTFd 3.8.8, flag statis dibagi semua tim, deploy Docker
Compose biasa, bukan container-per-tim):

- `flagTemplate` per-tim (`TechFest26{..._[TEAM_HASH]}`, ada typo `TechFest`) diganti
  **flag statis** `TecFest26{pr0t0_p0llut10n_m33ts_ut1l_1nsp3ct_rc3}`, di-set lewat
  env `RSCTF_FLAG` di `docker-compose.yml` (variabel ini sudah dibaca `start.sh`
  bawaan, tidak perlu ubah source).
- Compose asli (Traefik label + domain wildcard + sidecar `tcpdump`/tulip) dibuang,
  diganti `docker-compose.yml` satu service dengan port host `50501` sesuai skema
  proyek ini.
- Tidak ada source code yang dibagikan ke peserta (blackbox, sama seperti soal Web
  lain) — `ctfd_desc.md` murni cerita + alamat service.

Menggantikan slot **Web E milik Rahade** yang sebelumnya kosong/placeholder
("In Progress", belum ada konten) — lihat `CHALLENGE_DAN_HOSTING.md` §1.3 dan
`Challenge CTF TecFest 2026 - Chall.csv` baris Web/E. **Tidak** menyentuh slot Web F
(lab pentest Rahade yang lain, masih "Not Started").

## Flag

```
TecFest26{pr0t0_p0llut10n_m33ts_ut1l_1nsp3ct_rc3}
```

## Vulnerability chain

1. **Stored XSS** — `templates/note.html` merender `{{ content | safe }}` tanpa
   escaping. Script di note berjalan verbatim saat bot (Electron) membuka halamannya.
2. **Electron misconfig** — `bot/main.js` membuat `BrowserWindow` dengan
   `contextIsolation: false`. Renderer dan preload share satu V8 heap yang sama.
3. **Gadget baru: `Object.prototype[util.inspect.custom]`** — preload punya crash
   reporter yang memanggil `util.inspect({ runtime: process, ... })`. Simbol
   `Symbol.for('nodejs.util.inspect.custom')` ada di global registry Node, jadi
   renderer bisa mendefinisikan fungsi di `Object.prototype` untuk key itu.
   `util.inspect` manapun lalu memanggil fungsi tsb dengan `this` = objek yang
   sedang di-inspect — termasuk `process` itu sendiri saat rekursi sampai di sana.
4. Dari `this = process`, panggil `process.binding('process_wrap').Process` (kelas
   native yang sama dipakai `ChildProcess` di Node) lalu `.spawn()` untuk eksekusi
   `cat /flag` ke file output yang bisa diambil lewat `/out/<id>.html`.

Solver referensi (untuk QA, bukan dibagikan ke peserta): [`solver/solve.py`](solver/solve.py),
penjelasan lengkap di [`solver/writeup.md`](solver/writeup.md).

## Catatan deploy

- Image berbasis `node:20-bookworm` + Xvfb + Electron headless (`--no-sandbox`,
  `--disable-gpu`) untuk menjalankan bot reviewer di dalam container yang sama
  dengan Flask app (`start.sh` menjalankan Xvfb lalu `app.py`; `app.py` men-spawn
  Electron per `/report`).
- Butuh resource lebih besar dari web chall lain (Chromium headless) — compose
  sudah dinaikkan ke `mem_limit: 1024m`, `pids_limit: 512`.
- `cap_drop: ALL` + `cap_add: SYS_ADMIN` + `seccomp=unconfined` dipakai supaya
  Chromium headless tetap bisa jalan tanpa named user-namespace sandbox penuh (sudah
  `--no-sandbox` di level Electron, tapi Xvfb/Chromium butuh sedikit syscall yang
  diblokir default seccomp Docker).
- `src/start.sh` sempat ikut ter-copy dengan CRLF karena di-copy dari filesystem
  Windows → `exec: /app/start.sh: not found` saat container start (shebang
  `#!/bin/sh\r` tidak ditemukan). Sudah dinormalisasi ke LF di repo ini.

## Status validasi (lokal, Windows + Docker Desktop/WSL2)

- `docker compose build` + `up -d` di port `50501`: **sukses**, healthcheck `healthy`.
- Solver referensi (`solver/solve.py http://localhost:50501`) dijalankan end-to-end:
  register → login → buat note exploit → `/report` → bot Electron membuka note →
  prototype-pollution trigger → RCE → `cat /flag` → flag `TecFest26{pr0t0_p0llut10n_m33ts_ut1l_1nsp3ct_rc3}`
  berhasil terbaca lewat `/out/<id>.html`. Chain terkonfirmasi end-to-end.
- Resource idle: ~60MB RAM, <0.1% CPU, 5 PID — jauh di bawah limit (`mem_limit: 1024m`,
  `pids_limit: 512`).
- **Belum** dites lawan node Homelab 8GB sebenarnya — seccomp/kernel profile di sana
  bisa berbeda dari Docker Desktop/WSL2, cek ulang `cap_add: SYS_ADMIN` +
  `seccomp=unconfined` sebelum hari-H.
