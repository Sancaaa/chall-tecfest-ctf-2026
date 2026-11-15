#!/usr/bin/env python3
"""Buat capture.pcap untuk challenge Nahida (author-side).

Menyusun beberapa sesi TCP klien<->gateway berisi frame terenkripsi.
Satu sesi menuju vault (CMD stat; flag TIDAK pernah muncul di capture),
sisanya umpan (vault gagal, mail, print). Kunci/IV/token dibaca dari
secrets/ supaya identik dengan server.
"""
import hashlib
import os
import struct
import zlib

from Crypto.Cipher import AES
from scapy.all import IP, TCP, Ether, Raw, wrpcap

HERE = os.path.dirname(os.path.abspath(__file__))
SECRET_DIR = os.environ.get("SECRET_DIR", os.path.join(HERE, "secrets"))
OUT = os.path.join(HERE, "capture.pcap")
BLOCK = 16

KEY = bytes.fromhex(open(os.path.join(SECRET_DIR, "key")).read().strip())
TOKEN = open(os.path.join(SECRET_DIR, "token"), "rb").read().strip()
IV = hashlib.sha256(KEY).digest()[:BLOCK]

GATEWAY = "203.0.113.10"
GPORT = 13338


def cfb():
    return AES.new(KEY, AES.MODE_CFB, iv=IV, segment_size=128)


def header(ip, port, sid):
    b = bytes([1, 1]) + ip + struct.pack(">H", port) + sid
    b += struct.pack("<I", zlib.crc32(b) & 0xFFFFFFFF)
    assert len(b) == BLOCK
    return b


def align_filler(curlen):
    """Filler diakhiri \n agar panjang total jadi kelipatan blok."""
    need = (-curlen) % BLOCK
    if need == 0:
        return b""
    if need == 1:
        return b"\n"
    return b"#" * (need - 1) + b"\n"


def vault_request(verb, sid):
    ip = b"\x0a\x00\x00\x05"
    body = b"HELLO vault/1.0\n"
    body += b"AUTH " + TOKEN + b"\n"
    body += align_filler(len(body))          # CMD mulai di batas blok
    body += b"CMD " + verb + b"\n"
    body += align_filler(len(body))          # END didorong ke blok berikutnya
    body += b"END\n"
    body += b"#" * ((-len(body)) % BLOCK)     # rapikan akhir ke batas blok
    pt = header(ip, 9000, sid) + body
    return cfb().encrypt(pt)


def simple_request(ip, port, sid, text):
    pt = header(ip, port, sid) + text
    return cfb().encrypt(pt)


def vault_reply_stat():
    pt = b"200 OK vault/1.0" + b"\nuptime 41d\nsessions 7\nload 0.20\n"
    return cfb().encrypt(pt)


def vault_reply_denied():
    pt = b"401 DENIED vault" + b"\nnot authorized\n"
    return cfb().encrypt(pt)


def decoy_reply():
    pt = b"service temporarily unavailable\n"
    return cfb().encrypt(pt)


def session(pkts, cip, cport, cstream, sstream, t0):
    """Rakit satu sesi TCP: handshake, data dua arah, FIN."""
    cseq, sseq = 1000, 5000
    base = dict(sport=cport, dport=GPORT)
    ip_c = IP(src=cip, dst=GATEWAY)
    ip_s = IP(src=GATEWAY, dst=cip)
    # handshake
    pkts.append(Ether() / ip_c / TCP(flags="S", seq=cseq, **base))
    pkts.append(Ether() / ip_s / TCP(flags="SA", seq=sseq, ack=cseq + 1,
                                     sport=GPORT, dport=cport))
    cseq += 1
    pkts.append(Ether() / ip_c / TCP(flags="A", seq=cseq, ack=sseq + 1, **base))
    # client -> server data
    pkts.append(Ether() / ip_c / TCP(flags="PA", seq=cseq, ack=sseq + 1, **base)
                / Raw(cstream))
    cseq += len(cstream)
    sseq += 1
    # server -> client data
    pkts.append(Ether() / ip_s / TCP(flags="PA", seq=sseq, ack=cseq,
                                     sport=GPORT, dport=cport) / Raw(sstream))
    sseq += len(sstream)
    # teardown
    pkts.append(Ether() / ip_c / TCP(flags="FA", seq=cseq, ack=sseq, **base))
    pkts.append(Ether() / ip_s / TCP(flags="FA", seq=sseq, ack=cseq + 1,
                                     sport=GPORT, dport=cport))
    for i, p in enumerate(pkts[-7:]):
        p.time = t0 + i * 0.01


def main():
    pkts = []
    # sesi target: ke vault, CMD stat, balasan 200 (flag TIDAK ada di sini)
    session(pkts, "192.168.1.50", 40001,
            vault_request(b"stat", b"S1DA"), vault_reply_stat(), 1_700_000_000.0)
    # umpan: vault gagal auth (token sampah)
    bad = cfb().encrypt(header(b"\x0a\x00\x00\x05", 9000, b"S2DB")
                        + b"HELLO vault/1.0\nAUTH deadbeef\nCMD stat\nEND\n")
    session(pkts, "192.168.1.51", 40002, bad, vault_reply_denied(), 1_700_000_050.0)
    # umpan: mail & print
    session(pkts, "192.168.1.52", 40003,
            simple_request(b"\x0a\x00\x00\x07", 25, b"S3DC", b"EHLO office\n"),
            decoy_reply(), 1_700_000_100.0)
    session(pkts, "192.168.1.53", 40004,
            simple_request(b"\x0a\x00\x00\x08", 631, b"S4DD", b"print job 12\n"),
            decoy_reply(), 1_700_000_150.0)
    # umpan: vault stat kedua dari klien lain
    session(pkts, "192.168.1.54", 40005,
            vault_request(b"stat", b"S5DE"), vault_reply_stat(), 1_700_000_200.0)
    wrpcap(OUT, pkts)
    print(f"tulis {OUT} ({len(pkts)} paket, 5 sesi)")


if __name__ == "__main__":
    main()
