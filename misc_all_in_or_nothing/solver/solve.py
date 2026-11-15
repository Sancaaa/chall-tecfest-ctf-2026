import base64
import codecs
import http.cookiejar
import json
import re
import sys
import urllib.request


def make_client():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def get_text(opener, url: str) -> str:
    with opener.open(url, timeout=10) as resp:
        return resp.read().decode("utf-8")


def post_json(opener, url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:13500").rstrip("/")
    opener = make_client()

    # Clue 1: robots.txt -> /staff/shift-receipt
    robots = get_text(opener, f"{base_url}/robots.txt")
    receipt_path = re.search(r"Disallow:\s*(/staff/\S+)", robots).group(1)
    receipt = get_text(opener, f"{base_url}{receipt_path}")
    clue1 = re.search(r"DOC_REF\s*:\s*([A-Z0-9_-]+)", receipt).group(1)

    # Clue 2: /api/table/state -> audit_memo_b64
    table_state = json.loads(get_text(opener, f"{base_url}/api/table/state"))
    memo = base64.b64decode(table_state["audit_memo_b64"]).decode("utf-8")
    clue2 = re.search(r"Kode insiden:\s*([A-Z0-9_-]+)", memo).group(1)

    # Clue 3: /static/assets/dealer_badge.svg -> ROT13 metadata -> Clue 3 & Clue 4 path
    svg_text = get_text(opener, f"{base_url}/static/assets/dealer_badge.svg")
    meta_raw = re.search(r"<metadata[^>]*>(.*?)</metadata>", svg_text, re.S).group(1).strip()
    meta_decoded = codecs.decode(meta_raw, "rot_13")
    clue3 = re.search(r"username:\s*([A-Z0-9_]+)", meta_decoded).group(1)
    vault_path = re.search(r"(/logs/\S+)", meta_decoded).group(1)

    # Clue 4: /logs/vault-audit -> Hex payload
    vault_log = get_text(opener, f"{base_url}{vault_path}")
    hex_payload = re.search(r"PAYLOAD_HEX:\s*([0-9a-fA-F]+)", vault_log).group(1)
    vault_decoded = bytes.fromhex(hex_payload).decode("utf-8")
    clue4 = re.search(r"Audit Code:\s*([A-Z0-9_-]+)", vault_decoded).group(1)

    print(f"[+] Extracted clues: {clue1}, {clue2}, {clue3}, {clue4}")

    # 4-Stage Psychological Confrontation
    moves = [
        ("B", clue1),
        ("B", clue2),
        ("A", clue3),
        ("C", clue4),
    ]

    flag = None
    for idx, (tactic, evidence) in enumerate(moves, start=1):
        res = post_json(
            opener,
            f"{base_url}/api/confront/submit",
            {"tactic": tactic, "evidence": evidence},
        )
        if not res.get("hit"):
            print(f"[-] Stage {idx} missed: {res}")
            return 1
        print(f"[+] Stage {idx} WEAKNESS HIT -> Composure {res['confront']['composure']}%")
        flag = res.get("flag")

    if not flag:
        print("[-] Flag not received")
        return 1

    print(f"[+] FLAG: {flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
