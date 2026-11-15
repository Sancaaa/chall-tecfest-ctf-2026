#!/usr/bin/env python3
"""Sinclair server-side key generation. Organizer-only: NOT distributed to participants.

Each call returns a fresh modulus N = p*q with e = 65537 such that
  * p - 1 = 2 * (27 random primes in [2^19, 2^20))  -> Pollard p-1 with B >= 2^20 factors N
  * q - 1 = 2 * 65537 * r with r a 500-bit prime (q-1 not smooth; standard tools such as
    sympy.nthroot_mod can factor q-1 instantly, so the root step stays fast)
so gcd(e, p-1) = 1 (unique root mod p) and 65537 || q-1 (65537 roots mod q).
"""
import math
import secrets

E = 65537
SMALL_BITS = 20
P_FACTORS = 27
R_BITS = 500


def _sieve(n):
    s = bytearray([1]) * (n + 1)
    s[0:2] = b"\0\0"
    for i in range(2, int(n ** 0.5) + 1):
        if s[i]:
            s[i * i::i] = bytearray(len(s[i * i::i]))
    return [i for i, v in enumerate(s) if v]


_ALL = _sieve(1 << SMALL_BITS)
_POOL = [x for x in _ALL if x >= 1 << (SMALL_BITS - 1)]
_TRIAL = _ALL[:2000]


def _tree_product(xs):
    while len(xs) > 1:
        xs = [xs[i] * xs[i + 1] if i + 1 < len(xs) else xs[i] for i in range(0, len(xs), 2)]
    return xs[0]




def is_probable_prime(n, rounds=32):
    if n < 2:
        return False
    for p in _TRIAL[:200]:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def gen_p():
    while True:
        p = 2 * math.prod(secrets.choice(_POOL) for _ in range(P_FACTORS)) + 1
        if is_probable_prime(p):
            return p


_WINDOW = 1 << 16
_INV4E = {p: pow(2 * 2 * E, -1, p) for p in _TRIAL[1:] if p != E}


def gen_q():
    """q = 2*E*r + 1 with r prime: sieve a window r0 + 2k for small factors of r and q."""
    while True:
        r0 = secrets.randbits(R_BITS) | (1 << (R_BITS - 1)) | 1
        alive = bytearray([1]) * _WINDOW
        for p in _TRIAL[1:]:
            k = (-r0 * ((p + 1) // 2)) % p                     # p | r0 + 2k
            alive[k::p] = bytes(len(range(k, _WINDOW, p)))
            if p != E:
                k = (-(2 * E * r0 + 1) * _INV4E[p]) % p        # p | 2*E*(r0 + 2k) + 1
                alive[k::p] = bytes(len(range(k, _WINDOW, p)))
        k = alive.find(1)
        while k != -1:
            r = r0 + 2 * k
            q = 2 * E * r + 1
            if is_probable_prime(r, 1) and is_probable_prime(q, 1) and is_probable_prime(r) and is_probable_prime(q):
                return q
            k = alive.find(1, k + 1)


def new_modulus():
    p, q = gen_p(), gen_q()
    assert p != q and math.gcd(E, p - 1) == 1 and (q - 1) % E == 0 and ((q - 1) // E) % E
    return p * q, p, q
