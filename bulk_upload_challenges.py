#!/usr/bin/env python3
"""Bulk-upload challenge ke CTFd (type `tecart`) lewat REST API, dari 1 CSV.

Dibuat buat rehearsal di instance staging (port 8887, Tailscale-only, lihat
docker-compose.staging.yml) SEBELUM dipakai ke instance kompetisi beneran
(8889) -- target --url harus instance staging dulu.

Cara deskripsi + attachment digabung (meniru persis alur Admin Panel CTFd):
  1. Challenge dibuat dulu (butuh id-nya buat upload file).
  2. Setiap file di kolom `attachments` diupload ke
     POST /api/v1/files (field `challenge`=id), CTFd balas path penyimpanan
     asli (`location`, misal `38c8e69a.../coverJean.jpg`).
  3. Isi `desc_file` (markdown biasa) dibaca, lalu setiap placeholder
     `{{FILE:nama_file}}` di dalamnya diganti jadi `/files/<location>` yang
     sebenarnya -- INI SEBABNYA deskripsi final tidak bisa ditulis langsung
     di CSV: path `/files/<hash>/...` baru ada SETELAH upload.
  4. Deskripsi yang sudah disubstitusi di-PATCH ke challenge.
  5. Flag dan sampai 3 hint (hint_1..hint_3, cost selalu 0 -- hint
     berbayar/>3 hint silakan tambah manual lewat Admin Panel) dibuat.

Contoh isi file utk kolom `desc_file` (lihat example_desc/crypto_jean.md):

    ![coverJean.jpg]({{FILE:coverJean.jpg}})

    Jean dancok sangat emosi sama klee...

    Download [enc.py]({{FILE:enc.py}}) dan [output.enc]({{FILE:output.enc}})
    (lihat cara & key enkripsinya), lalu balikkan.

Kolom CSV (header wajib, urutan bebas) -- lihat challenges_upload.csv:
    category, name, desc_file, attachments, type, function, value,
    initial, decay, minimum, flag, flag_case_insensitive,
    hint_1, hint_2, hint_3, author, connection_info, wave, state

Default kalau sel kosong: type=tecart, function=snapshot, initial=500,
decay=50, minimum=100, state=hidden, flag_case_insensitive=no. `wave` murni
catatan panitia (tidak dikirim ke CTFd apa pun) -- dipakai sendiri buat
melacak baris mana untuk Wave 1 / Wave 2.

Idempoten per nama challenge: kalau nama sudah ada di CTFd target, baris
dilewati (tidak dibuat dobel). TAPI kalau sebelumnya gagal di tengah (misal
challenge kebuat tapi upload file gagal), baris itu juga akan "dianggap
sudah ada" dan dilewati -- hapus manual challenge yang setengah jadi itu
dari Admin Panel baru rerun barisnya. Makanya rehearsal di staging (8887)
dulu, bukan langsung ke 8889.

Mode:
  --dry-run   cuma cek nama yang akan dibuat/dilewati, TIDAK panggil API
  (default)   upload beneran ke --url

Usage:
    python bulk_upload_challenges.py challenges_upload.csv --dry-run
    python bulk_upload_challenges.py challenges_upload.csv --url http://100.125.149.124:8887 --token <TOKEN>

Stdlib saja (konsisten dengan stress_test.py / generate_team_creds.py).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

REQUIRED_COLUMNS = {"category", "name"}
FIELDNAMES = [
    "category", "name", "desc_file", "attachments", "type", "function",
    "value", "initial", "decay", "minimum", "flag", "flag_case_insensitive",
    "hint_1", "hint_2", "hint_3", "author", "connection_info", "wave", "state",
]

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

FILE_PLACEHOLDER = re.compile(r"\{\{FILE:([^}]+)\}\}")


def load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def _request(method, url, token, timeout, json_body=None, data_bytes=None, content_type=None):
    headers = {"Authorization": f"Token {token}", "User-Agent": BROWSER_UA}
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif data_bytes is not None:
        data = data_bytes
        headers["Content-Type"] = content_type
    else:
        # GET tanpa body (misal list_existing_challenge_names): CTFd cuma
        # memproses header Authorization di before_request `tokens()` kalau
        # `request.is_json` True (CTFd/utils/initialization/__init__.py) --
        # itu dicek dari Content-Type, bukan dari ada/tidaknya body. Tanpa
        # header ini, token admin diam-diam dianggap anonymous dan endpoint
        # yang digerbang @check_challenge_visibility redirect ke halaman
        # login (HTML, status 200) bukan balikin JSON. Bukan bug di CTFd
        # untuk kasus normal (browser admin selalu login via session cookie,
        # bukan token), tapi kena kalau API token dipakai buat GET polos.
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return True, json.loads(raw)
            except json.JSONDecodeError:
                # Status 200 tapi bukan JSON (misal keredirect ke halaman
                # login/setup HTML) -- balikin potongan raw body-nya biar
                # kelihatan kenapa, bukan crash tanpa info.
                snippet = raw[:300].replace("\n", "\\n")
                return False, f"respons bukan JSON (status 200): {snippet!r}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = f"HTTP {e.code}: {body[:300].replace(chr(10), '\\n')!r}"
        return False, body
    except urllib.error.URLError as e:
        return False, str(e.reason)


def _multipart_body(fields: dict, file_field: str, filename: str, filedata: bytes):
    boundary = uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n"
        ).encode("utf-8")
    body += (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
        f"filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    body += filedata
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def read_rows(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"Kolom wajib tidak ada di CSV: {', '.join(sorted(missing))}")
        return [row for row in reader if (row.get("name") or "").strip()]


def list_existing_challenge_names(base_url: str, token: str, timeout: float) -> dict:
    ok, resp = _request("GET", f"{base_url.rstrip('/')}/api/v1/challenges", token, timeout)
    if not ok or not isinstance(resp, dict):
        print(f"[WARNING] gagal ambil daftar challenge yang sudah ada: {resp}", file=sys.stderr)
        print("[WARNING] lanjut dengan asumsi belum ada challenge -- cek --url/--token kalau ini salah", file=sys.stderr)
        return {}
    return {c["name"]: c["id"] for c in resp.get("data", []) if "name" in c}


def create_challenge(base_url, token, timeout, row) -> int:
    initial = int(row.get("initial") or 500)
    decay = int(row.get("decay") or 50)
    minimum = int(row.get("minimum") or 100)
    function = (row.get("function") or "snapshot").strip()

    payload = {
        "name": row["name"].strip(),
        "category": row["category"].strip(),
        "description": "",
        "type": (row.get("type") or "tecart").strip(),
        "state": (row.get("state") or "hidden").strip(),
        "attribution": (row.get("author") or "").strip(),
        "connection_info": (row.get("connection_info") or "").strip(),
        "value": int(row.get("value") or initial),
    }
    if function:
        payload["function"] = function
        payload["initial"] = initial
        payload["decay"] = decay
        payload["minimum"] = minimum

    ok, resp = _request("POST", f"{base_url.rstrip('/')}/api/v1/challenges", token, timeout, json_body=payload)
    if not ok or not isinstance(resp, dict) or not resp.get("success"):
        raise RuntimeError(f"gagal create challenge: {resp}")
    return resp["data"]["id"]


def upload_attachment(base_url, token, timeout, challenge_id, filepath):
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        filedata = f.read()
    body, content_type = _multipart_body({"challenge": str(challenge_id)}, "file", filename, filedata)
    ok, resp = _request(
        "POST", f"{base_url.rstrip('/')}/api/v1/files", token, timeout,
        data_bytes=body, content_type=content_type,
    )
    if not ok or not isinstance(resp, dict) or not resp.get("success"):
        raise RuntimeError(f"gagal upload {filename}: {resp}")
    return filename, resp["data"][0]["location"]


def resolve_description(desc_file: str, location_map: dict) -> str:
    with open(desc_file, encoding="utf-8") as f:
        text = f.read()

    def _sub(match):
        name = match.group(1).strip()
        if name not in location_map:
            raise KeyError(
                f"{desc_file}: placeholder {{{{FILE:{name}}}}} tidak match attachment manapun "
                f"(yang diupload: {sorted(location_map)})"
            )
        return f"/files/{location_map[name]}"

    return FILE_PLACEHOLDER.sub(_sub, text)


def patch_description(base_url, token, timeout, challenge_id, description):
    ok, resp = _request(
        "PATCH", f"{base_url.rstrip('/')}/api/v1/challenges/{challenge_id}", token, timeout,
        json_body={"description": description},
    )
    if not ok or not isinstance(resp, dict) or not resp.get("success"):
        raise RuntimeError(f"gagal update description: {resp}")


def create_flag(base_url, token, timeout, challenge_id, content, case_insensitive):
    payload = {"challenge_id": challenge_id, "content": content, "type": "static"}
    if case_insensitive:
        payload["data"] = "case_insensitive"
    ok, resp = _request("POST", f"{base_url.rstrip('/')}/api/v1/flags", token, timeout, json_body=payload)
    if not ok or not isinstance(resp, dict) or not resp.get("success"):
        raise RuntimeError(f"gagal create flag: {resp}")


def create_hint(base_url, token, timeout, challenge_id, content, cost=0):
    payload = {"challenge_id": challenge_id, "content": content, "cost": cost, "type": "standard"}
    ok, resp = _request("POST", f"{base_url.rstrip('/')}/api/v1/hints", token, timeout, json_body=payload)
    if not ok or not isinstance(resp, dict) or not resp.get("success"):
        raise RuntimeError(f"gagal create hint: {resp}")


def process_row(base_url, token, timeout, row, existing_names) -> str:
    name = row["name"].strip()
    if name in existing_names:
        return f"skip: sudah ada (id={existing_names[name]})"

    challenge_id = create_challenge(base_url, token, timeout, row)

    location_map = {}
    attachments = [a.strip() for a in (row.get("attachments") or "").split(";") if a.strip()]
    for path in attachments:
        filename, location = upload_attachment(base_url, token, timeout, challenge_id, path)
        location_map[filename] = location

    desc_file = (row.get("desc_file") or "").strip()
    if desc_file:
        description = resolve_description(desc_file, location_map)
        patch_description(base_url, token, timeout, challenge_id, description)

    flag = (row.get("flag") or "").strip()
    if flag:
        case_insensitive = (row.get("flag_case_insensitive") or "").strip().lower() in ("yes", "y", "true", "1")
        create_flag(base_url, token, timeout, challenge_id, flag, case_insensitive)

    for key in ("hint_1", "hint_2", "hint_3"):
        hint_text = (row.get(key) or "").strip()
        if hint_text:
            create_hint(base_url, token, timeout, challenge_id, hint_text, cost=0)

    return f"created: id={challenge_id}"


def main() -> None:
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_csv", help="CSV input, lihat challenges_upload.csv untuk kolomnya")
    ap.add_argument("-o", "--output", default="upload_results.csv", help="CSV hasil (default: upload_results.csv)")
    ap.add_argument("--url", default=os.environ.get("CTFD_URL", ""), help="Base URL CTFd target (staging 8887 dulu!)")
    ap.add_argument("--token", default=os.environ.get("CTFD_API_TOKEN", ""), help="Admin API token")
    ap.add_argument("--dry-run", action="store_true", help="Cuma cek nama yang akan dibuat/dilewati, jangan panggil API")
    ap.add_argument("--delay", type=float, default=0.3, help="Jeda antar challenge (detik, default 0.3)")
    ap.add_argument("--timeout", type=float, default=15.0, help="Timeout per request (detik)")
    args = ap.parse_args()

    if not args.dry_run and not (args.url and args.token):
        raise SystemExit(
            "Perlu --url dan --token (atau isi CTFD_URL/CTFD_API_TOKEN di .env), "
            "atau pakai --dry-run buat cuma preview dulu."
        )

    rows = read_rows(args.input_csv)
    if not rows:
        raise SystemExit("Tidak ada baris valid di CSV input (cek kolom name terisi?)")

    existing_names = {} if args.dry_run else list_existing_challenge_names(args.url, args.token, args.timeout)

    results = []
    gagal = 0
    for row in rows:
        name = row["name"].strip()
        wave_tag = f" [wave {row['wave'].strip()}]" if (row.get("wave") or "").strip() else ""

        if args.dry_run:
            status = "skip: sudah ada" if name in existing_names else "dry-run: akan dibuat"
        else:
            try:
                status = process_row(args.url, args.token, args.timeout, row, existing_names)
            except Exception as e:  # noqa: BLE001 - tetap lanjut ke baris berikutnya
                status = f"GAGAL: {e}"
                gagal += 1
                print(f"[GAGAL] {name}: {e}", file=sys.stderr)
            time.sleep(args.delay)

        results.append({"name": name, "category": row.get("category", ""), "status": status})
        print(f"{name:40.40s}{wave_tag} -> {status}")

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "category", "status"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{len(results)} baris diproses, {gagal} gagal. Hasil ditulis ke {args.output}")
    if gagal:
        print("Baris gagal: hapus manual challenge yang setengah jadi di Admin Panel, lalu rerun barisnya.")


if __name__ == "__main__":
    main()
