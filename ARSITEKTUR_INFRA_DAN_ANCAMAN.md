# Arsitektur Infrastruktur Lomba TecFest 2026 + Model Ancaman

> **Dokumen panitia / sensitif.** Berisi topologi jaringan, peran server, dan permukaan serangan infrastruktur lomba. Jangan dipublikasikan ke GitHub, jangan diberikan ke peserta. Sejajar dengan catatan pada `readme lab.md`.

Dokumen ini punya dua fungsi:

1. **Operasional lomba** — rancangan cara 4 node menopang CTF 20 tim (60 orang) selama 9 jam.
2. **Tugas Keamanan IoT** — bahan untuk mendemonstrasikan serangan ke infrastruktur sendiri lalu menyusun mitigasi/hardening. Nama matkul tidak membatasi target ke device ber-label IoT secara literal — 3 serangan yang disetujui (bagian 9) menyasar titik nyata di infra lomba: layanan `nc` (pola hosting paling dominan — 15 dari 22 service soal), isolasi VM shell/RCE di Proxmox 16GB, dan edge gateway VPS-A.

Semua bagian "serangan" di bawah ditulis sebagai **model ancaman defensif** (apa yang bisa terjadi + cara menahannya), bukan panduan eksekusi. Eksekusi serangan untuk tugas dilakukan sendiri di lab terkontrol milikmu.

> **Catatan pivot desain**: dokumen ini awalnya memakai desain 5-node (VPS-A 2GB + VPS-B 4GB khusus CTFd + Homelab-1 16GB + Homelab-2 8GB + Raspi5 sebagai backup). Node **VPS-B (4GB) ditunda/dicoret** — perannya (platform CTFd) digabung ke **Raspi5**, yang sebelumnya cuma backup off-site. Ini trade-off sadar: hemat 1 node, tapi menaikkan risiko Raspi5 jadi SPOF kritis (lihat bagian 8). Jaringan antar node juga pindah dari WireGuard manual ke **Tailscale** pribadi (admin: Sanca) yang sudah berjalan di semua node.

---

## 1. Inventaris 4 node

| Node | Spesifikasi | Arsitektur | IP Tailscale | Sifat | Lokasi |
|---|---|---|---|---|---|
| **VPS-A** | 2 GB RAM, 2 vCPU | x86-64 | `100.110.175.56` | Publik (IP publik di NIC-nya), edge gateway/LB/monitor, selalu online | Cloud |
| **Raspi5** | 4 GB RAM, 4 core | **ARM64** | `100.125.149.124` | Platform CTFd (live) — **bukan lagi backup off-site** | Rumah |
| **Homelab 8GB** | 8 GB RAM, 4 core | x86-64 | `100.105.142.39` | Docker host, tier aman (tanpa shell); dipakai sekarang untuk warm-up | Rumah |
| **Proxmox 16GB** | 16 GB RAM, 16 core, Proxmox | x86-64 | `100.97.230.65` | Tier berisiko tinggi (shell/RCE), VM per segmentasi; **disiapkan untuk hari-H, belum dipakai saat warm-up** | Rumah |

Dua kendala fisik yang menentukan desain (tetap berlaku):

- **Raspi5, Homelab 8GB, dan Proxmox 16GB di rumah → kemungkinan di belakang NAT/CGNAT.** Port tidak bisa langsung dibuka dari internet; semuanya terhubung ke VPS-A lewat Tailscale (mesh, bukan port-forward manual). Ini juga menyembunyikan IP rumah.
- **Raspi5 itu ARM64.** Binary PWN/RE x86 **tidak jalan native**; emulasi qemu mengubah perilaku heap/alignment sehingga exploit bisa beda. Raspi5 tidak dipakai untuk soal biner — image Docker platform (CTFd/MariaDB/Redis) sudah **diverifikasi** arm64-compatible langsung di device-nya (lihat `WebTecFest/deploy/warmup-setup/README.md` bagian 2), jadi tidak ada risiko kompatibilitas image yang tersisa di titik ini.

Domain publik: **`tecfest.site`** lewat Cloudflare — `warmup.tecfest.site` (proxied) untuk platform warm-up, `competition.tecfest.site` (proxied) untuk platform hari-H, `chall.tecfest.site` (DNS only) untuk semua soal yang butuh service, format `host:port` ala picoCTF. Detail lengkap + alasan proxied/DNS-only ada di `WebTecFest/deploy/warmup-setup/README.md` bagian 4.

---

## 2. Peran tiap node

### VPS-A (2 GB) — Edge Gateway / Load Balancer / Monitor
Pintu masuk tunggal dari internet. Tidak menyimpan data berharga, jadi aman jadi yang paling terekspos.

