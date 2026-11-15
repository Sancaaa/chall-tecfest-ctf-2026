/**
 * sequence.js: Shared challenge page logic and submit handling.
 */

document.addEventListener('DOMContentLoaded', () => {
  initSolveForm();
  initHints();
  updateCorruption();
});

let failedAttempts = {};

function getSeqId() {
  return document.body.getAttribute('data-sequence') || '';
}

function updateCorruption() {
  const body = document.body;
  const count = parseInt(body.getAttribute('data-completed') || '0', 10);
  const fraction = Math.min(count / 5, 1);
  document.documentElement.style.setProperty('--corruption', fraction);

  const madnessFill = document.querySelector('.madness-fill');
  if (madnessFill) {
    madnessFill.style.width = Math.round(fraction * 100) + '%';
  }
}

function initSolveForm() {
  const forms = document.querySelectorAll('.solution-form');
  forms.forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const seqId = form.getAttribute('data-seq-id') || getSeqId();
      const formData = new FormData(form);
      const data = {};
      formData.forEach((v, k) => data[k] = v);

      const feedback = document.querySelector('.feedback') || createFeedback(form);
      feedback.style.display = 'none';
      feedback.className = 'feedback';

      try {
        const resp = await fetch('/complete/' + seqId, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        const result = await resp.json();

        if (result.success) {
          feedback.className = 'feedback success';
          feedback.textContent = result.message || 'Potion digested. The Pathway shifts...';
          feedback.style.display = 'block';
          form.classList.add('gold-burst-success');

          const digestionFill = document.querySelector('.digestion-fill');
          if (digestionFill) {
            digestionFill.style.width = '100%';
          }

          setTimeout(() => {
            if (result.redirect) {
              window.location.href = result.redirect;
            } else {
              window.location.href = '/';
            }
          }, 2000);
        } else {
          feedback.className = 'feedback error';
          feedback.textContent = result.message || 'Losing control... The whispers grow louder.';
          feedback.style.display = 'block';
          form.classList.add('shake-error');
          form.classList.add('crimson-flash-error');
          setTimeout(() => {
            form.classList.remove('shake-error');
            form.classList.remove('crimson-flash-error');
          }, 600);

          failedAttempts[seqId] = (failedAttempts[seqId] || 0) + 1;
          if (failedAttempts[seqId] >= 3) {
            const hintBtn = document.querySelector('.hint-btn');
            if (hintBtn && hintBtn.style.display !== 'inline-block') {
              hintBtn.style.display = 'inline-block';
              hintBtn.style.opacity = '0';
              hintBtn.style.transition = 'opacity 0.5s';
              setTimeout(() => hintBtn.style.opacity = '', 50);
            }
          }
        }
      } catch (err) {
        feedback.className = 'feedback error';
        feedback.textContent = 'Connection lost to the Pathway. Try again.';
        feedback.style.display = 'block';
      }
    });
  });
}

function createFeedback(form) {
  const fb = document.createElement('div');
  fb.className = 'feedback';
  form.parentNode.insertBefore(fb, form.nextSibling);
  return fb;
}

function initHints() {
  const hintBtns = document.querySelectorAll('.hint-btn');
  hintBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const content = document.querySelector('.hint-content');
      if (content) {
        content.classList.toggle('visible');
        btn.textContent = content.classList.contains('visible') ? '[-] Hide Hint' : '[+] Reveal Hint';
      }
    });
  });
}

/**
 * Create spell (S7)
 */
async function createSpell(spellData) {
  try {
    const resp = await fetch('/s7/magician/api/spells/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spellData)
    });
    const result = await resp.json();
    return result;
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Fetch scroll from the archive (S3)
 */
async function fetchScroll(scrollName) {
  const responseEl = document.getElementById('scroll-content');
  if (responseEl) {
    responseEl.textContent = 'Loading...';
  }

  try {
    const resp = await fetch('/s3/scholar/view?scroll=' + encodeURIComponent(scrollName));
    const result = await resp.json();

    if (responseEl) {
      if (result.error) {
        responseEl.textContent = result.error;
      } else {
        responseEl.textContent = result.content;
      }
    }
    return result;
  } catch (err) {
    if (responseEl) {
      responseEl.textContent = 'Failed to load scroll.';
    }
  }
}

/**
 * Login attempt (S6)
 */
async function attemptLogin(username, password) {
  try {
    const resp = await fetch('/s6/faceless/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username, password: password })
    });
    const result = await resp.json();
    if (result.token) {
      document.getElementById('jwt-token').textContent = result.token;
    }
    return result;
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Access admin page with token (S6)
 */
async function accessAdmin(token) {
  try {
    const resp = await fetch('/s6/faceless/admin', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    const result = await resp.json();
    return result;
  } catch (err) {
    return { error: err.message };
  }
}
