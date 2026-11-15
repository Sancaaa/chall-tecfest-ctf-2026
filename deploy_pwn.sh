#!/usr/bin/env bash
# deploy_pwn.sh -- rebuild + extract + bikin dist/*.zip untuk 6 soal Binary Exploitation.
#
# PENTING: jalankan dari WSL (Linux), BUKAN Git Bash/PowerShell langsung -- script ini
# butuh `strip`/`zip` Linux asli (biar ELF x86-64-nya kestrip benar, bukan toolchain
# Windows/MinGW yang kebetulan ada di PATH) dan `docker` yang connect ke Docker Desktop
# yang sama (WSL dengan integrasi Docker Desktop aktif sudah otomatis bisa).
#
# Pakai dari Git Bash/PowerShell:
#   export MSYS_NO_PATHCONV=1   (Git Bash saja, biar path /mnt/... tidak di-mangle)
#   wsl.exe -d kali-linux -- bash "/mnt/d/Universitas Udayana/UKM-KS/Tecart/2026/TecFest/Challenge & Competition/deploy_pwn.sh" [nama...]
#
# GOTCHA (ditemukan 15 Nov): kalau WSL (`kali-linux`) kebetulan punya install
# `docker` CLI SENDIRI yang terpisah dari Docker Desktop (cek `type -a docker`
# -- ada lebih dari satu, dan `/usr/bin/docker` menang di PATH tapi TIDAK
# punya plugin `compose` serta context default-nya bukan `desktop-linux`),
# script ini gagal dengan `docker: 'compose' is not a docker command` atau
# `Failed to initialize: protocol not available`, PADAHAL Docker Desktop di
# sisi Windows baik-baik saja. Cara cek: `wsl.exe -d kali-linux -- docker
# compose version` -- kalau error, JANGAN jalankan script ini apa adanya.
# Workaround kalau itu terjadi: jalankan bagian `docker compose`/`docker
# cp`/`docker exec` manual dari Git Bash (Windows), dan HANYA pakai WSL untuk
# `nm`/`strip`/`zip` (tulis ke file `.sh` kecil dulu lalu `wsl.exe -d
# kali-linux -- bash file.sh`, jangan nested `wsl.exe -- bash -c "..."` dari
# Git Bash langsung -- quoting-nya gampang pecah). Lihat
# `pwn_columbina/NOTES.md` bagian "Cara test ulang" untuk contoh lengkap
# urutan command manualnya.
#
# Atau dari dalam WSL langsung:
#   cd "/mnt/d/Universitas Udayana/UKM-KS/Tecart/2026/TecFest/Challenge & Competition"
#   bash deploy_pwn.sh                 # proses semua 6 soal
#   bash deploy_pwn.sh ei mavuika       # proses sebagian saja (nama folder atau nama binary, bebas)
#
# Tiap soal, urutannya: docker compose down -> build --no-cache -> up -d
# -> docker cp binary baru dari container ke bin/ (buat test lokal)
# -> (kalau punya attachment) strip SALINAN binary + zip ke dist/ (bin/ sendiri
#    TIDAK pernah di-strip -- itu dipakai solve.py buat exe.symbols[...]).
#
# KECUALI Istaroth & Columbina (UNIFIED=1 di CONFIGS) -- keduanya punya chaff
# yang butuh bin/ dan dist/ byte-identik (bukan cuma soal "simbol ketinggalan"):
# Istaroth punya symbol literal `decoy_win` yang langsung membocorkan mana
# fungsi asli/chaff kalau bin/ dibiarkan unstripped (QA jadi "curang" -- tidak
# pernah terbukti solve.py bisa benar-benar membedakan win vs decoy_win murni
# dari behavior, cuma baca nama). Columbina butuh glibc exact-match (heap/UAF),
# jadi bin/ juga perlu pakai libc/ld yang sama dengan yang dibagikan ke
# peserta, bukan cuma soal strip. Untuk keduanya: nm alamat SEBELUM strip,
# freeze ke addrs.py (auto-generated, dibaca solve.py), baru strip bin/$BIN
# IN-PLACE, dist/*.zip dibungkus dari file yang sama (bukan salinan terpisah).
#
# Mavuika/Furina/Sandrone TIDAK ikut mekanisme unified -- tidak ada decoy
# bernama apa pun di source-nya, jadi exe.symbols["win"] bukan kecurangan
# (alamat yang didapat persis sama dengan yang peserta temukan manual lewat
# nm/objdump di attachment yang sudah di-strip). Desain dual
# bin(unstripped)/dist(stripped ter-strip) lama tetap berlaku buat ketiganya.
#
# Ei: DAPAT attachment (revisi 14 Nov, lihat pwn_ei/NOTES.md & pwn_ei/readme --
# leak live `debug: access_granted @ %p` dihapus dari source, diganti binary
# dibagikan ke peserta supaya mereka cari sendiri alamatnya lewat nm/objdump).
# TIDAK di-strip -- itu justru bagian dari mekanisme soal (peserta memang
# dimaksudkan baca nama `access_granted` lewat nm), bukan oversight.
# CHALLENGE_DAN_HOSTING.md masih menyebut Ei "nc-only tanpa attachment" --
# itu BASI, sudah dikalahkan oleh revisi 14 Nov di atas.

