# I'm inside of inside of inside (Web Exploitation)

Challenge Web Exploitation untuk TecFest CTF 2026 dengan tema multi-layer perimeter traversal (SSRF ke SQL Injection pada layanan internal).

## Deskripsi Singkat

Tim operasional mengelola dashboard integrasi bernama **RelayDesk** yang menyediakan utilitas **API Connection Tester** untuk memeriksa konektivitas antar-layanan. Peserta memanfaatkan kerentanan Server-Side Request Forgery (SSRF) pada backend penguji koneksi untuk menjangkau layanan arsip internal (`archive-api.svc.local:8081`). Setelah membaca dokumentasi internal di `/docs`, peserta menemukan endpoint login `/staff/session` yang rentan terhadap SQL Injection sederhana, mengekstrak bearer token admin, dan mengambil flag rahasia dari endpoint `/staff/audit`.

## Struktur Folder

```text
I'm inside of inside of inside/
|-- challenge.yml                     # Metadata challenge untuk platform CTF
|-- README.md                         # Dokumentasi challenge
|-- im_inside_of_inside_of_inside.md  # Spesifikasi rancangan awal
|-- src/                              # Source code aplikasi dan setup Docker
|   |-- docker-compose.yml
|   |-- relaydesk-web/                # Portal publik RelayDesk (Flask, Alpine)
|   |   |-- Dockerfile
|   |   |-- requirements.txt
|   |   |-- app.py
|   |   |-- templates/
|   |   `-- static/
|   `-- archive-api/                  # Layanan arsip internal (Flask, SQLite, Alpine)
|       |-- Dockerfile
|       |-- requirements.txt
|       `-- app.py
|-- dist/                             # Berkas distribusi (kosong untuk dynamic service)
`-- solver/                           # Write-up resmi dan script exploit otomatis
    |-- README.md
    `-- solve.py
```

## Spesifikasi Teknis

- **Kategori:** Web Exploitation
- **Tingkat Kesulitan:** Medium
- **Vulnerability Chain:** SSRF -> SQL Injection -> Token Privilege Escalation
- **Stack:** Python 3.12 Alpine, Flask, Gunicorn, SQLite3
- **Ukuran Image:** Sangat ringan (~55 MB uncompressed per container, berbagi base layer Alpine yang sama)
- **Flag:** `TecFest26{wh3n_yhH_b1s4_d1_d4l3m_h4t1_ny4_d14}`

## Cara Menjalankan

Masuk ke direktori `src/` dan jalankan Docker Compose:

```bash
cd src
docker compose up --build -d
```

Akses portal RelayDesk melalui peramban: `http://localhost:8082`

Untuk menghentikan service:

```bash
docker compose down --volumes
```

## Menjalankan Solver

Jalankan script solver otomatis dari direktori `solver/`:

```bash
python solver/solve.py http://localhost:8082
```
