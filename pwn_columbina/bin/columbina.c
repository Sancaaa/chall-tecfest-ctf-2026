// Binary Exploitation F - Columbina (v2 -- tcache poisoning, safe-linking)
// Topik: Heap exploitation. UAF (lepas fragmen tanpa null) + UAF-WRITE
//   (ukir ulang nama fragmen yang sudah dilepas) -> tcache poisoning
//   (bypass safe-linking glibc >= 2.32) -> arbitrary write -> function
//   pointer hijack.
// Protections: full modern (NX on, canary on) + PIE off (sengaja, lihat catatan di
//   BINEXP_PLANNING.md - heap chall ini fokus ke mekanisme tcache, bukan ke defeat PIE
//   lagi, supaya tidak menumpuk 2 skill sekaligus di 1 soal). glibc di-pin via digest base image.
//
// Gimmick (lihat ref/ -- rekap lore Luna 3 & Luna 4 di Nod-Krai): Columbina baru benar-benar
// "ada" kalau tiga komponen bersatu di satu eksistensi yang sama -- tubuh (nama/identitas),
// jiwa (tersimpan pasif, seperti Luonnotar: tidak pernah dipanggil di jalur normal), dan
// otoritas (fungsi yang dipanggil untuk mengonfirmasi dia benar-benar Columbina). UAF di
// soal ini merepresentasikan itu secara harfiah: fragmen yang "dilepas" ke Moon's Reflection
// tidak pernah benar-benar hilang (bug -> dangling pointer) -- dan DUNIA MASIH MENDENGARKAN
// gaung fragmen itu (BARU di v2: "ukir ulang nama" lewat fragmen yang sudah dilepas tetap
// berhasil, bug UAF-write) -- gaung inilah yang dipakai memanipulasi arus Luonnotar (tcache)
// supaya entri baru "diarahkan" ke eksistensi lain yang masih hidup, menyatukan otoritas-nya
// paksa di sana -- bukan cuma menulis ulang fragmen yang sama seperti versi awal.
// Chaff flag: opsi menu "7" selalu mencetak flag SALAH (marrow sintetis ala False Moon
//   Institute Dottore -- otoritas Trilunar tiruan, bukan Columbina asli) tanpa butuh
//   eksploitasi apapun -- menjebak enumerasi membabi-buta/AI yang coba semua opsi. Flag
//   asli hanya lewat tcache poisoning penuh.
//
// Revisi dari v1: v1 cuma butuh UAF + reuse-by-size (malloc ukuran sama balikin chunk
// yang sama persis) -- TIDAK butuh leak apapun (PIE sudah off) dan TIDAK menyentuh
// mekanisme tcache `fd`/safe-linking sama sekali (cuma 1 chunk pernah ada di bin itu,
// jadi field metadata-nya tidak pernah relevan). Itu terbukti cuma level Medium (lihat
// diskusi difficulty review sebelum revisi ini), setara Furina/Sandrone, bukan Hard.
// v2 menambah SATU bug baru (UAF-WRITE lewat "ukir ulang nama") yang secara spesifik
// memungkinkan tcache poisoning: korupsi field `next` (fd) chunk yang masih nangkring
// di tcache SEBELUM di-pop ulang oleh malloc, lewat formula safe-linking
// (`mangled = (chunk_addr >> 12) ^ target`) yang WAJIB dihitung peserta sendiri pakai
// alamat heap yang di-leak program (menu "1" sekarang print alamat chunk-nya, pola yang
// sama dipakai Sandrone buat leak stack). Genuinely menuntut pemahaman internal tcache
// glibc >= 2.32, + 1 leak heap -- tanpa perlu nyalain PIE (lihat NOTES.md untuk detail
// penuh teknik & urutan langkahnya).
//
// Fix lanjutan (ditemukan via blackbox test, lihat TESTING_PWN/pwn_columbina/ +
// NOTES.md bagian "Kerentanan v2 yang diperbaiki"): opsi 5 awalnya masih
// mengizinkan `panjang` sampai sizeof(struct eksistensi)=40 byte -- itu
// membuka jalan pintas balik ke teknik v1 (free SATU chunk, langsung reuse
// via opsi 5 dengan panjang=40, overwrite offset 32 `otoritas` dalam SATU
// panggilan, tanpa fragmen ke-3/UAF-write/safe-linking math apa pun). `panjang`
// sekarang dibatasi maks 16 byte -- cukup buat 2 langkah LEGIT teknik v2 (0
// byte konsumsi, 8 byte tulis alamat win() ke target yang sudah diracun),
// tapi tidak akan pernah cukup menjangkau offset 32 dalam satu tulisan mentah
// dari offset 0 pada SATU chunk yang baru direuse -- jalan pintas v1 tertutup.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAX_FRAGMEN 16
// Flag palsu: marrow sintetis buatan False Moon Institute -- meniru otoritas Trilunar asli,
// tapi bukan Columbina. Tidak butuh eksploitasi apapun untuk dicetak (lihat NOTES.md).
#define CHAFF_FLAG  "TecFest26{false_moon_marrow_is_not_columbina}"

