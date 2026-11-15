import os
import socket
import threading
import json
import random
import string
import time
from collections import defaultdict

import numpy as np

# Konfigurasi bisa dioverride lewat environment variable (dipakai docker-compose).
# Untuk mencoba hitungan manual secara lokal, set TIMEOUT_SECONDS besar, mis. 600.
# FLAG dibaca dari file (di-mount read-only saat run), bukan literal di source
# ini supaya tidak ikut masuk ke image/git saat server.py dibagikan ke tester.
FLAG_FILE = os.environ.get(
    "FLAG_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "flag.txt")
)
with open(FLAG_FILE) as _f:
    FLAG = _f.read().strip()

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "13337"))
TIMEOUT_SECONDS = float(os.environ.get("TIMEOUT_SECONDS", "20"))
MAX_CONN_PER_IP = int(os.environ.get("MAX_CONN_PER_IP", "10"))
MAX_CONN_TOTAL = int(os.environ.get("MAX_CONN_TOTAL", "200"))

TOKEN_LENGTH = 13
MAX_RESPONSE_BYTES = 128

# 6 Unit Vectors (Center pieces)
UNIT_VECTORS = [
    {"name": "Front (+X)",  "c": [1, 0, 0]},
    {"name": "Back (-X)",   "c": [-1, 0, 0]},
    {"name": "Right (+Y)",  "c": [0, 1, 0]},
    {"name": "Left (-Y)",   "c": [0, -1, 0]},
    {"name": "Top (+Z)",    "c": [0, 0, 1]},
    {"name": "Bottom (-Z)", "c": [0, 0, -1]},
]

# 26 cubelets coordinates
ALL_COORDS = [
    [x, y, z]
    for x in [-1, 0, 1]
    for y in [-1, 0, 1]
    for z in [-1, 0, 1]
    if not (x == 0 and y == 0 and z == 0)
]

def rotation_matrix(v, direction=1):
    x, y, z = v
    cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.outer(v, v) - direction * cross

def get_center_rotation(v, k):
    # k in {0, 1, 2, 3}
    if k == 0:
        return np.identity(3, dtype=int)
    elif k == 1:
        return rotation_matrix(v, 1).astype(int)
    elif k == 2:
        r1 = rotation_matrix(v, 1).astype(int)
        return (r1 @ r1).astype(int)
    elif k == 3:
        return rotation_matrix(v, -1).astype(int)

def generate_challenge(token, selected_channels, rng=random):
    channel_coords = [ch["c"] for ch in selected_channels]
    cubes = []

    for idx, char in enumerate(token):
        val = ord(char)
        digits = [
            (val >> 6) & 3,
            (val >> 4) & 3,
            (val >> 2) & 3,
            val & 3,
        ]

        pieces = []
        for coord in ALL_COORDS:
            if coord in channel_coords:
                ch_idx = channel_coords.index(coord)
                k = digits[ch_idx]
                R = get_center_rotation(coord, k)
            else:
                # Keping selain 4 center aktif (identitas)
                R = np.identity(3, dtype=int)

            pieces.append({"c": coord, "R": R.tolist()})

        # Acak susunan kepingan dalam daftar
        rng.shuffle(pieces)
        cubes.append({"cube_id": idx, "pieces": pieces})

    return cubes

def new_session(rng=random):
    """Satu sesi = 4 channel acak, token acak, dan 13 kubus yang membawanya."""
    # Salin dict supaya label channel tidak menimpa UNIT_VECTORS yang dipakai bersama
    # oleh semua thread.
    selected_channels = [
        dict(ch, channel=i) for i, ch in enumerate(rng.sample(UNIT_VECTORS, 4))
    ]
    charset = string.ascii_letters + string.digits
    token = "".join(rng.choice(charset) for _ in range(TOKEN_LENGTH))
    cubes = generate_challenge(token, selected_channels, rng)
    return selected_channels, token, cubes