- **Reverse proxy** (nginx) untuk semua trafik web → diteruskan ke CTFd (Raspi5) dan ke soal web (Homelab 8GB, nanti Proxmox 16GB).
- **TCP proxy/forwarder** (nginx `stream`) untuk soal `nc`, supaya IP backend tidak pernah terlihat peserta.
- **Rate limit & connection limit** — lapis pertama pertahanan DoS (per-IP connection cap, request/detik, timeout).
- **Dua rute Tailscale aktif** sekarang — ke Raspi5 dan Homelab 8GB; rute ketiga ke Proxmox 16GB ditambahkan pas hari-H.
- **Cloudflare di depan** untuk 2 dari 3 hostname publik (`warmup.`/`competition.` — proxied, dapat WAF+DDoS shield); `chall.` sengaja DNS-only (Cloudflare tidak bisa proxy TCP mentah/port custom) — jadi VPS-A sendiri **tetap harus** keras di hardening-nya, tidak bisa mengandalkan Cloudflare untuk semua hostname.
- **`uptime-watch`** (dari `WebTecFest/deploy/uptime-watch`) berjalan di sini sebagai titik pandang utama.
- Firewall ketat + fail2ban; hanya port lomba yang terbuka.

> **Diuji untuk tugas Keamanan IoT** — lihat Serangan #3 di bagian 9.

### Raspi5 (ARM, 4 GB/4 core) — Platform CTFd (live)
Jantung lomba. Kalau ini mati, tidak ada yang bisa submit. **Ini perubahan peran terbesar dari desain awal** — sebelumnya Raspi5 cuma backup off-site (sengaja di luar jalur kritis); sekarang dia justru jadi satu-satunya tempat CTFd hidup.

- **CTFd + MariaDB + Redis** (platform `WebTecFest`), image sudah diverifikasi arm64-compatible langsung di Raspi5 (`ctfd/ctfd:3.8.8`, `redis:4`, `mariadb:10.11` ketiganya punya manifest arm64 — tidak perlu ganti image).
- Endpoint ingest monitoring anti-cheat (`/tecart-monitor/ingest`) — shipper dari server soal (Homelab 8GB & nanti Proxmox 16GB) lapor ke sini.
- **Tidak menjalankan soal apa pun** — compute soal tetap terpisah total dari database skor (prinsip isolasi dipertahankan meski node-nya berubah).
- **Risiko yang disengaja diterima**: node rumah (bukan cloud SLA — rawan listrik/internet rumah putus) dan sekarang di jalur kritis real-time (risiko kompatibilitas image arm64 sudah tidak relevan — sudah terverifikasi aman). Mitigasi minimum: UPS, `uptime-watch` dari VPS-A memantau terus-menerus, backup rutin **ke node lain** (lihat di bawah — Raspi5 tidak lagi bisa jadi backup untuk dirinya sendiri).

**Backup CTFd sekarang mengarah ke Homelab 8GB** (bukan lagi ke Pi, karena Pi-nya sendiri yang dibackup): `mysqldump` + rsync folder upload secara berkala (tiap 30–60 menit) lewat Tailscale dari Raspi5 ke Homelab 8GB. Kalau Raspi5 hilang/korup, restore ke device pengganti dari situ.

> **Diuji untuk tugas Keamanan IoT** — digabung ke Serangan #1/umum hardening platform; lihat bagian 7.B untuk model ancaman gabungan CTFd-app-layer + risiko khas perangkat kecil/rumahan.

### Homelab 8GB — Tier Aman (tanpa shell)
Soal yang tujuannya murni "dapat flag" — tidak dirancang memberi shell. Karena risikonya jauh lebih rendah, **cukup Docker biasa yang di-harden** (`cap_drop: ALL`, `read_only`, `no-new-privileges`, `pids_limit`, `mem_limit`, `cpus`) — tidak perlu Proxmox.

Dipakai **sekarang** untuk warm-up (`warmup_pwn_mona` + `warmup_web_diluc`). Hari-H nanti dipakai penuh untuk semua soal non-shell:

| Kelompok | Isi | Catatan |
|---|---|---|
| **Crypto-nc** | 6 soal Cryptography (A–F) — semua pola attachment + oracle `nc` | Ringan, stateless per koneksi |
| **Forensic-nc** | Forensic E (disk image + nc 7 pertanyaan) + 1 slot forensic lain | Slot kedua belum ditentukan di CSV (kandidat C/D/F) |
| **Misc C** | Asmoday — TCP stateless, sudah ada Dockerfile+compose ter-harden | Lihat `misc_asmoday/` |
| **Misc E** | "All-in Or Nothing" (Poker) — web | 1 container |
| **Web non-shell** | Web B (session forgery), Web C (SSRF/LFI/RFI/SQLi), Web E (Persona Overload, multi-step), Web F | Container per soal; SSRF (Web C) tetap di jaringan buntu tanpa akses internal |