// Satu fragmen eksistensi Columbina di Moon's Reflection: nama (jangkar identitas,
// offset 0), jiwa (tersimpan pasif seperti di Luonnotar -- tidak pernah dipanggil di
// jalur normal, offset 24), dan otoritas (fungsi yang dipanggil saat fragmen ini
// "diuji" sebagai Columbina yang sah, offset 32). Total 40 byte -- dicek lewat program
// kecil sizeof/offsetof terpisah saat development.
struct eksistensi {
    char nama[24];
    void (*jiwa)(struct eksistensi *);      // tidak pernah dipanggil di jalur normal
    void (*otoritas)(struct eksistensi *);  // target asli, dipanggil menu "4"
};

struct eksistensi *fragmen[MAX_FRAGMEN];

// Otoritas fana: fragmen ini baru punya nama, belum punya jiwa & otoritas Trilunar yang
// utuh -- jadi dunia belum mengenalinya sebagai Columbina seutuhnya.
void otoritas_fana(struct eksistensi *p) {
    printf("%s belum dikenali dunia secara utuh.\n", p->nama);
}

char flag[256];

// Tubuh, jiwa, dan otoritas akhirnya bersatu di fragmen yang sama -- Columbina pulih.
void win(struct eksistensi *p) {
    (void)p;
    puts("Tubuh, jiwa, dan otoritas bersatu -- Columbina pulih.");
    fputs(flag, stdout);
}

static long read_long(const char *prompt) {
    char line[64];
    printf("%s", prompt);
    fflush(stdout);
    if (!fgets(line, sizeof(line), stdin)) exit(0);
    return strtol(line, NULL, 0);
}

