// Any form with a data-loading attribute shows the loading overlay while the
// server talks to Gemini (~10 s), and disables its buttons so it can't be sent twice.
//   <form method="post" data-loading="Interviewing your object…">
(function () {
  const overlay = document.querySelector('[data-loading-overlay]');
  const text = document.querySelector('[data-loading-text]');
  if (!overlay || !text) return;

  const FOLLOW_UPS = [
    'Asking about its childhood…',
    'Taking notes on its rivals…',
    'Gently bringing up the trauma…',
    'Asking what it really thinks of you…',
  ];
  let timer = null;

  // Listening on document means this runs after the form's own submit handlers,
  // so a handler that cancels the submit (e.g. "no photo chosen") is respected.
  document.addEventListener('submit', function (event) {
    const form = event.target;
    if (!form.hasAttribute('data-loading') || event.defaultPrevented) return;

    form.querySelectorAll('button, [type="submit"]').forEach(function (button) {
      button.disabled = true;
    });
    const lines = [form.dataset.loading || 'Interviewing your object…'].concat(FOLLOW_UPS);
    let line = 0;
    text.textContent = lines[0];
    overlay.hidden = false;
    timer = setInterval(function () {
      line = (line + 1) % lines.length;
      text.textContent = lines[line];
    }, 2500);
  });

  // The browser's Back button can restore the page exactly as it was left,
  // overlay and disabled buttons included. Reset them.
  window.addEventListener('pageshow', function (event) {
    if (!event.persisted) return;
    clearInterval(timer);
    overlay.hidden = true;
    document.querySelectorAll('form[data-loading] button').forEach(function (button) {
      button.disabled = false;
    });
  });
})();
