import base64

INTERNAL_MEMO_TEXT = (
    "[INTERNAL MEMO - DO NOT EXPOSE] Malam 14/08/2024: Cold-deck aktif di Meja VIP "
    "untuk menjatuhkan target BIMA. Jam Rolex korban disita dan digadaikan senilai "
    "Rp 65jt untuk tutup utang margin. Kode insiden: BIMA-404."
)
INTERNAL_MEMO_B64 = base64.b64encode(INTERNAL_MEMO_TEXT.encode("utf-8")).decode("ascii")

SHIFT_RECEIPT_TEXT = """==================================================
VELVET PALACE CASINO - VIP ROOM 777
SHIFT THERMAL RECEIPT (AUTO-ARCHIVED)
==================================================
TIMESTAMP   : 02:14 WIB
DEALER      : REYNALDI PRATAMA (VELVET KING)
STATUS      : OVERDUE LOAN WARNING [PINJOL KILAT x4]

[MUTASI DARURAT TERDETEKSI]
SOURCE ACCT : KAS DONASI - PANTI HARAPAN
NOMINAL     : Rp 48.500.000,-
CATATAN     : Penutupan bunga pinjol & margin kalah slot
DOC_REF     : PANTI-9042
==================================================
"""

VAULT_CONFESSION_TEXT = (
    "[03:17 WIB] Selisih kas brankas Sindikat -$50,000 atas nama Reynaldi. "
    "Audit Code: SYNDICATE-777. Catatan pribadi pelaku: "
    "\"Mereka bilang aku sakit, tapi bagiku judi adalah jalan ninja ku. "
    "Jika bos besar tahu soal SYNDICATE-777, aku mati malam ini.\""
)
VAULT_AUDIT_LOG = f"""=== SYNDICATE SECURITY VAULT AUDIT ===
NODE: VIP-ROOM-777-TERMINAL
TYPE: ENCRYPTED_CONFESSION_FRAGMENT
ENCODING: hex

PAYLOAD_HEX:
{VAULT_CONFESSION_TEXT.encode("utf-8").hex()}
========================================
"""

STAGES = {
    1: {
        "stage": 1,
        "title": "BABAK 1 // TOPENG MORALIS ELIT",
        "dealer_prompt": (
            "Kau ingin menggertakku? Lihat sekelilingmu! Aku berdiri dengan setelan "
            "jas bersih dan uang halal meja VIP. Aku bukan penjudi receh yang "
            "menggadaikan harga diri demi uang haram."
        ),
        "tactics": [
            {"id": "A", "label": "Puji kehebatannya bermain kartu agar dia lengah"},
            {"id": "B", "label": "Kuliti kemunafikannya dengan menyindir uang donasi yang dia pakai melunasi pinjol"},
            {"id": "C", "label": "Ancam akan melaporkannya ke polisi umum sekarang juga"},
        ],
        "correct_tactic": "B",
        "valid_evidence": {"PANTI-9042", "REF-PANTI-9042"},
        "hit_line": (
            "A-apa?! Dari mana kau dapat nomor referensi transfer Panti Harapan itu?! "
            "Dengar, itu cuma pinjaman darurat sementara—bunganya mencekik leherku! "
            "Jangan bicara sembarangan!"
        ),
        "next_mood": "sweating",
    },
    2: {
        "stage": 2,
        "title": "BABAK 2 // TOPENG FAIR PLAY",
        "dealer_prompt": (
            "Diam! Itu cuma masa lalu keuangan yang kacau. Sebagai dealer, aku tetap suci! "
            "Di atas meja hijau ini, aku tidak pernah curang dan selalu menghormati "
            "persaudaraan serta aturan main!"
        ),
        "tactics": [
            {"id": "A", "label": "Tantang dia adu duel All-In satu ronde lagi"},
            {"id": "B", "label": "Hantam rasa bersalahnya dengan menyebut nama sahabat yang dia hancurkan lewat kecurangan cold-deck"},
            {"id": "C", "label": "Ejek caranya mengocok kartu di depan kamera CCTV"},
        ],
        "correct_tactic": "B",
        "valid_evidence": {"BIMA-404", "BIMA-ROLEX-404"},
        "hit_line": (
            "Cukup! Jangan sebut nama Bima di meja ini!! Dia... dia memang temanku, "
            "tapi malam itu aku butuh uang! Jam Rolex itu cuma jadi jaminan... "
            "Aku tidak berniat menjualnya secepat itu! Sialan, kata-katamu..."
        ),
        "next_mood": "panicking",
    },
    3: {
        "stage": 3,
        "title": "BABAK 3 // TOPENG ANAK BERBAKTI",
        "dealer_prompt": (
            "Kau tidak mengerti apa pun! Semua dosa yang kulakukan... uang panti, "
            "pengkhianatan itu... semuanya demi ibuku! Demi biaya rumah sakit ibuku! "
            "Aku melakukan ini karena aku anak yang berbakti!"
        ),
        "tactics": [
            {"id": "A", "label": "Bongkar kebohongannya bahwa ia justru menilep uang asuransi ibunya demi berjudi online"},
            {"id": "B", "label": "Tawarkan pinjaman uang supaya dia bisa menebus kesalahan"},
            {"id": "C", "label": "Tertawakan nasib malang keluarganya"},
        ],
        "correct_tactic": "A",
        "valid_evidence": {"KING_MAXWIN88", "KINGMAXWIN88", "POLIS-FAKE-119"},
        "hit_line": (
            "T-tidak... Tolong jangan keras-keras... Username itu... "
            "Aku cuma berpikir sekali maxwin lagi aku bisa melunasi ruang VIP untuk ibu! "
            "Aku bukan monster... Aku cuma terjebak putaran kekalahan..."
        ),
        "next_mood": "cornered",
    },
    4: {
        "stage": 4,
        "title": "BABAK 4 // ALL-OUT BREAKDOWN",
        "dealer_prompt": (
            "Mau mu apa sekarang?! Harga diriku sudah kau injak-injak! Tapi kau tidak "
            "punya kendali atas hidupku. Bos Sindikat masih percaya penuh padaku di "
            "ruang 777 ini. Kau tidak bisa menyentuhku!"
        ),
        "tactics": [
            {"id": "A", "label": "Minta dia mengembalikan semua uang panti besok pagi"},
            {"id": "B", "label": "Suruh dia mengundurkan diri sebagai dealer secara baik-baik"},
            {"id": "C", "label": "Todong dengan bukti penggelapan kas Sindikat dan bentak bahwa bos besar akan menghabisi dirinya malam ini jika brankas tak dibuka"},
        ],
        "correct_tactic": "C",
        "valid_evidence": {"SYNDICATE-777", "AUDIT-SYNDICATE-777"},
        "hit_line": (
            "JANGAN KIRIM LOG ITU KE BOS BESAR!! TOLONG!! Aku... aku mengaku! Aku tilep $50,000 "
            "dari brankas sindikat! Malam itu aku mabuk dan menulis bahwa judi adalah jalan ninjaku "
            "karena aku sudah tidak punya siapa-siapa lagi! Aku kalah... Aku menyerah! "
            "Ambil kode brankas dan flag sialan itu, biarkan aku pergi dari sini!"
        ),
        "next_mood": "broken",
    },
}


