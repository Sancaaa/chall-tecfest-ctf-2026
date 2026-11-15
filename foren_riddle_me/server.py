#!/usr/bin/env python3
"""
Netcat Q&A Verifier Server - CTF Challenge: Riddle Me This
Menjalankan TCP server multi-threaded untuk memverifikasi 7 jawaban investigasi
forensik dari disk image `nygma_drive.img`.

Dapat dijalankan langsung:
    python server.py --port 13370

Atau melalui Docker Compose di Home Server:
    docker compose up -d --build
"""

import argparse
import datetime
import os
import socket
import socketserver
import sys
from typing import Callable


DEFAULT_FLAG = "TecFest26{l00k_wh4t_1_g0t_b4tm4n}"
DEFAULT_PORT = 13370
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "8"))
IDLE_TIMEOUT = int(os.environ.get("IDLE_TIMEOUT", "900"))  # 15 menit default


def _norm_upper(s: str) -> str:
    return s.strip().strip('"').strip("'").upper()


from pathlib import Path
import json

ANSWER_DATA=json.loads(Path(__file__).with_name("answers.json").read_text(encoding="utf-8"))
if ANSWER_DATA.get("version") != 3 or len(ANSWER_DATA["answers"]) != 7:
    raise RuntimeError("Load the matching v3 answers.json before starting this server")
PROMPTS=[
    ("Evidence Identification","What are the volume label and serial number? Format LABEL:XXXX-XXXX."),
    ("Transfer Attribution","Which destination received the completed transfer of blueprints.zip? Format IP:PORT."),
    ("Program Attribution","What is the filename of the removed program associated with that transfer?"),
    ("Schedule Reconstruction","What UTC execution time does that program specify? Format YYYY-MM-DD HH:MM:SS."),
    ("Handoff Attribution","What is the location associated with the handoff survey at the time it was recorded?"),
    ("Archive Access","What password opens blueprints.zip?"),
    ("Classified Dossier","What is the MASTER_OVERRIDE_CODE in the dossier?")]

def checker(index):
    expected=ANSWER_DATA["answers"][index]
    def check(answer):
        value=answer.strip().strip('"').strip("'")
        if index==0:return value.upper().replace("-","").replace(" ",":")==expected.upper().replace("-","")
        if index in (1,2,4,6):return value.casefold()==expected.casefold()
        return value==expected
    return check

QUESTIONS=[{"title":f"[Q{i+1}/7] {title}","prompt":prompt,"check":checker(i)}
           for i,(title,prompt) in enumerate(PROMPTS)]


def log_event(addr: tuple[str, int], msg: str) -> None:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] [{addr[0]}:{addr[1]}] {msg}", flush=True)


def apply_backspaces(raw: str) -> str:
    """Menangani karakter backspace (\x08 / \x7f) dari klien telnet/raw netcat."""
    buf: list[str] = []
    for ch in raw:
        if ch in ("\x08", "\x7f"):
            if buf:
                buf.pop()
        else:
            buf.append(ch)
    return "".join(buf)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass, flag: str):
        super().__init__(server_address, RequestHandlerClass)
        self.flag = flag


class RiddleHandler(socketserver.BaseRequestHandler):
    def _send(self, text: str) -> None:
        self.request.sendall(text.encode("utf-8", errors="replace"))

    def _readline(self, max_len: int = 512) -> str | None:
        chunks = bytearray()
        while len(chunks) < max_len:
            b = self.request.recv(1)
            if not b:
                return None if not chunks else apply_backspaces(chunks.decode("utf-8", errors="ignore"))
            if b == b"\n":
                break
            if b != b"\r":
                chunks.extend(b)
        return apply_backspaces(chunks.decode("utf-8", errors="ignore"))

    def handle(self) -> None:
        client = self.client_address
        log_event(client, "Connected")
        self.request.settimeout(IDLE_TIMEOUT)

        try:
            for idx, q in enumerate(QUESTIONS, start=1):
                title = str(q["title"])
                prompt = str(q["prompt"])
                checker: Callable[[str], bool] = q["check"]  # type: ignore[assignment]

                if idx > 1:
                    self._send("\n------------------------------------------------------------------------\n")
                self._send(f"{title}\n{prompt}\n")

                attempt = 1
                empty_count = 0
                while True:
                    self._send(f"\nAnswer Q{idx} > ")
                    ans = self._readline()
                    if ans is None:
                        log_event(client, f"Disconnected at Q{idx}")
                        return

                    if not ans.strip():
                        empty_count += 1
                        if empty_count > 10:
                            self._send("[X] Too many empty inputs. Connection closed.\n")
                            return
                        self._send("[!] Empty input, please enter your answer.\n")
                        continue

                    if checker(ans):
                        self._send(f"[+] Correct! Question {idx}/7 solved.\n")
                        log_event(client, f"Passed Q{idx}/7 (after {attempt} attempt(s))")
                        break
                    else:
                        log_event(client, f"Wrong answer on Q{idx} (attempt {attempt}): {ans!r}")
                        self._send("[-] Incorrect answer, please try again!\n")
                        attempt += 1
                        if attempt > MAX_ATTEMPTS:
                            self._send("[X] Attempt limit reached. Reconnect when ready.\n")
                            return

            flag = self.server.flag  # type: ignore[attr-defined]
            congrats = (
                "\n========================================================================\n"
                " [!] RIDDLE SOLVED // CASE IR-2026-1024-NYGMA CLOSED!\n"
                "========================================================================\n"
                " Great work, Investigator! All evidence of insider sabotage and\n"
                " exfiltration by Edward Nygma has been successfully verified.\n\n"
                f" FLAG : {flag}\n"
                "========================================================================\n"
            )
            self._send(congrats)
            log_event(client, "SOLVED ALL 7 QUESTIONS -> FLAG DELIVERED!")

        except socket.timeout:
            try:
                self._send("\n\n[!] Connection closed due to idle timeout. Please reconnect.\n")
            except OSError:
                pass
            log_event(client, "Timed out")
        except (ConnectionResetError, BrokenPipeError, OSError):
            log_event(client, "Connection closed abruptly")


def main() -> None:
    parser = argparse.ArgumentParser(description="Riddle Me This - Netcat Q&A Server")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"), help="Bind host (default: 0.0.0.0)")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", str(DEFAULT_PORT))),
        help=f"Bind TCP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--flag",
        default=os.environ.get("FLAG", DEFAULT_FLAG),
        help="Flag yang diberikan setelah 7 pertanyaan terjawab benar",
    )
    args = parser.parse_args()

    with ThreadedTCPServer((args.host, args.port), RiddleHandler, flag=args.flag) as server:
        print(f"[*] Riddle Me This Netcat Server berjalan di {args.host}:{args.port}", flush=True)
        print("[*] Evidence release: v3", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Menutup server...", flush=True)
            sys.exit(0)


if __name__ == "__main__":
    main()