def read_response(conn, deadline):
    """Baca jawaban peserta sampai newline, EOF, atau sepanjang token (tanpa newline)."""
    buf = b""
    while b"\n" not in buf and len(buf.strip()) < TOKEN_LENGTH and len(buf) < MAX_RESPONSE_BYTES:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise socket.timeout()
        conn.settimeout(remaining)
        chunk = conn.recv(MAX_RESPONSE_BYTES)
        if not chunk:
            break
        buf += chunk
    return buf.split(b"\n", 1)[0].decode(errors="replace").strip()

def safe_send(conn, data):
    try:
        conn.sendall(data)
    except OSError:
        pass

def handle_client(conn, addr):
    print(f"[*] New connection from {addr}", flush=True)
    conn.settimeout(TIMEOUT_SECONDS)

    try:
        selected_channels, token, cubes = new_session()

        banner = (
            "====================================================\n"
            "   Unknown God: Sustainer of Heavenly Principles    \n"
            "====================================================\n"
            f"\n"
        )
        for ch in selected_channels:
            banner += f"    Channel {ch['channel']} -> {ch['name']} (c = {ch['c']})\n"

        banner += (
            f"[!] kelamaan! dah {TIMEOUT_SECONDS:g} detik! ULANGGGG!\n"
            f"[!] Mengirim {len(cubes)} cubes asmoday...\n"
        )
        conn.sendall(banner.encode())

        payload = {
            "channels": selected_channels,
            "cubes": cubes
        }
        conn.sendall((json.dumps(payload) + "\n").encode())
        conn.sendall(b"[?] Jadi, masukan codemu: ")

        # Batas waktu dihitung sejak data terkirim, bukan per recv
        start_time = time.monotonic()
        response = read_response(conn, start_time + TIMEOUT_SECONDS)
        elapsed = time.monotonic() - start_time

        if response == token:
            safe_send(conn, f"\n[+] ANJAY! solved dalam {elapsed:.2f} detik.\n[+] FLAG: {FLAG}\n".encode())
            print(f"[+] Client {addr} solved the challenge!", flush=True)
        else:
            safe_send(conn, b"\n[-] SALAHHH! ULANG!\n")
            print(f"[-] Client {addr} failed (submitted {response!r}, expected {token!r})", flush=True)

    except socket.timeout:
        safe_send(conn, f"\n[-] kelamaan! dah {TIMEOUT_SECONDS:g} detik, ulang!\n".encode())
        print(f"[-] Client {addr} timed out", flush=True)
    except Exception as e:
        print(f"[-] Error handling client {addr}: {e}", flush=True)
    finally:
        conn.close()

class ConnectionLimiter:
    """Batasi koneksi bersamaan per IP dan total, supaya satu klien tidak menghabiskan thread."""

    def __init__(self, per_ip, total):
        self.per_ip = per_ip
        self.total = total
        self.lock = threading.Lock()
        self.by_ip = defaultdict(int)
        self.count = 0

    def acquire(self, ip):
        with self.lock:
            if self.count >= self.total or self.by_ip[ip] >= self.per_ip:
                return False
            self.by_ip[ip] += 1
            self.count += 1
            return True

    def release(self, ip):
        with self.lock:
            self.by_ip[ip] -= 1
            if self.by_ip[ip] <= 0:
                del self.by_ip[ip]
            self.count -= 1

def create_listener(host=HOST, port=PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(128)
    return server

def serve_forever(server, limiter=None):
    limiter = limiter or ConnectionLimiter(MAX_CONN_PER_IP, MAX_CONN_TOTAL)

    def run(conn, addr):
        try:
            handle_client(conn, addr)
        finally:
            limiter.release(addr[0])

    while True:
        try:
            conn, addr = server.accept()
        except OSError:
            return  # listener ditutup
        if not limiter.acquire(addr[0]):
            print(f"[!] Connection from {addr} rejected (limit)", flush=True)
            safe_send(conn, b"[-] Kebanyakan koneksi. tutup lalu ulang!\n")
            conn.close()
            continue
        threading.Thread(target=run, args=(conn, addr), daemon=True).start()

def main():
    server = create_listener()
    print(f"[*] Server listening on {HOST}:{PORT} (timeout {TIMEOUT_SECONDS:g}s)", flush=True)
    serve_forever(server)

if __name__ == "__main__":
    main()
