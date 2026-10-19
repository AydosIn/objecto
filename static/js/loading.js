// The interview: while Gemini writes the story (~10 s), the screen cycles through
// the colour ramp with what's going on in the room. Any form with data-loading
// triggers it:   <form method="post" data-loading="ok it's talking">
(function () {
  const screen = document.querySelector('[data-interview]');
  if (!screen) return;
  const line = screen.querySelector('[data-interview-line]');
  let photo = null; // created when there's a photo to show

  const FIELDS = ['grape', 'pink', 'lime', 'orange', 'pool', 'butter', 'mint'];
  const LINES = [
    'asking about its childhood',
    'it has beef with someone',
    'it’s typing…',
    'taking notes on the trauma',
    'it has a lot to say about you',
    'almost. it’s getting emotional',
  ];
  let timer = null;

  function show(text, field) {
    screen.className = 'interview field--' + field;
    line.textContent = text;
    line.classList.remove('is-new');
    void line.offsetWidth; // replay the entrance
    line.classList.add('is-new');
  }

  // Listening on document runs after the form's own handlers, so a submit
  // they cancelled (e.g. "no photo yet") is respected.
  document.addEventListener('submit', function (event) {
    const form = event.target;
    if (!form.hasAttribute('data-loading') || event.defaultPrevented) return;

    form.querySelectorAll('button').forEach(function (button) { button.disabled = true; });
    // A form inside a sheet: close it, or it would sit above the interview.
    const dialog = form.closest('dialog');
    if (dialog) dialog.close();

    // Show the object being interviewed: the fresh upload, or the exhibit's photo.
    const source = document.querySelector('[data-upload-preview]:not([hidden])') ||
      document.querySelector('.print--hero img');
    if (source && source.src) {
      if (!photo) {
        photo = document.createElement('img');
        photo.className = 'interview__photo';
        photo.alt = '';
        screen.prepend(photo);
      }
      photo.src = source.src;
    }

    let step = 0;
    show(form.dataset.loading || LINES[0], FIELDS[0]);
    screen.hidden = false;
    timer = setInterval(function () {
      step += 1;
      show(LINES[(step - 1) % LINES.length], FIELDS[step % FIELDS.length]);
    }, 1700);
  });

  // Coming back with the Back button can restore the page mid-interview. Reset it.
  window.addEventListener('pageshow', function (event) {
    if (!event.persisted) return;
    clearInterval(timer);
    screen.hidden = true;
    document.querySelectorAll('form[data-loading] button').forEach(function (button) {
      button.disabled = false;
    });
  });
})();