Total ±14 service kecil hari-H — jauh di bawah kapasitas 8 GB. Homelab 8GB terhubung ke VPS-A lewat Tailscale (bukan WireGuard terpisah lagi — satu tailnet untuk semua).

> **Diuji untuk tugas Keamanan IoT** — lihat Serangan #1 di bagian 9 (flood/resource-exhaustion ke layanan nc).

### Proxmox 16GB — Tier Berisiko Tinggi (shell/RCE)
Semua soal yang **by-design** memberi shell atau berujung RCE/privesc. Proxmox dipakai supaya tiap kelas soal berada di **VM terpisah**, bukan sekadar container di satu OS — karena kalau salah satu ditembus, blast radius-nya harus berhenti di situ. **Belum dipakai untuk warm-up** — disiapkan khusus hari-H.

| VM | Isi | Isolasi |
|---|---|---|
| **VM-RCE** | Web D (lab Rahade, RCE → privesc root) | VM sendiri, snapshot untuk reset, **tanpa rute** ke VM lain / host / LAN rumah |
| **VM-PWN** | 6 soal Binary Exploitation via `socat ...,fork` (Nilou, Pwn B, Furina, Sandrone, Istaroth, Columbina) | Tiap koneksi = proses terpisah; tiap soal = container ter-harden (non-root, read-only, cap-drop, pids/mem limit) |
| **VM-RCE-2** | Web A (file upload → RCE) | Dipisah dari web biasa karena bisa memberi eksekusi |

Hari-H, Proxmox 16GB membuka koneksi **keluar** ke VPS-A lewat Tailscale; peserta masuk lewat VPS-A, diteruskan ke VM lewat tailnet.

> **Diuji untuk tugas Keamanan IoT** — lihat Serangan #2 di bagian 9 (validasi segmentasi/pivot) — dijalankan di clone lab, bukan di node Proxmox yang sebenarnya karena belum live dipakai.

---

## 3. Penempatan jenis soal ke node

| Jenis soal | Contoh | Node | Tingkat isolasi |
|---|---|---|---|
| Statis (attachment saja, tanpa compute) | Reverse A–F, Foren A/B/D (sebagian), Misc A/B/D/F | File di CTFd (Raspi5) | — (tak ada service) |
| `nc` oracle, tanpa shell | Crypto A–F | Homelab 8GB (Docker) | per-koneksi + limit |
| `nc` TCP, tanpa shell | Misc C Asmoday, Forensic E (+1) | Homelab 8GB (Docker) | per-koneksi + limit |
| Web, tanpa shell | Web B, C, E, F, Misc E (Poker) | Homelab 8GB (Docker) | container per soal |
| PWN, memberi shell | Nilou, Pwn B, Furina, Sandrone, Istaroth, Columbina | VM-PWN (Proxmox 16GB) | proses per-koneksi + container ter-harden |
| Web → RCE / shell | Web A (upload) | VM-RCE-2 (Proxmox 16GB) | VM/container ketat, tanpa egress |
| RCE → privesc root | Web D (lab Rahade) | VM-RCE (Proxmox 16GB) | VM penuh, snapshot reset, segmen buntu |

Attachment besar (disk image, pcap) **diberikan langsung** ke peserta (bukan via web) — tidak membebani bandwidth lomba.

Skema penomoran port untuk semua service yang dijangkau lewat `chall.tecfest.site` ada di bagian 3a.

---

## 3a. Skema penomoran port (5 digit) untuk `chall.tecfest.site`

Berlaku **cuma** untuk service yang dijangkau lewat `chall.tecfest.site:PORT` (nc & web
soal). Platform CTFd (`warmup.`/`competition.tecfest.site`) tetap standar 80/443 lewat
Cloudflare, tidak ikut skema ini.

Format: **`K CC W I`** (5 digit, selalu diisi penuh walau kategori/slot belum terpakai):

| Digit | Arti |
|---|---|
| ke-1 (`K`) | Nomor kategori, 1–6, **direserve permanen** meski kategori itu belum/tidak punya service — jaga-jaga supaya nomor tidak geser kalau nanti ditambah |
| ke-2–3 (`CC`) | Slot soal A–F dalam kategori itu (A=01 ... F=06) — slot yang **sama** dipakai baik oleh soal resmi hari-H maupun versi warm-up/latihannya; yang membedakan dua itu bukan slot, tapi digit ke-4 |
| ke-4 (`W`) | **`0`** = soal resmi hari-H, **`1`** = warm-up/latihan. Ini yang mencegah bentrok dengan soal resmi di slot sama, bukan reservasi slot terpisah |
| ke-5 (`I`) | Nomor instance — `1` default, `2` untuk mirror/duplicate (disiapkan hari-H buat jaga-jaga redundansi, belum dipakai sekarang) |

Reservasi kategori:

