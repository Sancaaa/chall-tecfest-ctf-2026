#!/usr/bin/env python3
"""viscous GHASH modulus. Organizer-only: NOT distributed to participants.

Returns P = Q^2 for a fresh random irreducible Q of degree 64 (so GF(2)[x]/P is not a field).
"""
import secrets


def clmul(a, b):
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
    return r


def gf2_mod(a, m):
    dm = m.bit_length() - 1
    while a and a.bit_length() - 1 >= dm:
        a ^= m << (a.bit_length() - 1 - dm)
    return a


def gf2_mulmod(a, b, m):
    return gf2_mod(clmul(a, b), m)


def gf2_gcd(a, b):
    while b:
        a, b = b, gf2_mod(a, b)
    return a


def x_pow_2k(f, k):
    r = gf2_mod(1 << 1, f)
    for _ in range(k):
        r = gf2_mulmod(r, r, f)
    return r


def prime_factors(n):
    fs, d = set(), 2
    while d * d <= n:
        while n % d == 0:
            fs.add(d)
            n //= d
        d += 1
    if n > 1:
        fs.add(n)
    return fs


def is_irreducible_gf2(f, n):
    x = gf2_mod(1 << 1, f)
    if x_pow_2k(f, n) != x:
        return False
    for p in prime_factors(n):
        h = x_pow_2k(f, n // p) ^ x
        if gf2_gcd(h, f) != 1:
            return False
    return True


def poly_square(v):
    r, i = 0, 0
    while v:
        if v & 1:
            r |= 1 << (2 * i)
        v >>= 1
        i += 1
    return r


def random_irreducible(deg):
    while True:
        v = (1 << deg) | 1
        for e in range(1, deg):
            if secrets.randbits(1):
                v |= 1 << e
        if is_irreducible_gf2(v, deg):
            return v


def new_modulus():
    return poly_square(random_irreducible(64))
