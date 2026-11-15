from collections import Counter
import itertools
import secrets

_RNG = secrets.SystemRandom()

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUITS = ["S", "H", "D", "C"]
RANK_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}

HAND_NAMES = {
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House",
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind",
    2: "Two Pair",
    1: "One Pair",
    0: "High Card",
}


def build_deck() -> list[str]:
    deck = [f"{r}{s}" for r in RANKS for s in SUITS]
    _RNG.shuffle(deck)
    return deck


def _eval_5(cards: tuple[str, ...]) -> tuple:
    vals = sorted((RANK_VALUE[c[0]] for c in cards), reverse=True)
    suits = [c[1] for c in cards]
    is_flush = len(set(suits)) == 1

    unique_vals = sorted(set(vals), reverse=True)
    is_straight = False
    straight_high = 0
    if len(unique_vals) == 5:
        if unique_vals[0] - unique_vals[4] == 4:
            is_straight = True
            straight_high = unique_vals[0]
        elif unique_vals == [14, 5, 4, 3, 2]:
            is_straight = True
            straight_high = 5

    if is_straight and is_flush:
        return (8, straight_high)

    counts = sorted(
        ((cnt, val) for val, cnt in Counter(vals).items()),
        key=lambda x: (x[0], x[1]),
        reverse=True,
    )
    pattern = [c for c, _ in counts]
    ordered_vals = [v for _, v in counts]

    if pattern == [4, 1]:
        return (7, ordered_vals[0], ordered_vals[1])
    if pattern == [3, 2]:
        return (6, ordered_vals[0], ordered_vals[1])
    if is_flush:
        return (5, *vals)
    if is_straight:
        return (4, straight_high)
    if pattern == [3, 1, 1]:
        return (3, ordered_vals[0], ordered_vals[1], ordered_vals[2])
    if pattern == [2, 2, 1]:
        return (2, ordered_vals[0], ordered_vals[1], ordered_vals[2])
    if pattern == [2, 1, 1, 1]:
        return (1, ordered_vals[0], ordered_vals[1], ordered_vals[2], ordered_vals[3])
    return (0, *vals)


def best_hand(cards: list[str]) -> tuple[tuple, str]:
    best = max(_eval_5(combo) for combo in itertools.combinations(cards, 5))
    cat = best[0]
    name = "Royal Flush" if cat == 8 and best[1] == 14 else HAND_NAMES[cat]
    return best, name


def format_card(code: str) -> dict:
    rank = "10" if code[0] == "T" else code[0]
    return {"code": code, "rank": rank, "suit": code[1]}


def _streak_line(streak: int) -> str:
    if streak == 0:
        return (
            "Haha! Nol lagi. Sudah kubilang, orang lemah tidak pantas berdiri "
            "di hadapan The Velvet King."
        )
    if streak >= 10:
        return (
            "Se... sepuluh kali berturut-turut?! Probabilitasnya mustahil... "
            "Matamu... kau benar-benar gila! Ambil hadiahmu dan keluar dari "
            "ruanganku sebelum aku kehilangan akal!"
        )
    if streak >= 5:
        return (
            f"Tch... {streak} kali beruntun. Jangan terlalu percaya diri. "
            "Satu kartu river yang salah, dan usahamu lenyap jadi debu."
        )
    return (
        f"Keberuntungan pemula ({streak}/10). Meja ini tidak butuh orang yang "
        "cuma mengandalkan doa."
    )


def start_hand(state: dict) -> dict:
    # Abandoning an unfinished hand resets streak to prevent fold-scumming via /new.
    abandoned = False
    if state.get("poker") and not state["poker"].get("finished"):
        state["win_streak"] = 0
        abandoned = True

    rebuy = False
    if state["chips"] <= 0:
        state["chips"] = 1000
        rebuy = True

    ante = min(100, state["chips"])
    state["chips"] -= ante
    deck = build_deck()

    state["poker"] = {
        "player_cards": deck[0:2],
        "dealer_cards": deck[2:4],
        "board": deck[4:9],
        "revealed_count": 0,
        "street": "PREFLOP",
        "pot": ante * 2,
        "finished": False,
        "outcome": None,
        "player_hand_name": None,
        "dealer_hand_name": None,
    }

    if rebuy:
        state["dealer_line"] = (
            "Chips habis? Kasino berbaik hati memberimu pinjaman darurat $1,000. "
            "Ayo lanjut, jangan bilang kau sudah gemetar."
        )
    elif abandoned:
        state["dealer_line"] = (
            "Kabur di tengah ronde? Itu tetap dihitung menyerah. Streak-mu "
            "kembali ke nol!"
        )
    else:
        state["dealer_line"] = "Kartu sudah dibagikan. Tunjukkan nyalimu: Call, All-In, atau Fold?"

    return {"rebuy": rebuy, "abandoned": abandoned}


