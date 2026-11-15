"""
Solver resmi: Aku Suka Kessoku Band
Kategori: Forensic

Usage:
    python solve.py kessoku_band.flac
"""

import sys
import base64

def solve_part2(flac_path: str) -> str:
    """Ekstrak dan decode Part 2 dari metadata COMMENT."""
    try:
        # Coba pakai mutagen (pip install mutagen)
        from mutagen.flac import FLAC
        audio = FLAC(flac_path)
        comment = audio.tags.get("comment", [None])[0]
        if not comment:
            raise ValueError("Field COMMENT tidak ditemukan di metadata.")
    except ImportError:
        print("[!] mutagen tidak terinstall. Jalankan: pip install mutagen")
        sys.exit(1)

    print(f"[*] COMMENT raw: {comment[:60]}...")

    result = comment
    for i in range(7):
        result = base64.b64decode(result).decode("utf-8")
        print(f"[*] Decode x{i+1}: {result[:60]}{'...' if len(result) > 60 else ''}")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python solve.py <path_to_flac>")
        sys.exit(1)

    flac_file = sys.argv[1]
    print("=" * 60)
    print("  Solver: Aku Suka Kessoku Band — Forensic")
    print("=" * 60)
    print()

    print("[+] Solving Part 2 (Metadata COMMENT — Base64 x7)...")
    part2 = solve_part2(flac_file)
    print(f"\n[+] Part 2: {part2}")

    print()
    print("[!] Part 1 harus diekstrak secara manual via Spectrogram:")
    print("    Tool: Sonic Visualiser / Audacity / librosa")
    print("    Lihat bagian AKHIR audio pada visualisasi spectrogram.")
    print()
    print("[+] Gabungkan Part 1 + Part 2 untuk mendapatkan flag lengkap!")
