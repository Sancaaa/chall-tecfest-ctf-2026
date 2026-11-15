# All-in Or Nothing

Challenge kategori **Misc (Web-Based)** untuk **TecFest CTF 2026** bertema judi poker dengan gaya visual **Persona 5 Royal**.

## Menjalankan Challenge

```bash
cd src
docker compose up --build -d
```

Web dapat diakses di `http://localhost:13500`.

Untuk menghentikan:

```bash
cd src
docker compose down --volumes
```

## Ringkasan Dua Solusi
1. **Cara Orang Gila (Path 1)**: Menang murni **10 ronde poker berturut-turut** di meja Simplified Heads-Up Texas Hold'em tanpa kalah atau fold.
2. **Intended Solution (Path 2 — Blackmail & Perang Psikologis)**:
   - Ungkap 4 aib pribadi dealer Reynaldi melalui investigasi misc (`/robots.txt` -> `/staff/shift-receipt`, `audit_memo_b64` di `/api/table/state`, `<metadata>` ROT13 di `/static/assets/dealer_badge.svg`, dan log Hex di `/logs/vault-audit`).
   - Klik **HOLD UP!** di UI, pilih taktik psikologis yang tepat, dan serahkan keempat kode bukti untuk menjatuhkan mental Reynaldi hingga `0%`.
