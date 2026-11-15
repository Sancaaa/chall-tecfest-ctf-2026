"""VM referensi (Python) untuk Naberius. Cerminan persis src/vm.go.

Dipakai gen.py untuk self-test dan sebagai pembanding perilaku binary Go.
"""

from naberius_spec import *


class VM:
    def __init__(self, cipher, tab_a, tab_b, k_a, k_b):
        self.cipher = bytes(cipher)
        self.tabs = [tab_a, tab_b]       # tab[slot] = ID logis opcode
        self.ks = [k_a, k_b]

    def run(self, inp, trace=None):
        code = bytearray(self.cipher)
        mem = bytearray(MEM_SIZE)
        mem[:len(inp)] = inp
        st = []
        acc, bad, nchk = ACC0, 0, 0
        pc, h, sel, halt = 0, H0, 0, False
        n = len(code) // INS_SIZE

        def push(x):
            nonlocal bad
            if len(st) >= 256:
                bad |= 0x80
                return
            st.append(x & 0xFF)

        def pop():
            nonlocal bad
            if not st:
                bad |= 0x40
                return 0
            return st.pop()

        while pc < n and not halt:
            i = pc
            p = i * INS_SIZE
            ksb = keystream(h, i)
            w = bytes(code[p + j] ^ ksb[j] for j in range(4))
            h = hmix(h, int.from_bytes(w, "little"), i)
            pc += 1
            op = self.tabs[sel][(w[0] ^ self.ks[sel]) & 15]
            a, b, c = w[1], w[2], w[3]
            if trace is not None:
                trace.append((i, sel, op, a, b, c))

            if op == OP_PUSH:
                push(a)
            elif op == OP_LOAD:
                push(mem[a & 63])
            elif op == OP_ADD:
                y = pop(); x = pop(); push(x + y)
            elif op == OP_SUB:
                y = pop(); x = pop(); push(x - y)
            elif op == OP_XOR:
                y = pop(); x = pop(); push(x ^ y)
            elif op == OP_ROL:
                push(rol8(pop(), a))
            elif op == OP_MUL:
                y = pop(); x = pop(); push(x * y)
            elif op == OP_MIX:
                x = pop()
                acc = (rol8(acc ^ x, 1) + a) & 0xFF
                push(acc)
            elif op == OP_CHK:
                x = pop()
                bad |= x ^ a
                nchk += 1
            elif op == OP_SWP:
                mem[a & 63], mem[b & 63] = mem[b & 63], mem[a & 63]
            elif op == OP_PATCH:
                off = a | (b << 8)
                if off < len(code):
                    code[off] ^= c
            elif op == OP_SEAL:
                cnt = min(a, MEM_SIZE)
                key = seal_key(bytes(mem[:cnt]))
                start = pc * INS_SIZE
                ks2 = stream2(key, len(code) - start)
                for j in range(len(ks2)):
                    code[start + j] ^= ks2[j]
            elif op == OP_MODE:
                sel = 1
            elif op == OP_HALT:
                halt = True
            elif op == OP_DROP:
                pop()
            # OP_NOP: tidak melakukan apa pun

        return bad == 0 and nchk == FLAG_LEN and halt and not st