def _resolve_showdown(state: dict, flag_value: str) -> str | None:
    poker = state["poker"]
    poker["revealed_count"] = 5
    poker["street"] = "SHOWDOWN"
    poker["finished"] = True
    state["hands_played"] += 1

    p_score, p_name = best_hand(poker["player_cards"] + poker["board"])
    d_score, d_name = best_hand(poker["dealer_cards"] + poker["board"])
    poker["player_hand_name"] = p_name
    poker["dealer_hand_name"] = d_name

    if p_score > d_score:
        poker["outcome"] = "win"
        state["chips"] += poker["pot"]
        state["win_streak"] += 1
    elif p_score < d_score:
        poker["outcome"] = "loss"
        state["win_streak"] = 0
    else:
        poker["outcome"] = "tie"
        state["chips"] += poker["pot"] // 2

    state["last_result"] = {
        "outcome": poker["outcome"],
        "player_hand": p_name,
        "dealer_hand": d_name,
        "pot": poker["pot"],
    }

    if poker["outcome"] == "tie":
        state["dealer_line"] = (
            f"Seri ({p_name}). Pot dibagi rata, dan streak-mu tertahan di "
            f"{state['win_streak']}/10."
        )
    else:
        state["dealer_line"] = _streak_line(state["win_streak"])

    if state["win_streak"] >= 10:
        state["won_by"] = "poker"
        state["dealer_mood"] = "broken"
        return flag_value
    return None


def apply_action(state: dict, action: str, flag_value: str) -> tuple[dict, str | None]:
    poker = state.get("poker")
    if not poker or poker.get("finished"):
        return {"error": "Belum ada ronde aktif. Tekan DEAL HAND untuk mulai."}, None

    if action == "fold":
        poker["finished"] = True
        poker["outcome"] = "fold"
        poker["street"] = "FOLDED"
        state["win_streak"] = 0
        state["hands_played"] += 1
        state["last_result"] = {
            "outcome": "fold",
            "player_hand": "Folded",
            "dealer_hand": "Hidden",
            "pot": poker["pot"],
        }
        state["dealer_line"] = _streak_line(0)
        return {"ok": True}, None

    if action == "allin":
        extra = state["chips"]
        state["chips"] = 0
        poker["pot"] += extra * 2
        flag = _resolve_showdown(state, flag_value)
        return {"ok": True}, flag

    if action == "check_call":
        bet = min(100, state["chips"])
        state["chips"] -= bet
        poker["pot"] += bet * 2

        if poker["street"] == "PREFLOP":
            poker["revealed_count"] = 3
            poker["street"] = "FLOP"
            state["dealer_line"] = "Flop terbuka. Masih berani lanjut, atau mau All-In?"
            return {"ok": True}, None
        if poker["street"] == "FLOP":
            poker["revealed_count"] = 4
            poker["street"] = "TURN"
            state["dealer_line"] = "Turn mendarat. Detak jantungmu mulai terdengar jelas."
            return {"ok": True}, None
        if poker["street"] == "TURN":
            flag = _resolve_showdown(state, flag_value)
            return {"ok": True}, flag

    return {"error": "Aksi poker tidak valid."}, None


def public_poker_view(state: dict) -> dict | None:
    poker = state.get("poker")
    if not poker:
        return None
    revealed = poker["board"][: poker["revealed_count"]]
    show_dealer = poker["finished"] and poker["outcome"] != "fold"
    return {
        "street": poker["street"],
        "pot": poker["pot"],
        "finished": poker["finished"],
        "outcome": poker["outcome"],
        "player_cards": [format_card(c) for c in poker["player_cards"]],
        "dealer_cards": (
            [format_card(c) for c in poker["dealer_cards"]]
            if show_dealer
            else [{"code": "??", "rank": "?", "suit": "?"} for _ in range(2)]
        ),
        "board": [format_card(c) for c in revealed],
        "player_hand_name": poker["player_hand_name"],
        "dealer_hand_name": poker["dealer_hand_name"],
    }