| Kategori | Digit `K` | Status sekarang |
|---|---|---|
| Cryptography | 1 | belum ada service warm-up |
| Forensic | 2 | belum ada service warm-up |
| Reverse Engineering | 3 | belum ada & kemungkinan tidak akan ada (semua flag attachment) — **tetap direserve** |
| Binary Exploitation (Pwn) | 4 | `warmup_pwn_mona` |
| Web Exploitation | 5 | `warmup_web_diluc` |
| Miscellaneous | 6 | belum ada service warm-up |

Port warm-up saat ini (host-side port di docker-compose & nginx — port internal
container tidak perlu ikut berubah, lihat `WebTecFest/deploy/warmup-setup/README.md`).
Slot `01` dipakai sebagai placeholder (Mona/Diluc belum terikat ke huruf A–F resmi
tertentu) — digit ke-4 = `1` yang menandai ini warm-up, bukan slot-nya:

| Soal | Kategori | Slot | Digit ke-4 | Port (skema 5 digit) |
|---|---|---|---|---|
| `warmup_pwn_mona` | Binary Exploitation (4) | 01 | 1 (warm-up) | **`40111`** |
| `warmup_web_diluc` | Web Exploitation (5) | 01 | 1 (warm-up) | **`50111`** |

Soal resmi hari-H di slot yang sama (contoh: Binary Exploitation A/Nilou) pakai
digit ke-4 = `0` → `40101` — beda dari Mona (`40111`) walau kategori+slot identik,
jadi tidak collide. Port soal hari-H (A–F resmi) lengkap ada di
`WebTecFest/deploy/competition-setup/README.md`.

---

## 4. Cara komunikasi antar node

```
Peserta (20 tim / 60 orang) ── internet ──▶ Cloudflare (tecfest.site)
                                               │ warmup./competition. = proxied   │ chall. = DNS only
                                               ▼                                   │
                                            VPS-A (edge gateway, IP publik) ◀──────┘
                                               │
      ┌─────────────────┬───────────────────────┼───────────────────────┐
      │ reverse proxy     │ TCP proxy (nc)         │ Tailscale              │ Tailscale (hari-H)
      ▼                   ▼                        ▼                        ▼
   Raspi5 (CTFd+DB)  (soal nc → via tailnet)  Homelab 8GB               Proxmox 16GB
      ▲                                       Crypto-nc / Forensic-nc /   VM-RCE / VM-PWN / VM-RCE-2
      │ backup (mysqldump/rsync, tailnet) ────▶ Asmoday / Poker / Web B,C,E,F   (belum dipakai sekarang)
      │ monitoring ingest (HTTP) ◀── shipper dari Homelab 8GB & Proxmox 16GB ───┘
```

- **Peserta hanya kenal 3 hostname di `tecfest.site`.** Semua IP backend (Raspi5, Homelab 8GB, Proxmox 16GB) disembunyikan di belakang VPS-A, dijangkau lewat IP Tailscale, tak pernah lewat internet publik langsung.
- **Tailscale** adalah satu-satunya jalan masuk ke tiap node rumah — satu tailnet untuk semuanya (beda dari desain WireGuard lama yang sengaja memisah dua tunnel independen; kontrol isolasi sekarang dipegang lewat ACL Tailscale + firewall level-NIC per node, bukan dari jumlah tunnel-nya).
- **Admin** mengelola semua node via **SSH key-only** (password login mati), lewat Tailscale (bukan port 22 terbuka ke publik).
- **Jam semua node disinkronkan (NTP)** — korelasi IP anti-cheat (`deploy/template`) bergantung pada timestamp yang seragam.

---

## 5. Strategi serve 20 tim / 60 orang

Skala ini kecil; titik tekan bukan jumlah user, tapi soal yang memberi shell — dan sekarang juga keandalan Raspi5 sebagai node rumah yang pegang platform.

- **CTFd (Raspi5):** 60 user bersamaan ringan secara RAM (4 GB cukup), tapi node rumah bukan cloud SLA — pantau lebih ketat dari biasanya lewat `uptime-watch`, siapkan UPS, dan jangan taruh soal apa pun di node ini biar resource-nya murni buat platform.
- **Soal statis & nc (Homelab 8GB):** stateless, aman dipakai bersama; `socat fork` + `ulimit` + `timeout` per koneksi (pola Asmoday) mencegah satu orang menahan resource. 14 service kecil ini jauh di bawah kapasitas 8 GB.
- **Instance bersama, bukan per-tim (Proxmox 16GB, hari-H).** Sesuai keputusan sebelumnya (waktu terbatas, tanpa instancing dinamis / flag dinamis). Konsekuensi diterima: satu tim bisa merusak state tim lain pada soal shell → mitigasi = **skrip reset cepat** (snapshot rollback / `compose down && up`) dijalankan manual lewat Open Ticket.
- **Web D** (paling destruktif): kalau sempat, batasi jadi 6–8 instance hidup bersamaan dengan idle-destroy; kalau tidak, satu instance bersama + reset manual.
- **Rate limit di VPS-A** menahan satu tim/AI yang memborbardir request (sekaligus lapis anti-DoS); untuk `warmup.`/`competition.` ada lapis tambahan dari Cloudflare, untuk `chall.` (DNS only) murni mengandalkan hardening VPS-A sendiri.

