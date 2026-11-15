#!/usr/bin/env python3
import hashlib
import secrets
import signal
import sys

from flag import flag
from keygen import new_modulus  # server-side key generation (not provided)

E = 65537
TIME_LIMIT = 180
MAX_TRIES = 3


def out(s=""):
    sys.stdout.write(s + "\n")
    sys.stdout.flush()


def timeout(*_):
    out("\nTime's up. The great Sinclair keeps his vault.")
    sys.exit(0)


def main():
    out("Sealing a fresh vault, one moment...")
    n, _, _ = new_modulus()
    width = (n.bit_length() + 7) // 8
    lo = 1 << (n.bit_length() - 2)
    m = lo + secrets.randbelow(n - lo)
    c = pow(m, E, n)
    check = hashlib.sha256(m.to_bytes(width, "big")).hexdigest()[:32]

    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(TIME_LIMIT)
    out("=========== Sinclair's Vault ===========")
    out("The great Sinclair has sealed a fresh secret m for you.")
    out()
    out(f"N = {n}")
    out(f"e = {E}")
    out(f"c = {c}")
    out(f"check = {check}")
    out()
    out("c = pow(m, e, N)")
    out("check = sha256(m.to_bytes((N.bit_length() + 7) // 8, 'big')).hexdigest()[:32]")
    out(f"Send m (decimal or 0x-hex). {MAX_TRIES} tries, {TIME_LIMIT} seconds.")
    for _ in range(MAX_TRIES):
        sys.stdout.write("m = ")
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            return
        try:
            guess = int(line.strip(), 0)
        except ValueError:
            out("That is not a number.")
            continue
        if guess == m:
            out(f"The vault opens: {flag}")
            return
        out("Wrong.")
    out("Too many attempts.")


if __name__ == "__main__":
    main()
