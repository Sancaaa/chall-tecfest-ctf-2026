"""Membuat sample_transmission.json: contoh transmisi dengan format dan konvensi yang
sama persis dengan server (memakai fungsi server.py, bukan salinan terpisah supaya tidak melenceng)."""
import json
import os
import random

import server

SAMPLE_TEXT = "The sustainer of heavenly principles."
SAMPLE_SEED = 37

# Urutan MSB -> LSB untuk sampel: Right (+Y), Front (+X), Top (+Z), Left (-Y)
SAMPLE_CHANNELS = [[0, 1, 0], [1, 0, 0], [0, 0, 1], [0, -1, 0]]

def dump_compact(transmission):
    """JSON valid yang sama dengan json.dump, tapi satu keping per baris (bukan satu angka per baris)."""
    line = json.dumps
    out = ['{', '  "channels": [']
    out.append(",\n".join("    " + line(ch) for ch in transmission["channels"]))
    out += ['  ],', '  "cubes": [']
    cubes = []
    for cube in transmission["cubes"]:
        pieces = ",\n".join("        " + line(p) for p in cube["pieces"])
        cubes.append(
            '    {\n'
            f'      "cube_id": {cube["cube_id"]},\n'
            '      "pieces": [\n'
            f'{pieces}\n'
            '      ]\n'
            '    }'
        )
    out.append(",\n".join(cubes))
    out += ['  ]', '}']
    return "\n".join(out) + "\n"

def main(out_dir="."):
    by_coord = {tuple(v["c"]): v for v in server.UNIT_VECTORS}
    channels = [dict(by_coord[tuple(c)], channel=i) for i, c in enumerate(SAMPLE_CHANNELS)]

    rng = random.Random(SAMPLE_SEED)
    transmission = {
        "channels": channels,
        "cubes": server.generate_challenge(SAMPLE_TEXT, channels, rng),
    }

    with open(os.path.join(out_dir, "sample_transmission.json"), "w") as f:
        f.write(dump_compact(transmission))

    with open(os.path.join(out_dir, "sample_decoded.txt"), "w") as f:
        f.write(SAMPLE_TEXT + "\n")

    print(f"Sample generated successfully! Token length: {len(SAMPLE_TEXT)}")

if __name__ == "__main__":
    main()
