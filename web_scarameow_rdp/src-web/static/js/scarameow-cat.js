(() => {
  const pet = document.getElementById("scarameow-pet");
  const bubble = document.getElementById("scarameow-bubble");
  const loading = document.getElementById("scarameow-loading");

  if (!pet || !bubble) return;

  // ============================================================
  // ELEMENTS
  // ============================================================

  const usernameField = document.getElementById("username");
  const passwordField = document.getElementById("password");
  const loginForm = document.getElementById("loginForm");
  const statusEl = document.getElementById("status");
  const serverError = document.getElementById("serverError");
  const showPassword = document.getElementById("showPassword");
  const toggleText = document.getElementById("toggleText");

  // ============================================================
  // SPRITES
  // ============================================================

  const sprites = {
    idle: "/static/img/idle.png",
    idleAlt: "/static/img/idle-2.png",
    password: "/static/img/password.png",
    passwordLooking: "/static/img/password-looking.png",
    happy: "/static/img/pat.png",
    tap2x: "/static/img/tap-2x.png"
  };

  // ============================================================
  // STATE
  // ============================================================

  let loaded = 0;
  let currentSpriteName = "idle";
  let spriteTimer = null;
  let bubbleTimer = null;
  let clickTimer = null;

  let lastChange = 0;
  let isPasswordVisible = false;
  let isDragging = false;
  let hasMoved = false;

  let dragOffsetX = 0;
  let dragOffsetY = 0;

  let mouseX = window.innerWidth / 2;
  let mouseY = window.innerHeight / 2;

  let lastMouseMove = Date.now();
  let isMouseIdle = false;

  let hiddenAt = 0;
  let wasHidden = false;
  let blurAt = 0;

  let currentX = 0;
  let currentY = 0;
  let near = false;

  // ============================================================
  // MESSAGES
  // ============================================================

  const messages = {
    click: [
      "Hehe~",
      "Aww!",
      "Lagi! Lagi!",
      "Nyaa~!",
      "Klik lagi dong!"
    ],

    doubleClick: [
      "Waaah!",
      "Jangan diganggu terus~",
      "Hmph!",
      "HIISHHhh...!"
    ],

    password: [
      "Aku tutup mata ya~",
      "Nggak aku intip kok!",
      "Ssttt...",
      "Password rahasia?"
    ],

    passwordSee: [
      "Waaah! Aku lihat!",
      "Hehe, kelihatan~",
      "Sssst! Aku intip dikit!"
    ],

    idle: [
      "Meow~",
      "Hai!",
      "Klik aku!",
      "Nyaa~",
      "Kamu lagi apa?"
    ],

    near: [
      "Kamu dekat! Hihi~",
      "Hai kamu~",
      "Mau main?"
    ]
  };

  // ============================================================
  // BUBBLE
  // ============================================================

  function updateBubblePosition() {
    const rect = pet.getBoundingClientRect();

    const width = bubble.offsetWidth || 150;
    const height = bubble.offsetHeight || 40;

    let x = rect.left + 10;
    let y = rect.top - height - 20;

    const maxX = window.innerWidth - width - 10;

    x = Math.max(10, Math.min(maxX, x));

    if (y < 10) {
      y = rect.bottom + 20;
      bubble.classList.add("bubble-below");
    } else {
      bubble.classList.remove("bubble-below");
    }

    bubble.style.left = `${x}px`;
    bubble.style.top = `${y}px`;

    const arrowX = Math.max(
      15,
      Math.min(
        rect.left + 30 - x,
        width - 30
      )
    );

    bubble.style.setProperty("--arrow-x", `${arrowX}px`);
  }

  function showBubble(text, duration = 2000) {
    if (!text) return;

    bubble.textContent = text;

    updateBubblePosition();

    bubble.classList.add("show");

    clearTimeout(bubbleTimer);

    bubbleTimer = setTimeout(() => {
      bubble.classList.remove("show");
    }, duration);
  }

  // ============================================================
  // SPRITE
  // ============================================================

  function setSprite(name, force = false) {
    if (!sprites[name]) return;

    if (
      !force &&
      Date.now() - lastChange < 700
    ) {
      return;
    }

    if (currentSpriteName === name) {
      return;
    }

    currentSpriteName = name;
    lastChange = Date.now();

    pet.style.opacity = "0";

    clearTimeout(spriteTimer);

    spriteTimer = setTimeout(() => {
      pet.src = sprites[name];
      pet.style.opacity = "1";
    }, 80);
  }

  function expectedSprite() {
    if (
      passwordField &&
      passwordField.value.length > 0
    ) {
      return isPasswordVisible
        ? "passwordLooking"
        : "password";
    }

    return isMouseIdle
      ? "idleAlt"
      : "idle";
  }

  // ============================================================
  // PRELOAD SPRITES
  // ============================================================

  Object.values(sprites).forEach((src) => {
    const image = new Image();

    image.onload = image.onerror = () => {
      loaded++;

      if (
        loaded === Object.keys(sprites).length
      ) {
        pet.src = sprites.idle;
        pet.style.display = "block";
        pet.style.opacity = "1";

        if (loading) {
          loading.style.display = "none";
        }

        try {
          const savedPosition =
            localStorage.getItem("scarameowPos");

          if (savedPosition) {
            const position =
              JSON.parse(savedPosition);

            const x = Math.max(
              0,
              Math.min(
                window.innerWidth - pet.offsetWidth,
                position.x
              )
            );

            const y = Math.max(
              0,
              Math.min(
                window.innerHeight - pet.offsetHeight,
                position.y
              )
            );

            pet.style.left = `${x}px`;
            pet.style.top = `${y}px`;
            pet.style.bottom = "auto";
            pet.style.right = "auto";
          }
        } catch (error) {
          console.warn(
            "Gagal membaca posisi SCARAMEOW.",
            error
          );
        }

        updateBubblePosition();
      }
    };

    image.src = src;
  });

  // ============================================================
  // MOUSE TRACKING
  // ============================================================

  document.addEventListener("mousemove", (event) => {
    mouseX = event.clientX;
    mouseY = event.clientY;

    lastMouseMove = Date.now();

    if (isMouseIdle) {
      isMouseIdle = false;

      if (currentSpriteName === "idleAlt") {
        setSprite("idle", true);
      }
    }
  });

  // ============================================================
  // IDLE DETECTION
  // ============================================================

  setInterval(() => {
    const idleTime =
      Date.now() - lastMouseMove;

    if (
      passwordField &&
      passwordField.value.length
    ) {
      return;
    }

    if (
      idleTime >= 2000 &&
      !isMouseIdle
    ) {
      isMouseIdle = true;
      setSprite("idleAlt", true);
    }

    if (
      idleTime < 2000 &&
      isMouseIdle
    ) {
      isMouseIdle = false;
      setSprite("idle", true);
    }
  }, 200);

  // ============================================================
  // SPRITE WATCHER
  // ============================================================

  setInterval(() => {
    if (
      currentSpriteName === "happy" ||
      currentSpriteName === "tap2x" ||
      isMouseIdle
    ) {
      return;
    }

    const expected = expectedSprite();

    if (
      currentSpriteName !== expected
    ) {
      setSprite(expected, true);
    }
  }, 150);

  // ============================================================
  // USERNAME / PASSWORD INPUT
  // ============================================================

  if (
    usernameField &&
    passwordField
  ) {
    usernameField.addEventListener(
      "input",
      () => {
        if (!passwordField.value.length) {
          setSprite("idle", true);
        }
      }
    );

    passwordField.addEventListener(
      "input",
      () => {
        setSprite(
          passwordField.value.length
            ? (
                isPasswordVisible
                  ? "passwordLooking"
                  : "password"
              )
            : "idle",
          true
        );
      }
    );

    usernameField.addEventListener(
      "focus",
      () => {
        if (!passwordField.value.length) {
          setSprite("idle", true);
        }
      }
    );

    passwordField.addEventListener(
      "focus",
      () => {
        if (passwordField.value.length) {
          setSprite(
            isPasswordVisible
              ? "passwordLooking"
              : "password",
            true
          );
        } else {
          showBubble(
            messages.password[
              Math.floor(
                Math.random() *
                messages.password.length
              )
            ],
            2500
          );
        }
      }
    );
  }

  // ============================================================
  // PASSWORD TOGGLE
  // ============================================================

  if (
    showPassword &&
    passwordField
  ) {
    showPassword.addEventListener(
      "change",
      () => {
        isPasswordVisible =
          showPassword.checked;

        passwordField.type =
          isPasswordVisible
            ? "text"
            : "password";

        if (toggleText) {
          toggleText.textContent =
            isPasswordVisible
              ? "Sembunyikan Password"
              : "Lihat Password";
        }

        if (passwordField.value.length) {
          setSprite(
            isPasswordVisible
              ? "passwordLooking"
              : "password",
            true
          );

          if (isPasswordVisible) {
            showBubble(
              messages.passwordSee[
                Math.floor(
                  Math.random() *
                  messages.passwordSee.length
                )
              ],
              2000
            );
          }
        }
      }
    );
  }

  // ============================================================
  // PET CLICK
  // ============================================================

  pet.addEventListener(
    "click",
    () => {
      if (hasMoved) return;

      if (clickTimer) {
        clearTimeout(clickTimer);
        clickTimer = null;

        pet.classList.add("bounce");

        setSprite("tap2x", true);

        showBubble(
          messages.doubleClick[
            Math.floor(
              Math.random() *
              messages.doubleClick.length
            )
          ],
          1800
        );

        setTimeout(() => {
          pet.classList.remove("bounce");
          setSprite(
            expectedSprite(),
            true
          );
        }, 1500);

        return;
      }

      clickTimer = setTimeout(() => {
        clickTimer = null;

        pet.classList.add("bounce");

        setSprite("happy", true);

        showBubble(
          messages.click[
            Math.floor(
              Math.random() *
              messages.click.length
            )
          ],
          1500
        );

        setTimeout(() => {
          pet.classList.remove("bounce");

          setSprite(
            expectedSprite(),
            true
          );
        }, 1000);
      }, 250);
    }
  );

  // ============================================================
  // PET LOOKING AT MOUSE
  // ============================================================

  function lookAtMouse() {
    const rect =
      pet.getBoundingClientRect();

    const centerX =
      rect.left + rect.width / 2;

    const centerY =
      rect.top + rect.height / 2;

    const dx = Math.max(
      -8,
      Math.min(
        8,
        (mouseX - centerX) / 50
      )
    );

    const dy = Math.max(
      -8,
      Math.min(
        8,
        (mouseY - centerY) / 50
      )
    );

    currentX +=
      (dx - currentX) * 0.1;

    currentY +=
      (dy - currentY) * 0.1;

    pet.style.setProperty(
      "--tx",
      `${currentX}px`
    );

    pet.style.setProperty(
      "--ty",
      `${currentY}px`
    );

    updateBubblePosition();

    requestAnimationFrame(
      lookAtMouse
    );
  }

  lookAtMouse();

  // ============================================================
  // NEAR MOUSE
  // ============================================================

  setInterval(() => {
    const rect =
      pet.getBoundingClientRect();

    const distance = Math.hypot(
      mouseX -
        (rect.left + rect.width / 2),
      mouseY -
        (rect.top + rect.height / 2)
    );

    if (
      distance < 150 &&
      !near
    ) {
      near = true;

      showBubble(
        messages.near[
          Math.floor(
            Math.random() *
            messages.near.length
          )
        ],
        1800
      );
    }

    if (distance > 220) {
      near = false;
    }
  }, 400);

  // ============================================================
  // LOGIN
  // ============================================================

  if (
    loginForm &&
    usernameField &&
    passwordField
  ) {
    loginForm.addEventListener(
      "submit",
      (event) => {
        event.preventDefault();

        const username =
          usernameField.value.trim();

        const password =
          passwordField.value.trim();

        if (statusEl) {
          statusEl.className = "";
        }

        // ------------------------------------------------------
        // EMPTY FIELD
        // ------------------------------------------------------

        if (!username || !password) {
          if (statusEl) {
            statusEl.textContent =
              "Isi semua field dulu ya!";

            statusEl.classList.add(
              "error"
            );
          }

          setSprite(
            "tap2x",
            true
          );

          showBubble(
            "Isi dulu username dan passwordnya~",
            2500
          );

          setTimeout(() => {
            setSprite(
              expectedSprite(),
              true
            );
          }, 2500);

          return;
        }

        // ------------------------------------------------------
        // PASSWORD TOO SHORT
        // ------------------------------------------------------

        if (password.length < 6) {
          if (statusEl) {
            statusEl.textContent =
              "Password minimal 6 karakter!";

            statusEl.classList.add(
              "error"
            );
          }

          setSprite(
            "tap2x",
            true
          );

          showBubble(
            "Passwordnya kurang panjang~",
            2500
          );

          setTimeout(() => {
            setSprite(
              expectedSprite(),
              true
            );
          }, 2500);

          return;
        }

        // ------------------------------------------------------
        // SEND TO FLASK
        // ------------------------------------------------------

        if (statusEl) {
          statusEl.textContent =
            "Memproses...";

          statusEl.className =
            "processing";
        }

        pet.classList.add("bounce");

        setSprite(
          "password",
          true
        );

        showBubble(
          "Memeriksa kredensial...",
          1200
        );

        setTimeout(() => {
          loginForm.submit();
        }, 900);
      }
    );
  }

  // ============================================================
  // SERVER ERROR
  // ============================================================

  if (serverError) {
    const errorMessage =
      serverError.textContent.trim();

    if (
      errorMessage === "Password salah."
    ) {
      setSprite("tap2x", true);

      showBubble(
        "Password salah.",
        2500
      );
    } else if (
      errorMessage === "Siapa kamu?"
    ) {
      setSprite("tap2x", true);

      showBubble(
        "Siapa kamu?",
        2500
      );
    } else {
      setSprite("tap2x", true);

      showBubble(
        errorMessage,
        2500
      );
    }
  }

  // ============================================================
  // RANDOM IDLE MESSAGE
  // ============================================================

  setInterval(() => {
    if (
      !bubble.classList.contains("show") &&
      currentSpriteName === "idle"
    ) {
      showBubble(
        messages.idle[
          Math.floor(
            Math.random() *
            messages.idle.length
          )
        ],
        15000
      );
    }
  }, 15000);

  // ============================================================
  // TAB VISIBILITY
  // ============================================================

  document.addEventListener(
    "visibilitychange",
    () => {
      if (document.hidden) {
        hiddenAt = Date.now();
        wasHidden = true;

        showBubble(
          "Jangan lama-lama pergi~",
          4000
        );
      } else if (wasHidden) {
        wasHidden = false;

        showBubble(
          Date.now() - hiddenAt < 3000
            ? "Cepat banget~"
            : "Akhirnya kembali!",
          3500
        );
      }
    }
  );

  // ============================================================
  // WINDOW BLUR / FOCUS
  // ============================================================

  window.addEventListener(
    "blur",
    () => {
      blurAt = Date.now();
    }
  );

  window.addEventListener(
    "focus",
    () => {
      if (
        blurAt &&
        Date.now() - blurAt > 2000
      ) {
        showBubble(
          "Lagi ngapain diluar?~",
          3000
        );
      }

      blurAt = 0;
    }
  );

  // ============================================================
  // TAB TITLE
  // ============================================================

  const originalTitle =
    document.title;

  let titleTimer = null;

  document.addEventListener(
    "visibilitychange",
    () => {
      clearInterval(titleTimer);

      if (document.hidden) {
        let i = 0;

        titleTimer = setInterval(() => {
          document.title =
            i++ % 2
              ? "Aku tungguin ya~"
              : "Nyaa~ jangan pergi...";
        }, 1500);
      } else {
        document.title =
          originalTitle;
      }
    }
  );

  // ============================================================
  // DRAG & DROP
  // ============================================================

  pet.addEventListener(
    "pointerdown",
    (event) => {
      if (
        event.button !== 0 &&
        event.pointerType === "mouse"
      ) {
        return;
      }

      isDragging = true;
      hasMoved = false;

      const rect =
        pet.getBoundingClientRect();

      dragOffsetX =
        event.clientX - rect.left;

      dragOffsetY =
        event.clientY - rect.top;

      pet.style.animation = "none";
      pet.style.transition = "none";

      event.preventDefault();
    }
  );

  document.addEventListener(
    "pointermove",
    (event) => {
      if (!isDragging) return;

      if (
        !hasMoved &&
        Math.hypot(
          event.movementX,
          event.movementY
        ) > 5
      ) {
        hasMoved = true;

        if (clickTimer) {
          clearTimeout(clickTimer);
          clickTimer = null;
        }
      }

      if (!hasMoved) return;

      const x = Math.max(
        0,
        Math.min(
          window.innerWidth -
            pet.offsetWidth,
          event.clientX -
            dragOffsetX
        )
      );

      const y = Math.max(
        0,
        Math.min(
          window.innerHeight -
            pet.offsetHeight,
          event.clientY -
            dragOffsetY
        )
      );

      pet.style.left = `${x}px`;
      pet.style.top = `${y}px`;

      pet.style.bottom = "auto";
      pet.style.right = "auto";

      updateBubblePosition();
    }
  );

  document.addEventListener(
    "pointerup",
    () => {
      if (!isDragging) return;

      isDragging = false;

      pet.style.animation =
        "scarameow-breathe 3s ease-in-out infinite";

      pet.style.transition =
        "opacity .2s ease, filter .3s ease";

      if (hasMoved) {
        try {
          const rect =
            pet.getBoundingClientRect();

          localStorage.setItem(
            "scarameowPos",
            JSON.stringify({
              x: rect.left,
              y: rect.top
            })
          );
        } catch (error) {
          console.warn(
            "Gagal menyimpan posisi SCARAMEOW.",
            error
          );
        }
      }

      setTimeout(() => {
        hasMoved = false;
      }, 100);
    }
  );

  // ============================================================
  // WINDOW RESIZE
  // ============================================================

  window.addEventListener(
    "resize",
    () => {
      updateBubblePosition();

      const rect =
        pet.getBoundingClientRect();

      if (
        rect.left >
        window.innerWidth -
          pet.offsetWidth
      ) {
        pet.style.left =
          `${Math.max(
            0,
            window.innerWidth -
              pet.offsetWidth
          )}px`;
      }

      if (
        rect.top >
        window.innerHeight -
          pet.offsetHeight
      ) {
        pet.style.top =
          `${Math.max(
            0,
            window.innerHeight -
              pet.offsetHeight
          )}px`;
      }
    }
  );

  // ============================================================
  // INITIAL POSITION
  // ============================================================

  updateBubblePosition();
})();