set -u
cd "$(dirname "$0")"

# format: dirname:binname:has_attachment:needs_libc:unified:strip:symbols
#   unified=1 -> bin/$BIN di-strip in-place & == isi dist/ (Istaroth/Columbina saja).
#   unified=0 + strip=1 -> desain lama: bin/$BIN unstripped, dist/ = salinan ter-strip.
#   unified=0 + strip=0 -> Ei: dist/ = salinan APA ADANYA dari bin/$BIN (tanpa strip).
#   symbols   -> daftar nama simbol (pisah koma) yang di-nm SEBELUM strip dan
#   di-freeze ke addrs.py; hanya dipakai kalau unified=1.
CONFIGS=(
  "pwn_sandrone:sandrone:1:0:0:1:"
  "pwn_mavuika:mavuika:1:0:0:1:"
  "pwn_furina:furina:1:0:0:1:"
  "pwn_ei:ei:1:0:0:0:"
  "pwn_istaroth:istaroth:1:1:1:1:"
  "pwn_columbina:columbina:1:1:1:1:win"
)
# NOTE (revisi ret2libc): pwn_istaroth sekarang NEEDS_LIBC=1 (dulu 0) --
# v2 istaroth.c tidak punya win() siap pakai, exploit-nya ret2libc beneran
# (system() dari libc yang dibagikan), jadi attachment WAJIB sertakan
# libc.so.6 + ld-linux-x86-64.so.2 sama seperti Columbina. SYMBOLS juga
# dikosongkan (dulu "win") karena tidak ada lagi symbol lokal yang perlu
# di-freeze ke addrs.py -- kedua leak tahap 1 (alamat puts() yang di-resolve
# GLOB_DAT, alamat string "./catflag" sendiri) sudah berupa alamat absolut
# runtime yang langsung dipakai, solve.py tidak butuh offset statis dari
# bin/istaroth yang sudah di-strip.

RESULTS=()

