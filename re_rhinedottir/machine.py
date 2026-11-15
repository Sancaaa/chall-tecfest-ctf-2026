"""Model referensi mesin rotor Rhinedottir (dipakai gen.py dan solve.py).

Mesin ini harus identik dengan implementasi di src/rhinedottir.c (parent).
Rotor di atas 256 simbol, stepping ala Enigma (double-step), ditambah dua hal:
  * salt dari rip pemanggil (alamat tepat setelah instruksi syscall di child)
  * autokey: byte plaintext ditambahkan ke posisi rotor ke-3 setelah dienkripsi
"""
import random

N = 256


def gen_params(seed):
    rng = random.Random(seed)
    rot = []
    for _ in range(3):
        p = list(range(N))
        rng.shuffle(p)
        rot.append(p)
    # reflector: involusi tanpa titik tetap
    idx = list(range(N))
    rng.shuffle(idx)
    refl = [0] * N
    for a, b in zip(idx[0::2], idx[1::2]):
        refl[a] = b
        refl[b] = a
    p0 = rng.randrange(N)
    n0 = (p0 + rng.randrange(25, 40)) & 255   # carry rotor 0 -> 1 kena di dalam pesan
    n1 = rng.randrange(N)
    p1 = n1                                    # double-step langsung di panggilan pertama
    p2 = rng.randrange(N)
    return {"rot": rot, "refl": refl, "n0": n0, "n1": n1, "init": [p0, p1, p2]}


def salt_of(rip):
    """Salt dari alamat setelah syscall (harus sama dengan parent di C)."""
    return ((rip >> 4) ^ (rip >> 12)) & 0xFF


class Machine:
    def __init__(self, params):
        self.P = params
        self.inv = []
        for r in params["rot"]:
            iv = [0] * N
            for i, v in enumerate(r):
                iv[v] = i
            self.inv.append(iv)
        self.reset()

    def reset(self):
        self.p = list(self.P["init"])

    def _step(self):
        p = self.p
        if p[1] == self.P["n1"]:
            p[1] = (p[1] + 1) & 255
            p[2] = (p[2] + 1) & 255
        elif p[0] == self.P["n0"]:
            p[1] = (p[1] + 1) & 255
        p[0] = (p[0] + 1) & 255

    def _path(self, x):
        p, rot, inv = self.p, self.P["rot"], self.inv
        for i in range(3):
            x = (rot[i][(x + p[i]) & 255] - p[i]) & 255
        x = self.P["refl"][x]
        for i in (2, 1, 0):
            x = (inv[i][(x + p[i]) & 255] - p[i]) & 255
        return x

    def enc(self, x, salt):
        self._step()
        self.p[2] = (self.p[2] + salt) & 255
        y = self._path(x)
        self.p[2] = (self.p[2] + x) & 255
        return y

    def dec(self, y, salt):
        self._step()
        self.p[2] = (self.p[2] + salt) & 255
        x = self._path(y)
        self.p[2] = (self.p[2] + x) & 255
        return x


def run_enc(params, data, salts):
    """salts: salt untuk call site a, b, c; call site dipilih dari indeks % 3."""
    m = Machine(params)
    return [m.enc(b, salts[i % 3]) for i, b in enumerate(data)]


def run_dec(params, data, salts):
    m = Machine(params)
    return [m.dec(b, salts[i % 3]) for i, b in enumerate(data)]