---

## 6. Backup & ketahanan

| Risiko | Dampak | Penanganan |
|---|---|---|
| Raspi5 (CTFd) mati | Lomba berhenti total — **risiko ini naik** dibanding desain VPS-B lama karena sekarang node rumah, bukan cloud (image arm64 sudah terverifikasi aman, bukan lagi sumber risiko) | Backup DB+upload tiap 30–60 mnt ke Homelab 8GB; dokumentasikan langkah restore sebelum hari-H; UPS di rumah |
| Listrik/internet rumah putus | Soal di Homelab 8GB/Proxmox 16GB hilang, **atau platform CTFd sendiri hilang** (karena sekarang juga di rumah — bukan lagi cuma soal) | UPS untuk tiap node rumah; `uptime-watch` dari VPS-A deteksi cepat; restore CTFd dari backup Homelab 8GB kalau Raspi5 benar-benar tumbang |
| Satu soal shell rusak oleh peserta | Soal itu tak bisa dikerjakan | Snapshot per VM (Proxmox 16GB); skrip reset; alert `uptime-watch` → restart |
| Tunnel Tailscale/VPS-A tumbang | Semua akses putus | `uptime-watch` tetap lokal di VPS-A; pertimbangkan instance `uptime-watch` kedua di Homelab 8GB sebagai jalur pandang alternatif (menggantikan peran "jalur-2 di Pi" dari desain lama, karena Pi sekarang bukan lagi node independen dari jalur kritis) |
| **Homelab 8GB down** (listrik/jaringan rumah) | Soal "aman" (crypto/forensic-nc/web ringan/misc) turun | Platform CTFd (Raspi5) **tidak terdampak** — submission tetap jalan, cuma soal yang kena; `uptime-watch` mendeteksi via Tailscale |
| **Proxmox 16GB down**, atau insiden isolasi (percobaan VM escape dari soal shell) — hari-H | Pwn + Web A + Web D turun/terkunci | Homelab 8GB & platform **tidak terdampak** — ini alasan utama tier dipisah fisik, bukan cuma VM |

Backup CTFd juga wajib **sebelum lomba** dan **setelah freeze** (sudah ada di checklist `CHALLENGE_DAN_HOSTING.md`).

---

## 7. Model ancaman — permukaan serangan per titik

Dikelompokkan per lokasi. Tiap baris: **ancaman → target → mitigasi/hardening**. Ini daftar untuk pertahanan; bukan instruksi menyerang.

### A. Di Edge (VPS-A)
| Ancaman | Mitigasi / Hardening |
|---|---|
| **DDoS volumetrik / flood koneksi** (SYN flood, connection exhaustion) menjatuhkan 2 GB VPS | SYN cookies, connection cap per-IP, `conn_limit`/`req_limit` nginx, timeout agresif; Cloudflare proxied menambah lapis untuk `warmup.`/`competition.`, tapi `chall.` (DNS only) **tidak terlindungi Cloudflare** — murni mengandalkan hardening VPS-A |
| **Slowloris / slow-read** (app-layer, hemat bandwidth tapi mematikan) | Timeout header/body ketat, batas koneksi idle, `mod_reqtimeout`/setelan setara |
| **Port scan / enumerasi** gateway | Hanya buka port lomba; tutup sisanya; fail2ban untuk pola abusive |
| **Brute force SSH** ke gateway | Key-only, password mati, akses lewat Tailscale (bukan port 22 publik), fail2ban |

> **Diuji untuk tugas Keamanan IoT** — lihat Serangan #3 di bagian 9. Karena `chall.tecfest.site` tidak lewat Cloudflare, uji ini paling representatif kalau diarahkan ke hostname/IP yang setara `chall.` (atau IP publik VPS-A langsung), bukan ke `warmup.`/`competition.` yang sudah terlindungi Cloudflare — kalau diarahkan ke situ, yang teruji sebagian besar Cloudflare, bukan hardening VPS-A sendiri.

### B. Platform CTFd (Raspi5) — gabungan risiko aplikasi + risiko perangkat rumahan
Digabung dari desain lama (dulu platform di VPS-B cloud dan Raspi5 cuma backup — sekarang satu node, jadi dua kelas risiko ini sekarang menumpuk di tempat yang sama).

