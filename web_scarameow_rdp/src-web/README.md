# lab-tim1-web-ready

Folder ini sudah disusun untuk dipakai sebagai service `web-sqli` pada Docker Compose.

Struktur:
- `app.py` Flask app + SQLite + intentional lab vulnerabilities
- `templates/` HTML/Jinja hasil penggabungan
- `static/css/style.css` stylesheet
- `static/js/app.js` JavaScript
- `Dockerfile`
- `requirements.txt`

Untuk dipasang ke proyek lama, backup dulu folder `web-sqli`, lalu ganti dengan folder ini.
Port tetap mengikuti compose utama (misalnya `9001:5000`).

Catatan: ini sengaja dibuat vulnerable untuk lab/CTF lokal yang kamu kontrol.
