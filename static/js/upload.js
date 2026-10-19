// Upload page: show a preview of the chosen photo, then a loading overlay
// while the server interviews the object. No framework, no build step.
(function () {
  const form = document.querySelector('[data-upload-form]');
  if (!form) return;

  const MAX_BYTES = 10 * 1024 * 1024;
  const LOADING_LINES = [
    'Interviewing your object…',
    'Asking about its childhood…',
    'Taking notes on its rivals…',
    'Gently bringing up the trauma…',
    'Asking what it really thinks of you…',
  ];

  const input = form.querySelector('[data-upload-input]');
  const preview = form.querySelector('[data-upload-preview]');
  const prompt = form.querySelector('[data-upload-prompt]');
  const hint = form.querySelector('[data-upload-hint]');
  const error = form.querySelector('[data-upload-error]');
  const submit = form.querySelector('[data-upload-submit]');
  const overlay = document.querySelector('[data-loading-overlay]');
  const loadingText = document.querySelector('[data-loading-text]');

  let previewUrl = null;
  let loadingTimer = null;

  function showError(message) {
    error.textContent = message;
    error.hidden = !message;
  }

  input.addEventListener('change', function () {
    const file = input.files[0];
    showError('');
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    preview.hidden = true;

    if (!file) {
      prompt.hidden = false;
      return;
    }
    if (file.size > MAX_BYTES) {
      showError('That photo is over 10 MB. Try a smaller one.');
      input.value = '';
      prompt.hidden = false;
      return;
    }

    hint.textContent = file.name;
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
  });

  preview.addEventListener('load', function () {
    preview.hidden = false;
    prompt.hidden = true;
  });

  // Some browsers can't display HEIC. The server still can, so just skip the preview.
  preview.addEventListener('error', function () {
    preview.hidden = true;
    prompt.hidden = false;
  });

  form.addEventListener('submit', function (event) {
    if (!input.files.length) {
      event.preventDefault();
      showError('Choose or take a photo first.');
      return;
    }
    // Block double submits: one photo, one interview.
    submit.disabled = true;
    overlay.hidden = false;
    let line = 0;
    loadingTimer = setInterval(function () {
      line = (line + 1) % LOADING_LINES.length;
      loadingText.textContent = LOADING_LINES[line];
    }, 2500);
  });

  // Coming back with the browser's Back button can restore the page as it was
  // left, overlay and all. Reset it.
  window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
      submit.disabled = false;
      overlay.hidden = true;
      clearInterval(loadingTimer);
      loadingText.textContent = LOADING_LINES[0];
    }
  });
})();