for cfg in "${CONFIGS[@]}"; do
  IFS=":" read -r DIR BIN HAS_ATT NEEDS_LIBC UNIFIED STRIP SYMBOLS <<< "$cfg"

  # filter opsional dari argumen CLI -- cocok ke nama folder ATAU nama binary
  if [ "$#" -gt 0 ]; then
    match=0
    for want in "$@"; do
      if [ "$want" = "$DIR" ] || [ "$want" = "$BIN" ] || [ "pwn_$want" = "$DIR" ]; then
        match=1
      fi
    done
    [ "$match" -eq 0 ] && continue
  fi

  echo "##### $DIR #####"
  (
    set -e
    cd "$DIR"
    CONTAINER="pwn_${BIN}-${BIN}-1"
    WORKDIR="/home/${BIN}_pwn"

    docker compose down
    docker compose build --no-cache
    docker compose up -d

    # tunggu container benar-benar "running" sebelum docker cp (biasanya instan,
    # tapi jaga-jaga)
    for i in 1 2 3 4 5; do
      status="$(docker inspect -f '{{.State.Status}}' "$CONTAINER" 2>/dev/null || true)"
      [ "$status" = "running" ] && break
      sleep 1
    done

    docker cp "$CONTAINER:$WORKDIR/$BIN" "bin/$BIN"
    chmod +x "bin/$BIN"

    # istaroth: catflag juga di-refresh buat test lokal. catflag TIDAK didistribusikan
    # ke peserta (win() cuma execve ke ./catflag di server), jadi sengaja tidak
    # ikut masuk alur strip/addrs.py di bawah -- cukup unstripped buat debug lokal.
    if [ "$DIR" = "pwn_istaroth" ]; then
      docker cp "$CONTAINER:$WORKDIR/catflag" "bin/catflag"
      chmod +x "bin/catflag"
      cp -f flag.txt "bin/flag.txt"
    fi

    if [ "$HAS_ATT" = "1" ] && [ "$UNIFIED" = "1" ]; then
      # ===== Istaroth & Columbina: bin/$BIN == isi dist/*.zip (lihat komentar
      #       di atas file ini kenapa cuma dua soal ini yang butuh ini). =====

      # --- 1. Freeze alamat simbol dari binary yg MASIH unstripped, SEBELUM strip ---
      if [ -n "$SYMBOLS" ]; then
        ADDRS_FILE="addrs.py"
        BUILDID="$(readelf -n "bin/$BIN" 2>/dev/null | grep -o 'Build ID: [0-9a-f]*' | head -1)"
        {
          echo "# AUTO-GENERATED oleh deploy_pwn.sh -- JANGAN EDIT MANUAL, bakal ketimpa."
          echo "# nm diambil dari bin/$BIN SEBELUM di-strip (strip menghapus symbol"
          echo "# table) -- nilai di sini dipakai solve.py supaya tetap jalan lawan"
          echo "# bin/$BIN yang SUDAH di-strip, byte-identik dengan isi"
          echo "# dist/${BIN}_attachment.zip. Rebuild lewat deploy_pwn.sh kalau source"
          echo "# berubah, JANGAN edit angka di sini langsung."
          echo "# ${BUILDID:-BuildID tidak terbaca}"
          IFS=',' read -ra SYMS <<< "$SYMBOLS"
          for sym in "${SYMS[@]}"; do
            addr="$(nm "bin/$BIN" 2>/dev/null | awk -v s="$sym" '$3==s {print $1; exit}')"
            up="$(printf '%s' "$sym" | tr '[:lower:]' '[:upper:]')"
            if [ -z "$addr" ]; then
              echo "WARNING: symbol '$sym' tidak ketemu di bin/$BIN, addrs.py SALAH -- cek source/compile flags!" >&2
              echo "ADDR_${up} = None  # symbol '$sym' TIDAK KETEMU saat deploy -- cek ulang sebelum pakai!"
            else
              echo "ADDR_${up} = 0x${addr}"
            fi
          done
        } > "$ADDRS_FILE"
        echo "-> $DIR/$ADDRS_FILE diperbarui:"
        sed 's/^/     /' "$ADDRS_FILE"
      fi

      # --- 2. Strip bin/$BIN IN-PLACE -- ini sekarang satu-satunya binary test,
      #     dipakai juga buat isi dist/*.zip (tidak ada lagi salinan terpisah). ---
      chmod u+w "bin/$BIN"
      strip --strip-all "bin/$BIN"
      chmod 755 "bin/$BIN"

      # --- 3. Libc/ld yang dipin (kalau perlu, Columbina) -- ikut ditaruh di
      #     bin/ juga, supaya test lokal non-Docker pakai glibc yang SAMA dgn
      #     yg dibagikan ke peserta (bukan glibc sistem host). ---
      if [ "$NEEDS_LIBC" = "1" ]; then
        LIBC_REAL="$(docker exec "$CONTAINER" readlink -f /lib/x86_64-linux-gnu/libc.so.6)"
        LD_REAL="$(docker exec "$CONTAINER" readlink -f /lib64/ld-linux-x86-64.so.2)"
        docker cp "$CONTAINER:$LIBC_REAL" "bin/libc.so.6"
        docker cp "$CONTAINER:$LD_REAL" "bin/ld-linux-x86-64.so.2"
        chmod +x "bin/ld-linux-x86-64.so.2"
      fi

      # --- 4. Bungkus dist/*.zip langsung dari bin/$BIN yang sudah di-strip ---
      STAGE="$(mktemp -d)"
      DIST_ZIP="$(pwd)/dist/${BIN}_attachment.zip"

      cp "bin/$BIN" "$STAGE/$BIN"
      chmod 755 "$STAGE/$BIN"

      if [ "$NEEDS_LIBC" = "1" ]; then
        cp "bin/libc.so.6" "$STAGE/libc.so.6"
        cp "bin/ld-linux-x86-64.so.2" "$STAGE/ld-linux-x86-64.so.2"
        chmod +x "$STAGE/ld-linux-x86-64.so.2"
      fi

      rm -f "$DIST_ZIP"
      ( cd "$STAGE" && zip -q -X "$DIST_ZIP" ./* )
      rm -rf "$STAGE"
      echo "-> dist/${BIN}_attachment.zip dibuat ($(du -h "$DIST_ZIP" | cut -f1)), isi:"
      unzip -l "$DIST_ZIP" | awk 'NR>3 {print "     " $0}'

    elif [ "$HAS_ATT" = "1" ]; then
      # ===== Sandrone/Mavuika/Furina: desain lama -- bin/$BIN TETAP unstripped
      #       (dipakai exe.symbols[...] di solve.py), dist/ = salinan terpisah
      #       yang di-strip. Tidak ada decoy bernama apa pun di soal-soal ini,
      #       jadi tidak ada yang perlu disembunyikan dari bin/.
      #       Ei (STRIP=0): dist/ = salinan APA ADANYA, TIDAK di-strip -- lihat
      #       komentar di atas file ini, ini bagian dari mekanisme soal. =====
      STAGE="$(mktemp -d)"
      DIST_ZIP="$(pwd)/dist/${BIN}_attachment.zip"

      cp "bin/$BIN" "$STAGE/$BIN"
      chmod u+w "$STAGE/$BIN"   # bin/$BIN ke-extract mode 550 (lihat Dockerfile) -- strip butuh write
      if [ "$STRIP" = "1" ]; then
        strip --strip-all "$STAGE/$BIN"
      fi
      chmod 755 "$STAGE/$BIN"

      if [ "$NEEDS_LIBC" = "1" ]; then
        LIBC_REAL="$(docker exec "$CONTAINER" readlink -f /lib/x86_64-linux-gnu/libc.so.6)"
        LD_REAL="$(docker exec "$CONTAINER" readlink -f /lib64/ld-linux-x86-64.so.2)"
        docker cp "$CONTAINER:$LIBC_REAL" "$STAGE/libc.so.6"
        docker cp "$CONTAINER:$LD_REAL" "$STAGE/ld-linux-x86-64.so.2"
        chmod +x "$STAGE/ld-linux-x86-64.so.2"
      fi

      rm -f "$DIST_ZIP"
      ( cd "$STAGE" && zip -q -X "$DIST_ZIP" ./* )
      rm -rf "$STAGE"
      echo "-> dist/${BIN}_attachment.zip dibuat ($(du -h "$DIST_ZIP" | cut -f1)), isi:"
      unzip -l "$DIST_ZIP" | awk 'NR>3 {print "     " $0}'
    else
      echo "-> tidak ada attachment untuk $BIN (sengaja, lihat readme/NOTES.md)"
    fi
  )
  if [ $? -eq 0 ]; then
    RESULTS+=("OK     $DIR")
  else
    RESULTS+=("GAGAL  $DIR -- cek log di atas")
  fi
  echo
done

echo "===== Ringkasan ====="
for r in "${RESULTS[@]}"; do echo "$r"; done
