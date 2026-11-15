import socket
import json
import numpy as np

def rotation_matrix(v, direction=1):
    x, y, z = v
    cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.outer(v, v) - direction * cross

def decode_center(v, R_mat):
    v = tuple(v)
    R1 = rotation_matrix(v, 1)
    candidates = [
        np.identity(3, dtype=int),
        R1,
        R1 @ R1,
        rotation_matrix(v, -1)
    ]
    for k, cand in enumerate(candidates):
        if np.array_equal(R_mat, cand):
            return k
    raise ValueError(f"Unknown rotation matrix for center {v}")

def solve(host="127.0.0.1", port=13337):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    buffer = ""
    while "{" not in buffer:
        chunk = s.recv(1024).decode()
        if not chunk:
            break
        buffer += chunk

    # Cari awal JSON
    idx = buffer.find("{")
    banner = buffer[:idx]
    print(banner, end="")
    buffer = buffer[idx:]

    while "\n" not in buffer:
        chunk = s.recv(4096).decode()
        if not chunk:
            break
        buffer += chunk

    json_line, remainder = buffer.split("\n", 1)
    data = json.loads(json_line)

    channels = data["channels"]
    cubes = data["cubes"]

    decoded_chars = []
    for cube in cubes:
        piece_map = {tuple(p["c"]): np.array(p["R"], dtype=int) for p in cube["pieces"]}
        digits = []
        for ch in channels:
            coord = tuple(ch["c"])
            R_mat = piece_map[coord]
            digits.append(decode_center(coord, R_mat))

        ascii_val = (digits[0] << 6) | (digits[1] << 4) | (digits[2] << 2) | digits[3]
        decoded_chars.append(chr(ascii_val))

    token = "".join(decoded_chars)
    print(f"[*] Decoded 13-character Token: {token}")

    # Kirim token kembali ke server
    s.sendall((token + "\n").encode())

    # Terima respons flag
    response = s.recv(2048).decode()
    print(response)

    s.close()
    return token, response

if __name__ == "__main__":
    solve()
