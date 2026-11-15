const SUIT_SVGS = {
  S: '<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2C9 6 4 9.5 4 14a4.5 4.5 0 0 0 6.5 4c-.2 1.5-.8 2.8-2 4h7c-1.2-1.2-1.8-2.5-2-4A4.5 4.5 0 0 0 20 14c0-4.5-5-8-8-12z"/></svg>',
  H: '<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 21s-7.5-4.7-9.5-9.5C.8 7.5 3.6 4 7.2 4c2 0 3.7 1 4.8 2.6C13.1 5 14.8 4 16.8 4c3.6 0 6.4 3.5 4.7 7.5C19.5 16.3 12 21 12 21z"/></svg>',
  D: '<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="12 2 21 12 12 22 3 12"/></svg>',
  C: '<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 3a4 4 0 0 0-3.4 6.1A4.2 4.2 0 0 0 4 13.3 4.2 4.2 0 0 0 8.2 17.5c1.1 0 2-.4 2.7-1-.2 1.7-.9 3.2-2.2 4.5h6.6c-1.3-1.3-2-2.8-2.2-4.5.7.6 1.6 1 2.7 1a4.2 4.2 0 0 0 4.2-4.2 4.2 4.2 0 0 0-4.6-4.2A4 4 0 0 0 12 3z"/></svg>',
};

const el = (id) => document.getElementById(id);

function renderCard(card) {
  if (!card) {
    return '<div class="card-tile card-slot" aria-hidden="true"></div>';
  }
  if (card.code === "??") {
    return '<div class="card-tile card-back" aria-label="Kartu tertutup">?</div>';
  }
  const isRed = card.suit === "H" || card.suit === "D";
  return `
    <div class="card-tile ${isRed ? "suit-red" : ""}" aria-label="Kartu ${card.rank} ${card.suit}">
      <span class="card-rank">${card.rank}</span>
      <span class="card-suit">${SUIT_SVGS[card.suit] || ""}</span>
    </div>
  `;
}

function renderTable(data) {
  el("stat-streak").textContent = `${data.win_streak} / 10`;
  el("stat-chips").textContent = `$${Number(data.chips).toLocaleString("en-US")}`;
  el("stat-composure").textContent = `${data.composure}%`;
  el("hands-count").textContent = data.hands_played;
  el("dealer-line").textContent = data.dealer_line;

  const portrait = el("dealer-portrait");
  portrait.className = `dealer-portrait mood-${data.dealer_mood || "smug"}`;

  const p = data.poker;
  const resultBanner = el("result-banner");

  if (!p) {
    el("street-badge").textContent = "READY";
    el("pot-amount").textContent = "$0";
    el("dealer-cards").innerHTML = renderCard({ code: "??" }) + renderCard({ code: "??" });
    el("player-cards").innerHTML = renderCard(null) + renderCard(null);
    el("board-cards").innerHTML = Array(5).fill(null).map(() => renderCard(null)).join("");
    el("dealer-hand-rank").textContent = "";
    el("player-hand-rank").textContent = "";
    resultBanner.classList.add("hidden");
    setPokerButtons(false);
  } else {
    el("street-badge").textContent = p.street;
    el("pot-amount").textContent = `$${p.pot}`;
    el("dealer-cards").innerHTML = p.dealer_cards.map(renderCard).join("");
    el("player-cards").innerHTML = p.player_cards.map(renderCard).join("");

    const boardSlots = [];
    for (let i = 0; i < 5; i += 1) {
      boardSlots.push(renderCard(p.board[i] || null));
    }
    el("board-cards").innerHTML = boardSlots.join("");
    el("dealer-hand-rank").textContent = p.dealer_hand_name || "";
    el("player-hand-rank").textContent = p.player_hand_name || "";

    if (p.finished) {
      const labels = {
        win: "YOU WIN THE HAND!",
        loss: "DEALER WINS — STREAK RESET",
        fold: "FOLDED — STREAK RESET",
        tie: "SPLIT POT (TIE)",
      };
      resultBanner.textContent = labels[p.outcome] || p.outcome;
      resultBanner.className = `result-banner ${p.outcome}`;
      setPokerButtons(false);
    } else {
      resultBanner.classList.add("hidden");
      setPokerButtons(true);
    }
  }

  if (data.flag) {
    showVictory(
      data.flag,
      data.won_by === "poker"
        ? "CARA ORANG GILA — 10 Kemenangan Beruntun di Meja Poker!"
        : "ALL-OUT BREAKDOWN — Mental Reynaldi Hancur Total!",
      data.dealer_line
    );
  }
}