| Ancaman | Mitigasi / Hardening |
|---|---|
| **Brute force / credential stuffing** ke login admin & tim | Password admin kuat + ganti default (`admin/admin123`), rate-limit login, 2FA bila tersedia |
| **Abuse upload solver** (plugin `tecart_capture`): file besar, tipe berbahaya, path traversal, XSS tersimpan di link AI | Batas 64 MB (sudah ada), simpan di luar webroot, sajikan `Content-Disposition: attachment` + `nosniff`, jangan pernah eksekusi, escape tampilan link, download admin-only |
| **Serangan plugin kustom** (`tecart_capture`/`tecart_extras`) via input tak tervalidasi | Review validasi input plugin, jalankan test suite, patch CTFd rutin |
| **API abuse / scraping scoreboard** | Rate limit, token admin dijaga |
| **Pemalsuan skor / replay submit** | CSRF bawaan CTFd, snapshot scoring, log submission |
| **Kredensial default / lemah di OS Raspi5** (user `pi`, SSH terbuka) — pola klasik perangkat IoT, sekarang relevan langsung ke platform | Ganti user & password default, SSH key-only via Tailscale, nonaktifkan layanan tak perlu |
| **OS/firmware Raspi5 usang** jarang dipatch | `apt upgrade` berkala, matikan service default yang tak dipakai |
| **Raspi5 sebagai pijakan ke jaringan rumah** kalau tersusupi | Raspi5 di segmen Tailscale terbatas (ACL); tidak menyimpan kunci produksi lain selain punyanya sendiri |
| **Backup (sekarang di Homelab 8GB) tak terenkripsi** berisi dump DB lomba | Enkripsi volume/backup, akses terbatas ke Homelab 8GB |

> Tidak termasuk 3 serangan resmi tugas (nc lebih representatif untuk infra ini) — opsional kalau waktu masih ada, lihat penutup bagian 9.

### C. Proxmox 16GB — soal yang memberi shell (VM-RCE / VM-PWN / VM-RCE-2), hari-H
| Ancaman | Mitigasi / Hardening |
|---|---|
| **Pivot pasca-shell**: peserta pakai shell soal untuk menyerang soal lain, host, atau DB lomba | Segmentasi jaringan — VM soal **tak punya rute** ke CTFd/DB/host/VM lain; egress jaringan dimatikan setelah build |
| **Container/VM escape** (exploit kernel, misconfig, docker socket terekspos) | Boundary VM untuk risiko tertinggi (Web D root); **jangan** mount `docker.sock`; kernel host dipatch; seccomp/AppArmor, user namespace, `no-new-privileges`, `cap-drop ALL` |
| **Bocor flag antar-soal** | Flag hanya terbaca setelah exploit yang dimaksud; tiap soal jaringan & filesystem terpisah |
| **Reverse shell keluar** (shell dipakai menyerang target luar / internet) | Egress ditutup total dari VM soal; firewall level-NIC Proxmox (tak bisa dilewati dari dalam VM) |
| **Resource abuse** (fork bomb, crypto-miner di dalam shell) | `pids-limit`, `mem-limit`, `cpus`, timeout sesi (pola `socat ... timeout`) |

> **Diuji untuk tugas Keamanan IoT** — lihat Serangan #2 di bagian 9 (validasi segmentasi/pivot), dijalankan di clone lab karena node ini belum live dipakai.

### C2. Homelab 8GB — soal tanpa shell (crypto-nc, forensic-nc, web ringan, Asmoday, Poker)
Risiko jauh lebih rendah (tidak ada yang *by-design* memberi shell), tapi tetap relevan:

| Ancaman | Mitigasi / Hardening |
|---|---|
| **SSRF by-design (Web C)** diarahkan ke layanan internal / metadata cloud | Jaringan buntu; blokir akses ke `169.254.169.254` dan subnet internal |
| **Resource exhaustion per container** (banyak koneksi oracle crypto/nc bersamaan) | `pids_limit`/`mem_limit`/`cpus` per container, connection cap per-IP (pola Asmoday) |
| **Session/cookie tampering** (Web B session forgery adalah goal soal, tapi jangan sampai bisa dipakai menyerang sesi tim lain yang tak terkait soal) | `HttpOnly`/`Secure` di cookie non-soal, session ID acak panjang, scoped per-request |
| **Satu tim "pinjam" state tim lain** (webshell/file dari Web A pola serupa, state lomba, dsb di soal multi-step Web E) | Nama file/temp acak per sesi, bukan predictable; folder dibersihkan berkala |

> **Diuji untuk tugas Keamanan IoT** — lihat Serangan #1 di bagian 9 (flood/resource-exhaustion ke layanan nc).

