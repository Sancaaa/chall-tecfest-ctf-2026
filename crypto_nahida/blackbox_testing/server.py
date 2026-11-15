#!/usr/bin/env python3
"""TecTunnel v1 - gateway internal PT Nahida.

Meneruskan lalu lintas karyawan yang terbungkus ke layanan dalam. Tiap
koneksi membawa frame terenkripsi berisi header tujuan diikuti payload.
Konfigurasi (kunci sesi, token layanan) dibaca dari SECRET_DIR.
"""
import hashlib
import os
import socket
import socketserver
import struct
import threading
import time
import zlib

from Crypto.Cipher import AES

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "13338"))
SECRET_DIR = os.environ.get(
    "SECRET_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets")
)

MAX_CONN_PER_IP = int(os.environ.get("MAX_CONN_PER_IP", "6"))
MAX_INPUT = int(os.environ.get("MAX_INPUT", "4096"))   # byte payload maksimum
IO_TIMEOUT = float(os.environ.get("IO_TIMEOUT", "5"))  # idle timeout per recv
HARD_DEADLINE = float(os.environ.get("HARD_DEADLINE", "8"))  # total per koneksi

BLOCK = 16


def _secret(name):
    with open(os.path.join(SECRET_DIR, name), "rb") as f:
        return f.read().strip()


KEY = bytes.fromhex(_secret("key").decode())
TOKEN = _secret("token")          # 32 hex char
FLAG = _secret("flag")
IV = hashlib.sha256(KEY).digest()[:BLOCK]   # IV sesi diturunkan dari kunci


def _dec():
    return AES.new(KEY, AES.MODE_CFB, iv=IV, segment_size=128)


def _enc():
    return AES.new(KEY, AES.MODE_CFB, iv=IV, segment_size=128)


# --- tujuan virtual (host:port -> penanganan), semua dalam proses ---------
VAULT = (b"\x0a\x00\x00\x05", 9000)   # 10.0.0.5:9000
DBG = (b"\x0a\x00\x00\x63", 1)        # 10.0.0.99:1
MAIL = (b"\x0a\x00\x00\x07", 25)      # 10.0.0.7:25
PRN = (b"\x0a\x00\x00\x08", 631)      # 10.0.0.8:631


def parse_header(pt16):
    """Kembalikan dict header bila CRC valid, else None."""
    if len(pt16) < BLOCK:
        return None
    ver, cmd = pt16[0], pt16[1]
    ip = pt16[2:6]
    port = struct.unpack(">H", pt16[6:8])[0]
    sid = pt16[8:12]
    crc = struct.unpack("<I", pt16[12:16])[0]
    if zlib.crc32(pt16[:12]) & 0xFFFFFFFF != crc:
        return None
    if ver != 1 or cmd != 1:
        return None
    return {"ip": ip, "port": port, "sid": sid}


def vault_handle(payload):
    """Protokol vault berbasis baris. Status 16 byte + body."""
    lines = payload.split(b"\n")
    has_hello = lines and lines[0].startswith(b"HELLO vault/1.0")
    token = None
    verb = None
    has_end = False
    for ln in lines:
        if ln.startswith(b"AUTH "):
            token = ln[5:].strip()
        elif ln.startswith(b"CMD "):
            verb = ln[4:8]
        elif ln.strip() == b"END":
            has_end = True
    if not has_hello or verb is None or not has_end:
        return b"400 BAD REQUEST \n"
    if token != TOKEN:
        return b"401 DENIED vault" + b"\nnot authorized\n"
    if verb == b"stat":
        return b"200 OK vault/1.0" + b"\nuptime 41d\nsessions 7\nload 0.20\n"
    if verb == b"flag":
        return b"200 OK vault/1.0" + b"\n" + FLAG + b"\n"
    return b"400 BAD REQUEST \n"


def route(header, payload):
    """Kembalikan (reply_plaintext, encrypt_reply: bool)."""
    dst = (header["ip"], header["port"])
    if dst == VAULT:
        return vault_handle(payload), True
    if dst == DBG:
        # loopback diagnostik: kirim balik payload untuk pengecekan integritas
        return payload[:1024], False
    if dst in (MAIL, PRN):
        return b"service temporarily unavailable\n", True
    return b"\x00" * BLOCK, True


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        sock = self.request
        sock.settimeout(IO_TIMEOUT)
        deadline = time.time() + HARD_DEADLINE
        buf = b""
        try:
            while len(buf) <= MAX_INPUT + BLOCK:
                if time.time() > deadline:
                    break
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                buf += chunk
        except OSError:
            return

        if len(buf) < BLOCK:
            self._reply(b"\x00" * BLOCK, True)
            return

        pt = _dec().decrypt(buf)
        header = parse_header(pt[:BLOCK])
        if header is None:
            # header tak valid / CRC salah -> error seragam = 16 byte nol
            self._reply(b"\x00" * BLOCK, True)
            return
        reply, enc = route(header, pt[BLOCK:])
        self._reply(reply, enc)

    def _reply(self, data, encrypt):
        if encrypt:
            data = _enc().encrypt(data)
        try:
            self.request.sendall(data)
        except OSError:
            pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._per_ip = {}
        self._lock = threading.Lock()

    def verify_request(self, request, client_address):
        ip = client_address[0]
        with self._lock:
            n = self._per_ip.get(ip, 0)
            if n >= MAX_CONN_PER_IP:
                return False
            self._per_ip[ip] = n + 1
        return True

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            ip = client_address[0]
            with self._lock:
                self._per_ip[ip] = max(0, self._per_ip.get(ip, 1) - 1)


def main():
    srv = Server((HOST, PORT), Handler)
    print(f"[nahida] listening on {HOST}:{PORT}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