function setPokerButtons(handActive) {
  el("btn-call").disabled = !handActive;
  el("btn-allin").disabled = !handActive;
  el("btn-fold").disabled = !handActive;
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  return res.json();
}

async function refreshTable() {
  const data = await fetchJson("/api/table/state");
  renderTable(data);
}

async function dealHand() {
  const data = await fetchJson("/api/poker/new", { method: "POST" });
  renderTable(data);
}

async function playAction(action) {
  const data = await fetchJson("/api/poker/action", {
    method: "POST",
    body: JSON.stringify({ action }),
  });
  renderTable(data);
}

function renderConfront(view) {
  el("confront-title").textContent = view.title;
  el("confront-composure").textContent = `${view.composure}%`;
  el("confront-meter-fill").style.width = `${view.composure}%`;
  el("confront-strikes").textContent = `${view.strikes} / ${view.max_strikes}`;
  el("confront-dealer-prompt").textContent = view.dealer_prompt;

  el("tactics-list").innerHTML = view.tactics
    .map(
      (t, idx) => `
      <label class="tactic-option">
        <input type="radio" name="tactic" value="${t.id}" ${idx === 0 ? "required" : ""}>
        <span><strong>[${t.id}]</strong> ${t.label}</span>
      </label>
    `
    )
    .join("");
}

async function openConfront() {
  el("confront-feedback").classList.add("hidden");
  el("evidence-input").value = "";
  const view = await fetchJson("/api/confront/state");
  renderConfront(view);
  el("modal-confront").classList.remove("hidden");
}

function showVictory(flag, reason, quote) {
  el("modal-confront").classList.add("hidden");
  el("flag-value").textContent = flag;
  el("victory-reason").textContent = reason;
  el("victory-quote").textContent = quote;
  el("modal-victory").classList.remove("hidden");
}

el("btn-deal").addEventListener("click", dealHand);
el("btn-call").addEventListener("click", () => playAction("check_call"));
el("btn-allin").addEventListener("click", () => playAction("allin"));
el("btn-fold").addEventListener("click", () => playAction("fold"));

el("btn-open-dossier").addEventListener("click", () => {
  el("modal-dossier").classList.remove("hidden");
});
el("btn-close-dossier").addEventListener("click", () => {
  el("modal-dossier").classList.add("hidden");
});

el("btn-open-confront").addEventListener("click", openConfront);
el("btn-close-confront").addEventListener("click", () => {
  el("modal-confront").classList.add("hidden");
});

el("btn-close-victory").addEventListener("click", () => {
  el("modal-victory").classList.add("hidden");
});

el("btn-copy-flag").addEventListener("click", async () => {
  const flag = el("flag-value").textContent;
  await navigator.clipboard.writeText(flag);
  el("btn-copy-flag").textContent = "COPIED!";
  setTimeout(() => {
    el("btn-copy-flag").textContent = "COPY FLAG";
  }, 1500);
});

el("confront-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const checked = document.querySelector('input[name="tactic"]:checked');
  const tactic = checked ? checked.value : "";
  const evidence = el("evidence-input").value;

  const res = await fetchJson("/api/confront/submit", {
    method: "POST",
    body: JSON.stringify({ tactic, evidence }),
  });

  if (res.table) {
    renderTable(res.table);
  }

  if (res.broken && res.flag) {
    showVictory(
      res.flag,
      "ALL-OUT BREAKDOWN — Mental Reynaldi Hancur Total!",
      res.message
    );
    return;
  }

  const fb = el("confront-feedback");
  fb.textContent = res.hit ? `WEAKNESS HIT! ${res.message}` : `MISS! ${res.message}`;
  fb.className = `confront-feedback ${res.hit ? "hit" : "miss"}`;

  if (res.kicked_out) {
    setTimeout(() => {
      el("modal-confront").classList.add("hidden");
    }, 1500);
    return;
  }

  el("evidence-input").value = "";
  renderConfront(res.confront);
});

refreshTable();
