#!/usr/bin/env python3
"""Solver referensi untuk challenge Nahida (Cryptography E).

Jalur: bocorkan K0 (= E(IV)) lewat balasan error, pakai pantulan plaintext
tujuan `dbg` sebagai oracle E(x), pulihkan token dari sesi vault di pcap,
lalu susun permintaan 'CMD flag' sendiri secara CFB dan dekripsi balasannya.

Dependensi: pycryptodome, scapy. Tanpa kunci rahasia apa pun.
Pemakaian: python solve.py <host> <port> [capture.pcap]
"""
import os
import socket
import struct
import sys
import zlib

from scapy.all import rdpcap, Raw, TCP, IP

BLOCK = 16
VAULT_IP, VAULT_PORT = b"\x0a\x00\x00\x05", 9000
DBG_IP, DBG_PORT = b"\x0a\x00\x00\x63", 1


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def mkheader(ip, port, sid=b"ATK0"):
    b = bytes([1, 1]) + ip + struct.pack(">H", port) + sid
    b += struct.pack("<I", zlib.crc32(b) & 0xFFFFFFFF)
    return b


# --- jaringan -------------------------------------------------------------
def send_recv(host, port, data):
    s = socket.create_connection((host, port), timeout=10)
    s.sendall(data)
    s.shutdown(socket.SHUT_WR)
    out = b""
    while True:
        try:
            chunk = s.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        out += chunk
    s.close()
    return out


def leak_k0(host, port):
    # header dengan CRC pasti salah -> error seragam = Enc(0^16) = E(IV) = K0
    reply = send_recv(host, port, b"\x11" * 32)
    assert len(reply) >= BLOCK, "balasan error tak terduga"
    return reply[:BLOCK]


class Oracle:
    """E(x) untuk x sembarang, lewat pantulan plaintext tujuan dbg."""

    def __init__(self, host, port, k0):
        self.host, self.port, self.k0 = host, port, k0
        self.c0 = xor(mkheader(DBG_IP, DBG_PORT), k0)  # header dbg terenkripsi
        self.calls = 0

    def enc_many(self, xs):
        out = {}
        PACK = 60  # x per koneksi (2 blok tiap x), < MAX_INPUT
        for i in range(0, len(xs), PACK):
            batch = xs[i:i + PACK]
            payload = b"".join(x + b"\x00" * BLOCK for x in batch)
            refl = send_recv(self.host, self.port, self.c0 + payload)
            self.calls += 1
            # refl = P1 P2 P3 P4 ...  ; E(xj) ada di blok indeks 2j+1
            for j, x in enumerate(batch):
                off = (2 * j + 1) * BLOCK
                out[bytes(x)] = refl[off:off + BLOCK]
        return [out[bytes(x)] for x in xs]

    def enc(self, x):
        return self.enc_many([x])[0]


# --- CFB via oracle -------------------------------------------------------
def cfb_decrypt(ct, k0, oracle):
    """Dekripsi ciphertext CFB penuh memakai K0 + oracle E()."""
    blocks = [ct[i:i + BLOCK] for i in range(0, len(ct), BLOCK)]
    ks = [k0] + oracle.enc_many(blocks[:-1])      # keystream tiap blok
    pt = b"".join(xor(blocks[i], ks[i]) for i in range(len(blocks)))
    return pt


def cfb_encrypt(pt, k0, oracle):
    """Enkripsi plaintext CFB penuh memakai K0 + oracle E() (sekuensial)."""
    if len(pt) % BLOCK:
        pt += b"#" * (BLOCK - len(pt) % BLOCK)
    blocks = [pt[i:i + BLOCK] for i in range(0, len(pt), BLOCK)]
    ct = []
    feedback = k0
    for b in blocks:
        c = xor(b, feedback)
        ct.append(c)
        feedback = oracle.enc(c)   # keystream blok berikut = E(c)
    return b"".join(ct)


