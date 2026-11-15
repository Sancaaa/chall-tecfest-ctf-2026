SCARAMEOW Server Dashboard - Drag Cat

Ganti:
web-sqli/templates/dashboard.html

Fitur:
- CPU / Memory / Disk / Network bergerak otomatis.
- GOOD < 55% = hijau.
- MEDIUM 55-79% = kuning.
- HIGH >= 80% = merah.
- CPU atau Memory HIGH memicu kucing ke tap-2x.png.
- Saat HIGH, kucing menampilkan pesan "Server high load".
- Saat kucing sedang di-drag, sprite menjadi idle.png.
- Setelah drag selesai, sprite menjadi idle-2.png.
- Saat high load, tap-2x.png tetap dipakai.
- Kucing dapat dipindahkan dengan pointer/mouse.
- Menggunakan asset:
  static/img/idle.png
  static/img/idle-2.png
  static/img/tap-2x.png
