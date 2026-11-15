/**
 * dashboard.js: Potion cabinet interactivity.
 */

document.addEventListener('DOMContentLoaded', () => {
  updateCorruption();
  initPotionHoverSounds();
});

/**
 * Update corruption vignette based on completed sequences.
 */
function updateCorruption() {
  const body = document.body;
  const count = parseInt(body.getAttribute('data-completed') || '0', 10);
  const fraction = Math.min(count / 5, 1);
  document.documentElement.style.setProperty('--corruption', fraction);

  const madnessFill = document.querySelector('.madness-fill');
  if (madnessFill) {
    const pct = Math.round(fraction * 100);
    madnessFill.style.width = pct + '%';
  }
}

/**
 * Subtle click feedback on potion bottles
 */
function initPotionHoverSounds() {
  const bottles = document.querySelectorAll('.potion-bottle:not(.locked)');
  bottles.forEach(bottle => {
    bottle.addEventListener('mouseenter', () => {
      bottle.style.filter = 'brightness(1.1)';
    });
    bottle.addEventListener('mouseleave', () => {
      bottle.style.filter = '';
    });
  });
}

/**
 * Confirm reset
 */
function confirmReset() {
  return confirm('Abandon your Pathway? All progress will be erased.');
}