# --- pcap -----------------------------------------------------------------
def _server_endpoints(pkts):
    """Endpoint server = tujuan paket SYN (tanpa ACK). Fallback: dport tersering."""
    servers = set()
    for p in pkts:
        if p.haslayer(TCP):
            f = int(p[TCP].flags)
            if (f & 0x02) and not (f & 0x10):   # SYN set, ACK unset
                servers.add((p[IP].dst, p[TCP].dport))
    if servers:
        return servers
    from collections import Counter
    c = Counter((p[IP].dst, p[TCP].dport) for p in pkts if p.haslayer(TCP))
    return {c.most_common(1)[0][0]} if c else set()


def reassemble(pcap_path, gport=None):
    """Rakit stream TCP; deteksi sisi server otomatis (lepas dari port live)."""
    pkts = rdpcap(pcap_path)
    servers = _server_endpoints(pkts)
    flows = {}
    for p in pkts:
        if not (p.haslayer(TCP) and p.haslayer(Raw)):
            continue
        ipl, tcpl = p[IP], p[TCP]
        key = (ipl.src, tcpl.sport, ipl.dst, tcpl.dport)
        flows.setdefault(key, []).append((tcpl.seq, bytes(p[Raw].load)))
    streams = {}
    for key, parts in flows.items():
        parts.sort()
        seen, data = set(), b""
        for seq, payload in parts:
            if seq in seen:
                continue
            seen.add(seq)
            data += payload
        streams[key] = data
    # pasangkan per endpoint klien: arah klien->server = dst adalah server
    sessions = []
    for (src, sport, dst, dport), cdata in streams.items():
        if (dst, dport) not in servers:
            continue
        rev = (dst, dport, src, sport)
        sessions.append({"client": (src, sport), "c": cdata,
                         "s": streams.get(rev, b"")})
    return sessions


# --- utama ----------------------------------------------------------------
def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 13338
    pcap = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "capture.pcap")

    k0 = leak_k0(host, port)
    print(f"[+] K0 = {k0.hex()}")
    oracle = Oracle(host, port, k0)

    sessions = reassemble(pcap)
    print(f"[+] {len(sessions)} sesi dari pcap")

    # cari sesi vault yang auth-nya berhasil (balasan diawali 200)
    target = None
    for s in sessions:
        if len(s["c"]) < BLOCK:
            continue
        hdr = xor(s["c"][:BLOCK], k0)
        dst_ip, dst_port = hdr[2:6], struct.unpack(">H", hdr[6:8])[0]
        if (dst_ip, dst_port) != (VAULT_IP, VAULT_PORT):
            continue
        if s["s"][:BLOCK] and xor(s["s"][:BLOCK], k0).startswith(b"200"):
            target = s
            break
    assert target, "sesi vault sukses tidak ditemukan"
    print(f"[+] sesi vault target: client {target['client']}")

    req_pt = cfb_decrypt(target["c"], k0, oracle)
    token = None
    for ln in req_pt.split(b"\n"):
        if ln.startswith(b"AUTH "):
            token = ln[5:].strip()
    assert token, "token tidak terbaca"
    print(f"[+] token = {token.decode()}")

    # susun permintaan 'CMD flag' sendiri
    body = (b"HELLO vault/1.0\n" + b"AUTH " + token + b"\n"
            + b"CMD flag\nEND\n")
    pt = mkheader(VAULT_IP, VAULT_PORT, b"ATKZ") + body
    ct = cfb_encrypt(pt, k0, oracle)
    reply = send_recv(host, port, ct)
    resp = cfb_decrypt(reply, k0, oracle)
    print(f"[+] balasan vault: {resp[:16]!r}")

    flag = None
    for ln in resp.split(b"\n"):
        if ln.startswith(b"TecFest26{"):
            flag = ln
    print(f"[+] oracle calls: {oracle.calls}")
    if flag:
        print(f"\n[FLAG] {flag.decode()}")
        return 0
    print("\n[!] flag tidak ditemukan; dump:")
    print(resp)
    return 1


if __name__ == "__main__":
    sys.exit(main())