static void read_line(char *buf, size_t n) {
    if (fgets(buf, n, stdin)) {
        size_t l = strcspn(buf, "\n");
        buf[l] = 0;
    }
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);

    // Baca flag SEKALI DI PALING AWAL (sebelum interaksi apa pun) -- kalau
    // filenya tidak ada, langsung ketahuan & exit di sini juga (bisa diganti),
    // bukan baru ketahuan setelah berhasil exploit. win() cuma print buffer
    // ini, tidak buka file lagi -- satu-satunya tempat yang perlu nge-handle
    // "flag tidak ada" ya di sini, bukan dobel.
    FILE *f = fopen("flag.txt", "r");
    if (!f) {
        puts("Buat flag.txt di directory ini untuk debugging.");
        return 1;
    }
    fgets(flag, sizeof(flag), f);
    fclose(f);

    puts("=== Moon's Reflection: Rekonstruksi Eksistensi Columbina ===");
    while (1) {
        printf("\n1. Catat fragmen eksistensi\n"
                 "2. Lepas fragmen ke Moon's Reflection\n"
                 "3. Ukir ulang nama fragmen\n"
                 "4. Uji otoritas fragmen\n"
                 "5. Tulis entri Luonnotar (raw, dipakai buat reuse/redirect chunk)\n"
                 "6. Keluar\n"
                 "7. Marrow sintetis (pengganti darurat)\n> ");
        fflush(stdout);
        long choice = read_long("");

        if (choice == 1) {
            long idx = read_long("slot: ");
            if (idx < 0 || idx >= MAX_FRAGMEN) { puts("slot invalid."); continue; }
            fragmen[idx] = malloc(sizeof(struct eksistensi));
            if (!fragmen[idx]) { puts("alloc gagal."); continue; }
            fragmen[idx]->jiwa = NULL;
            fragmen[idx]->otoritas = otoritas_fana;
            printf("nama: ");
            fflush(stdout);
            read_line(fragmen[idx]->nama, sizeof(fragmen[idx]->nama));
            // Leak -- gaung fragmen ini bersemayam di alamat heap tertentu.
            // Pola yang sama dengan debug leak stack di Sandrone (lihat
            // pwn_sandrone/bin/sandrone.c) -- di sini dipakai buat menghitung
            // formula safe-linking tcache, BUKAN buat defeat PIE (PIE sudah
            // off, tidak relevan di sini).
            printf("fragmen baru bersemayam di %p\n", (void *)fragmen[idx]);
        } else if (choice == 2) {
            long idx = read_long("slot: ");
            if (idx < 0 || idx >= MAX_FRAGMEN) { puts("slot invalid."); continue; }
            free(fragmen[idx]);
            // BUG 1: fragmen[idx] sengaja TIDAK di-NULL-kan -> dangling pointer (UAF).
        } else if (choice == 3) {
            long idx = read_long("slot: ");
            if (idx < 0 || idx >= MAX_FRAGMEN) { puts("slot invalid."); continue; }
            // BUG 2 (BARU di v2): TIDAK ada pengecekan apakah fragmen ini
            // sudah "dilepas" (di-free) atau belum -- UAF WRITE lewat
            // fragmen[idx] yang masih dangling. read() RAW (bukan fgets/
            // read_line) supaya byte apa pun (termasuk 0x00 dan nilai
            // pointer mentah) bisa ditulis penuh tanpa kepotong newline --
            // field `nama` (24 byte) pas menimpa seluruh metadata tcache
            // `next`+`key` (16 byte pertama) kalau slot ini sedang berada
            // di freelist tcache.
            printf("nama baru (%zu byte, raw): ", sizeof(fragmen[idx]->nama));
            fflush(stdout);
            read(0, fragmen[idx]->nama, sizeof(fragmen[idx]->nama));
        } else if (choice == 4) {
            long idx = read_long("slot: ");
            if (idx < 0 || idx >= MAX_FRAGMEN) { puts("slot invalid."); continue; }
            fragmen[idx]->otoritas(fragmen[idx]);
        } else if (choice == 5) {
            // Alokasi "entri Luonnotar" seukuran struct eksistensi supaya allocator
            // (tcache) menggunakan kembali/redirect chunk sesuai state tcache bin
            // saat ini. `panjang` BISA 0 (dipakai buat langkah "konsumsi" chunk
            // tanpa menulis apa pun -- lihat NOTES.md teknik tcache poisoning).
            //
            // BATAS SENGAJA cuma 16 byte (BUKAN sizeof(struct eksistensi)=40) --
            // ditemukan lewat blackbox test (lihat NOTES.md "Kerentanan v2 yang
            // diperbaiki") bahwa kalau batasnya 40, satu panggilan opsi ini
            // langsung bisa menimpa offset 32 (`otoritas`) pada chunk yang BARU
            // di-free sendiri (free + reuse SATU chunk, tanpa fragmen ke-3, tanpa
            // UAF-write opsi 3, tanpa hitung safe-linking) -- balik ke teknik v1
            // yang trivial. 16 byte cukup buat kebutuhan LEGIT teknik v2 (0 byte
            // buat konsumsi, 8 byte buat tulis alamat win() ke `target` yang
            // sudah diracun), tapi TIDAK PERNAH cukup buat mencapai offset 32
            // dalam satu tulisan mentah mulai dari offset 0 -- memaksa peserta
            // genuinely pakai tcache poisoning, bukan reuse langsung.
            long note_id = read_long("entri Luonnotar (0-15, bebas): ");
            if (note_id < 0 || note_id >= MAX_FRAGMEN) { puts("id invalid."); continue; }
            long len = read_long("panjang (0-16): ");
            if (len < 0 || len > 16) { puts("panjang invalid."); continue; }
            void *note = malloc(sizeof(struct eksistensi));
            if (!note) { puts("alloc gagal."); continue; }
            if (len > 0) {
                printf("entri (%ld byte, raw): ", len);
                fflush(stdout);
                read(0, note, len);
            }
            // entri sengaja tidak disimpan ke slot manapun - tujuannya murni supaya
            // allocator pop/redirect entry tcache yang sedang jadi head.
        } else if (choice == 7) {
            puts(CHAFF_FLAG);
        } else {
            break;
        }
    }
    return 0;
}