### D. Jaringan rumah (Raspi5, Homelab 8GB, Proxmox 16GB)
| Ancaman | Mitigasi / Hardening |
|---|---|
| **Lateral movement ke LAN pribadi** — breakout soal menjangkau perangkat rumah | VM/container soal di bridge/VLAN terisolasi; **tanpa rute** ke LAN rumah maupun antarmuka manajemen Proxmox |
| **Kompromi node/kunci Tailscale** → akses ke jaringan rumah | ACL Tailscale dibatasi per-node (cuma port/soal yang perlu bisa saling akses), auth key tidak di repo/image, revoke+re-auth kalau ada indikasi bocor |
| **Serangan ke host Proxmox** (web UI 8006, SSH) | UI Proxmox tidak terekspos ke internet, hanya via Tailscale; update rutin |

### E. Rantai pasok & rahasia (lintas node)
| Ancaman | Mitigasi / Hardening |
|---|---|
| **Flag/secret terbawa ke image atau repo** (flag di image, DB creds, Tailscale auth key) | `.dockerignore` (sudah di Asmoday), `.env` di-gitignore, flag lewat env bukan di-build, rotasi |
| **Base image jahat/usang** | Pin versi, image minimal, sumber tepercaya |

---

## 8. Ringkasan: SPOF & risiko terbesar infra ini

1. **Raspi5 (CTFd, live)** — SPOF terbesar sekarang. Satu-satunya titik yang kalau mati menghentikan seluruh lomba, **dan** sekarang node rumah (bukan cloud SLA) **dan** sekaligus target empuk khas IoT (kredensial default, firmware) — risiko kompatibilitas image arm64 sudah tidak berlaku lagi (terverifikasi aman). Dua risiko yang dulu terpisah (SPOF platform di VPS-B cloud, risiko rumah di Pi yang di luar jalur kritis) sekarang menumpuk jadi satu. Backup + rencana restore ke Homelab 8GB wajib matang.
2. **VPS-A (gateway)** — pintu tunggal; target DDoS paling masuk akal karena RAM kecil, dan satu-satunya yang menanggung penuh `chall.tecfest.site` tanpa bantuan Cloudflare.
3. **Web D (privesc root) & Istaroth (shell)** — bahaya terkontrol terbesar; butuh isolasi VM & segmentasi paling ketat, keduanya di Proxmox 16GB (hari-H, belum live sekarang jadi belum jadi risiko aktif).
4. **Jaringan rumah (Raspi5, Homelab 8GB, Proxmox 16GB)** — breakout soal yang lolos bisa menyentuh perangkat pribadi; risiko yang tidak ada kalau semua di cloud, dan sekarang mencakup platform juga, bukan cuma soal.
5. **Homelab 8GB bukan SPOF baru** — justru mengurangi dampak kalau Proxmox 16GB (hari-H) ada insiden, karena dua tier risiko soal tetap terpisah fisik meski platform-nya sendiri sekarang jadi SPOF tunggal di Raspi5.

---

## 9. Untuk tugas Keamanan IoT — 3 serangan yang disetujui

Tugas minta serangan ke infrastruktur lalu mitigasi/hardening. Sempat didesain sekitar Raspberry Pi (karena nama matkul), tapi dikonfirmasi boleh menyasar infra yang lebih luas — jadi 3 serangan di bawah ini dipilih karena paling relevan dengan desain nyata di dokumen ini, bukan cuma device kecil. **Serangan #1 sengaja diarahkan ke layanan `nc`** karena itu pola hosting paling dominan di seluruh infra (15 dari 22 service soal: 6 crypto, 2 forensic, 6 pwn, Asmoday) — kalau cuma uji edge dan VM shell, bagian terbesar dari permukaan serangan justru tidak tersentuh. Semua dijalankan di **lab terkontrol/clone milikmu sendiri**, bukan ke infra lomba yang sedang live, dan sebaiknya **sebelum Homelab/Raspi5 mulai dipakai aktif untuk warm-up/lomba**.

### Serangan #1 — Flood / resource-exhaustion ke layanan `nc`, target Homelab 8GB
Menguji ketahanan pola hosting yang dipakai di hampir semua soal (crypto oracle, forensic nc, Asmoday) terhadap banyak koneksi bersamaan — bukan DoS ke jaringan, tapi ke *resource per-proses* (fork per koneksi, tanpa limit).

- Deploy klon satu soal nc sederhana (oracle crypto, atau langsung `misc_asmoday/server.py` versi **belum** di-harden — hapus dulu `ConnectionLimiter`/limit compose-nya untuk simulasi "before").
- Buka banyak koneksi paralel (loop `nc`/skrip Python `socket`) tanpa henti.
- **Before** (tanpa connection-cap per-IP/total, tanpa `pids_limit`/`mem_limit`): service hang, koneksi baru/tim lain tidak bisa masuk, atau proses menumpuk sampai memori/PID habis.
- **After**: terapkan ulang pola Asmoday yang sudah ada — `ConnectionLimiter` (`MAX_CONN_PER_IP`, `MAX_CONN_TOTAL`) + `pids_limit`/`mem_limit`/`cpus` di compose + `timeout` per koneksi (bagian 7.C2) → service tetap menerima koneksi tim lain walau satu IP membanjiri.

