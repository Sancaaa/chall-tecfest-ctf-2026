#!/usr/bin/env python3
"""Official solver for The Apprentice Grimoire (Reverse Engineering).

Parses the unstripped Go ELF64 binary directly, locates main.spellBytecode
and main.spellTarget via .symtab -> .data -> .rodata, interprets the VM
bytecode, and recovers the flag without external dependencies.

Usage:
    python solve.py [path_to_grimoire]
"""

from pathlib import Path
import struct
import sys


def parse_elf64_sections(data: bytes) -> dict[str, tuple[int, int, int, int]]:
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise ValueError("Expected a 64-bit little-endian ELF binary.")

    e_shoff = struct.unpack_from("<Q", data, 40)[0]
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 58)

    shstr_off, shstr_size = struct.unpack_from(
        "<QQ", data, e_shoff + e_shstrndx * e_shentsize + 24
    )
    shstr = data[shstr_off : shstr_off + shstr_size]

    sections: dict[str, tuple[int, int, int, int]] = {}
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name, _type, _flags, sh_addr, sh_offset, sh_size, _link, _info, _align, sh_entsize = struct.unpack_from(
            "<IIQQQQIIQQ", data, off
        )
        end = shstr.find(b"\x00", sh_name)
        name = shstr[sh_name:end].decode("ascii", errors="replace")
        sections[name] = (sh_addr, sh_offset, sh_size, sh_entsize)
    return sections


def vaddr_to_offset(
    sections: dict[str, tuple[int, int, int, int]], vaddr: int
) -> int:
    for _name, (sa, so, sz, _entsize) in sections.items():
        if sa != 0 and sa <= vaddr < sa + sz:
            return so + (vaddr - sa)
    raise ValueError(f"Virtual address 0x{vaddr:x} not mapped to any section.")


def find_symbols(
    data: bytes, sections: dict[str, tuple[int, int, int, int]]
) -> dict[str, int]:
    if ".symtab" not in sections or ".strtab" not in sections:
        raise ValueError("Missing .symtab/.strtab; binary appears stripped.")

    _sa, sym_off, sym_size, entsize = sections[".symtab"]
    _sa2, str_off, str_size, _ = sections[".strtab"]
    strtab = data[str_off : str_off + str_size]

    symbols: dict[str, int] = {}
    entry_size = entsize or 24
    for off in range(sym_off, sym_off + sym_size, entry_size):
        st_name, _info, _other, _shndx, st_value, _st_size = struct.unpack_from(
            "<IBBHQQ", data, off
        )
        if st_name == 0 or st_value == 0:
            continue
        end = strtab.find(b"\x00", st_name)
        name = strtab[st_name:end].decode("ascii", errors="replace")
        symbols[name] = st_value
    return symbols


def read_go_string(
    data: bytes, sections: dict[str, tuple[int, int, int, int]], header_vaddr: int
) -> bytes:
    header_off = vaddr_to_offset(sections, header_vaddr)
    str_ptr, str_len = struct.unpack_from("<QQ", data, header_off)
    str_off = vaddr_to_offset(sections, str_ptr)
    return data[str_off : str_off + str_len]


def extract_xor_key(bytecode: bytes) -> int:
    pc = 0
    while pc < len(bytecode):
        op = bytecode[pc]
        if op in (0x01, 0x03, 0x04, 0x05):
            pc += 1
        elif op == 0x02:
            if pc + 1 >= len(bytecode):
                raise ValueError("Truncated XOR immediate in bytecode.")
            return bytecode[pc + 1]
        elif op in (0x06, 0x07):
            break
        else:
            raise ValueError(f"Unknown opcode 0x{op:02x} at pc={pc}.")
    raise ValueError("XOR opcode (0x02) not found in bytecode.")


def simulate_vm(candidate: bytes, bytecode: bytes, target: bytes) -> bool:
    if len(candidate) != len(target):
        return False

    pc = 0
    idx = 0
    acc = 0
    while pc < len(bytecode):
        op = bytecode[pc]
        if op == 0x01:
            acc = candidate[idx]
            pc += 1
        elif op == 0x02:
            acc ^= bytecode[pc + 1]
            pc += 2
        elif op == 0x03:
            acc = (acc + idx) & 0xFF
            pc += 1
        elif op == 0x04:
            if acc != target[idx]:
                return False
            pc += 1
        elif op == 0x05:
            idx += 1
            if idx >= len(target):
                pc += 1
            else:
                pc = 0
        elif op == 0x06:
            return True
        elif op == 0x07:
            return False
        else:
            return False
    return False


def solve(binary_path: Path) -> str:
    data = binary_path.read_bytes()
    sections = parse_elf64_sections(data)
    symbols = find_symbols(data, sections)

    for required in ("main.spellBytecode", "main.spellTarget"):
        if required not in symbols:
            raise ValueError(f"Required symbol {required} not found.")

    bytecode = read_go_string(data, sections, symbols["main.spellBytecode"])
    target = read_go_string(data, sections, symbols["main.spellTarget"])
    xor_key = extract_xor_key(bytecode)

    print(f"[*] Binary      : {binary_path}")
    print(f"[*] Bytecode    : {bytecode.hex(' ')}")
    print(f"[*] XOR key     : 0x{xor_key:02x}")
    print(f"[*] Target len  : {len(target)}")
    print(f"[*] Target hex  : {target.hex()}")

    recovered = bytes(((t - i) & 0xFF) ^ xor_key for i, t in enumerate(target))
    if not simulate_vm(recovered, bytecode, target):
        raise RuntimeError("Recovered candidate failed local VM verification.")

    return recovered.decode("utf-8")


def main() -> None:
    default_bin = Path(__file__).resolve().parent.parent / "dist" / "grimoire"
    target_bin = Path(sys.argv[1]) if len(sys.argv) > 1 else default_bin
    if not target_bin.is_file():
        print(f"[!] Binary not found: {target_bin}", file=sys.stderr)
        sys.exit(1)

    flag = solve(target_bin)
    print(f"[+] Flag        : {flag}")


if __name__ == "__main__":
    main()