def public_confront_view(state: dict) -> dict:
    stage_num = min(state.get("interrogation_stage", 1), 4)
    stage = STAGES[stage_num]
    return {
        "stage": stage_num,
        "title": stage["title"],
        "dealer_prompt": stage["dealer_prompt"],
        "tactics": stage["tactics"],
        "composure": state.get("composure", 100),
        "strikes": state.get("strikes", 0),
        "max_strikes": 3,
        "dealer_mood": state.get("dealer_mood", "smug"),
        "won": state.get("won_by") is not None,
    }


def submit_confrontation(state: dict, tactic: str, evidence: str, flag_value: str) -> dict:
    if state.get("won_by") is not None:
        return {
            "hit": True,
            "broken": True,
            "message": STAGES[4]["hit_line"],
            "flag": flag_value,
        }

    stage_num = state.get("interrogation_stage", 1)
    stage = STAGES[stage_num]
    norm_tactic = (tactic or "").strip().upper()
    norm_evidence = (evidence or "").strip().upper()

    tactic_ok = norm_tactic == stage["correct_tactic"]
    evidence_ok = norm_evidence in stage["valid_evidence"]

    if tactic_ok and evidence_ok:
        state["composure"] = max(0, state["composure"] - 25)
        state["dealer_mood"] = stage["next_mood"]
        state["dealer_line"] = stage["hit_line"]

        if stage_num == 4 or state["composure"] == 0:
            state["composure"] = 0
            state["won_by"] = "blackmail"
            return {
                "hit": True,
                "broken": True,
                "message": stage["hit_line"],
                "flag": flag_value,
            }

        state["interrogation_stage"] = stage_num + 1
        return {
            "hit": True,
            "broken": False,
            "message": stage["hit_line"],
        }

    state["strikes"] = state.get("strikes", 0) + 1
    if state["strikes"] >= 3:
        state["interrogation_stage"] = 1
        state["composure"] = 100
        state["strikes"] = 0
        state["dealer_mood"] = "smug"
        kick_msg = (
            "Cukup bualanmu! Tiga kali kau menggertak kosong. Kembali ke meja poker "
            "atau keluar dari Ruang 777!"
        )
        state["dealer_line"] = kick_msg
        return {
            "hit": False,
            "kicked_out": True,
            "message": kick_msg,
        }

    if tactic_ok and not evidence_ok:
        miss_msg = "Omonganmu tajam, tapi mana buktinya?! Kode bukti itu salah atau omong kosong!"
    elif not tactic_ok and evidence_ok:
        miss_msg = "Fakta itu ada benarnya, tapi cara menekanku payah! Aku tidak gentar!"
    else:
        miss_msg = "Taktik murahan dan tanpa bukti nyata! Kau tidak tahu apa-apa tentangku!"

    state["dealer_line"] = miss_msg
    return {
        "hit": False,
        "kicked_out": False,
        "message": miss_msg,
    }
