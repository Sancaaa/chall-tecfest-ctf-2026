// Binary Exploitation A - Sandrone
// Topik: Shellcode injection (NX off) + badchar-free XOR payload encoding.
// Protections (wajib dicek via checksec saat build): NX off, canary off, PIE off
//
// Desain dua channel (lihat NOTES.md "Revisi badchar/XOR"):
//   1. "payload diagnostik"  -> disanitasi (fgets + strcpy), BUKAN raw read.
//      strcpy berhenti di byte NUL (0x00) pertama, fgets berhenti di '\n' (0x0a)
//      -> dua badchar ini MUNCUL SENDIRI dari cara fungsi ini bekerja, bukan
//      filter buatan yang sengaja nolak byte tertentu. Shellcode yang ditaruh
//      di sini wajib di-encode (XOR) supaya lolos tanpa mengandung 0x00/0x0a.
//   2. "kontrol overflow"    -> raw read(), TIDAK disanitasi, dipakai buat
//      overflow return address asli (supaya return address -- yang hampir
//      pasti mengandung byte NUL di 2 byte teratas alamat stack -- tetap bisa
//      ditulis utuh tanpa kepotong strcpy).
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

void vuln(void) {
    // Satu array gabungan, dibagi manual lewat pointer -- BUKAN dua `char[]`
    // terpisah. Ini sengaja: urutan 2 variabel lokal terpisah bergantung
    // heuristik gcc (bisa taruh urutan beda dari urutan deklarasi), sedangkan
    // index di dalam SATU array dijamin standar C selalu naik alamatnya.
    // frame[0..127]   = payload (shellcode ter-encode, alamat LEBIH RENDAH)
    // frame[128..191] = buf (overflow target asli, alamat LEBIH TINGGI)
    // -> read(fd, buf, 256) menulis maju (alamat naik) dari buf, jadi TIDAK
    // PERNAH menimpa balik payload yang sudah diisi channel 1 sebelumnya.
    char frame[128 + 64];
    char *payload = frame;
    char *buf = frame + 128;

    // buf ada di STACK -> alamatnya tetap diacak ASLR terlepas dari ada/tidaknya
    // attachment binary (ASLR stack independen dari PIE, dan tidak tercatat statis
    // di file binary manapun) -> program sendiri yang leak alamatnya supaya peserta
    // tidak perlu disable ASLR di level kernel (butuh privileged container).
    // payload ada di frame yang sama -> offset-nya relatif terhadap buf TETAP
    // (properti statis stack frame, dicek lewat objdump, sama seperti offset
    // return address).
    printf("debug: buf @ %p\n", (void *)buf);
    fflush(stdout);

    char net_buf[300];
    printf("payload diagnostik: ");
    fflush(stdout);
    if (!fgets(net_buf, sizeof(net_buf), stdin)) return;
    strcpy(payload, net_buf); // VULNERABLE tapi disengaja sebagai "sanitizer": berhenti di NUL

    printf("kontrol overflow: ");
    fflush(stdout);
    read(0, buf, 256); // sengaja overflow mentah: buf cuma 64 byte (dari frame), dibaca sampai 256 byte
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);

    // Cek file flag DI PALING AWAL (sebelum interaksi apa pun) -- supaya kalau
    // dites dari attachment/dist tanpa flag yang benar, langsung ketahuan dan
    // bisa diganti, bukan baru ketahuan setelah berhasil exploit.
    FILE *flag_check = fopen("flag.txt", "r");
    if (!flag_check) {
        puts("Buat flag.txt di directory ini untuk debugging.");
        return 1;
    }
    fclose(flag_check);

    vuln();
    puts("selesai.");
    return 0;
}
