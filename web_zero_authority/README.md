# The Trust Protocol: Zero's Authority

## Deskripsi

Di bawah bayang-bayang jaringan Black Knights, ada satu arsip yang konon hanya boleh dibuka oleh mereka yang menyandang otoritas Zero. Tapi topeng bukanlah jaminan, ia hanyalah klaim yang dipercaya begitu saja oleh sistem yang menjaganya.

Setiap anggota punya identitas. Setiap identitas punya catatan. Dan setiap catatan... disimpan di suatu tempat yang mengaku rahasia, ditandatangani oleh sebuah kunci yang mengaku aman.

Pertanyaan sebenarnya bukan "siapa itu Zero", tapi apakah sistem benar-benar memeriksa kebenaran klaimmu, atau ia hanya percaya pada apa yang terlihat olehnya?

Buktikan bahwa kau layak menyandang otoritas itu. Temukan apa yang tertinggal, dan ambil alih kepercayaan yang seharusnya tidak pernah diberikan secuma-cuma.

All hail Britannia? Not in this archive.

## Panduan Deploy

Challenge ini berupa aplikasi Flask + SQLite, dijalankan di belakang reverse proxy Apache.

### 1. Siapkan environment

```bash
unzip zero-authority.zip
cd zero-authority
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Inisialisasi database

```bash
python init_db.py
```

Ini akan membuat `zero_authority.db` dari `schema.sql`. Jalankan ulang perintah ini kapan pun butuh reset instance ke kondisi bersih.

### 3. Jalankan aplikasi dengan Gunicorn

**Jangan** pakai `python run.py` untuk production — itu dev server dengan debug mode yang tidak aman untuk diekspos publik.

```bash
gunicorn --workers 2 --bind 127.0.0.1:5000 run:app --daemon
```

### 4. Konfigurasi Apache sebagai reverse proxy

Aktifkan module proxy:

```bash
sudo a2enmod proxy proxy_http
```

Buat virtual host (misal `/etc/apache2/sites-available/ctf.conf`):

```apache
<VirtualHost *:8000>
    ServerAdmin webmaster@localhost

    ErrorLog ${APACHE_LOG_DIR}/error.log
    CustomLog ${APACHE_LOG_DIR}/access.log combined

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
</VirtualHost>
```

Aktifkan site dan restart:

```bash
sudo a2ensite ctf.conf
sudo systemctl restart apache2
```

### 5. Verifikasi

```bash
curl -I http://127.0.0.1:8000/
curl http://127.0.0.1:8000/static/config.bak
```

Request kedua harus mengembalikan isi file berisi `SECRET_KEY` — ini jalur penemuan kunci yang dipakai peserta, pastikan tetap bisa diakses.

## Hints

**Hint 1**

> Zero selalu berkata: jejak masa lalu tidak pernah benar-benar hilang — bahkan yang seharusnya sudah dimusnahkan developer sebelum sebuah proyek rahasia diluncurkan.

**Hint 2**

> Setiap anggota Black Knights yang andal membawa daftar nama rahasia miliknya sendiri. Di dunia nyata, daftar itu punya nama: **SecLists**. Namun ingat — tidak semua daftar diciptakan sama. Carilah kategori yang menyimpan _kata_, bukan yang menyimpan _berkas_ yang sudah utuh.
