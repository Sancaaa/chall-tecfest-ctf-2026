# toy.sage — contoh HNP angka kecil untuk dokumen matematis.
# Abstraksi: lupakan kurva, pakai t_i, a_i langsung. k_i = a_i + t_i*d mod n, k_i kecil.
n = 10007            # modulus kecil (~14 bit) menggantikan orde kurva
d = 1234             # "private key" rahasia
K = 128              # batas atas nonce kecil: k_i < K  (~7 bit, jadi bocor ~7 bit)

t = [5915, 2134, 8201]          # "t_i" (acak), ibarat r_i/s_i
k = [42, 7, 88]                 # nonce kecil rahasia
a = [(k[i] - t[i]*d) % n for i in range(3)]   # a_i dipilih agar k_i = a_i + t_i*d mod n
m = len(t)

print("a_i =", a)
print("cek k_i = a_i + t_i*d mod n :", [(a[i] + t[i]*d) % n for i in range(m)])

# lattice (m+2) x (m+2), gaya Boneh-Venkatesan / repo
M = Matrix(QQ, m+2, m+2)
for i in range(m):
    M[i, i] = n
for i in range(m):
    M[m,   i] = t[i]
    M[m+1, i] = a[i]
M[m,   m]   = QQ(K)/n
M[m+1, m+1] = K
print("\n--- Basis M (sebelum reduksi) ---")
print(M)

R = M.LLL()
print("\n--- Setelah LLL ---")
print(R)

print("\n--- Ekstraksi d dari tiap baris ---")
for idx, row in enumerate(R.rows()):
    dcol = row[-2]                      # kolom = d*K/n
    if dcol != 0:
        cand = (ZZ(dcol * n / K)) % n
        print(f"baris {idx}: dcol={dcol}  -> cand_d={cand}  {'<-- COCOK' if cand==d else ''}")