### Serangan #2 — Validasi segmentasi (pivot test), target Proxmox 16GB
Menguji apakah klaim "VM soal tanpa rute ke VM lain/CTFd/host" di bagian 7.C benar-benar berlaku, bukan cuma asumsi desain. Dijalankan di clone lab karena node Proxmox yang sebenarnya belum live dipakai untuk warm-up.

- Deploy satu soal Pwn/RCE (klon Istaroth atau Web D) di clone lab setara Proxmox 16GB.
- Dari shell yang didapat: coba scan jaringan internal, coba konek ke IP mewakili Raspi5 (CTFd), coba akses VM lain di Proxmox yang sama, coba egress ke internet.
- **Before** (tanpa firewall NIC/segmentasi): pivot/egress berhasil.
- **After** (firewall NIC Proxmox + egress-off + VLAN terisolasi, sesuai bagian 7.C & 10): semua percobaan gagal/timeout.

### Serangan #3 — Stress test / DDoS, target VPS-A (edge gateway)
VPS-A adalah SPOF #2 (RAM kecil, pintu masuk tunggal) — ini satu-satunya yang menyasar lapisan jaringan/edge, melengkapi #1 (resource per-proses di backend) dan #2 (isolasi internal).

- Jalankan flood/slow-connection (misal `slowhttptest` untuk slowloris, `hping3` untuk SYN flood ringan) ke endpoint reverse proxy-nya — arahkan ke hostname/IP yang **tidak** lewat Cloudflare (setara `chall.tecfest.site`, atau IP publik VPS-A langsung), bukan ke `warmup.`/`competition.` yang sudah terlindungi Cloudflare, supaya yang teruji benar hardening VPS-A sendiri.
- **Before**: tanpa rate-limit/connection-cap → service goyang/down dengan traffic kecil.
- **After**: `fail2ban` + `limit_conn`/`limit_req` nginx + SYN cookies (bagian 7.A) → tetap responsif di beban yang sama. Ukur request/sec, latency, availability.

Fokus laporan pada **arsitektur before/after** untuk ketiganya: tunjukkan permukaan serangan dari bagian 7 pada kondisi "sebelum hardening", lalu terapkan mitigasi dan tunjukkan permukaan yang sama tertutup. Diagram pendamping (`diagram_arsitektur_ancaman.html`) bisa dipakai sebagai lampiran.

**Bonus opsional (tidak wajib)**: abuse test ke upload solver/link AI plugin `tecart_capture` (bagian 7.B) — kalau waktu masih ada setelah 3 serangan di atas, bisa jadi temuan ke-4 sekaligus review keamanan gratis untuk fitur yang dipakai beneran saat lomba.

---

## 10. Checklist hardening sebelum lomba

- [ ] VPS-A: firewall default-deny, hanya port lomba; rate/connection limit; fail2ban; SSH key-only lewat Tailscale
- [ ] Cloudflare: `warmup.`/`competition.tecfest.site` proxied + SSL mode Flexible; `chall.tecfest.site` DNS only (sengaja, lihat bagian 4 README warmup-setup)
- [x] Raspi5: image arm64 terverifikasi (`ctfd/ctfd:3.8.8`, `redis:4`, `mariadb:10.11`)
- [ ] Raspi5: ganti semua kredensial default CTFd & DB; backup terjadwal ke Homelab 8GB; test restore; UPS
- [ ] Proxmox 16GB (hari-H): tiap kelas soal di VM terpisah; firewall NIC Proxmox; UI Proxmox tak terekspos ke internet
- [ ] Homelab 8GB: container ter-harden (non-root, read-only, cap-drop ALL, no-new-privileges, pids/mem/cpu limit) untuk tiap soal; tak perlu Proxmox
- [ ] VM/container soal shell (Proxmox 16GB, hari-H): non-root, read-only FS, `cap-drop ALL`, `no-new-privileges`, egress mati, pids/mem/cpu limit, bukan mount docker.sock
- [ ] Segmentasi: VM/container soal tak punya rute ke CTFd/DB/host/LAN rumah/satu sama lain
- [ ] Tailscale: ACL dibatasi per-node (cuma yang perlu saling akses), auth key di luar repo, revoke+re-auth kalau ada indikasi bocor
- [ ] NTP sinkron di semua node (untuk korelasi anti-cheat)
- [ ] `uptime-watch` jalan di VPS-A; pertimbangkan instance kedua di Homelab 8GB sebagai jalur pandang alternatif
- [ ] Rencana reset per soal shell terdokumentasi (snapshot / compose)
- [ ] 3 serangan tugas Keamanan IoT (bagian 9) sudah dijalankan & didokumentasikan di lab clone, **sebelum** Homelab/Raspi5 dipakai aktif untuk warm-up
