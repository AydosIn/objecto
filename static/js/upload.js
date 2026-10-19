// Upload page: show a preview of the chosen photo before it is sent.
// The loading overlay on submit is handled by loading.js (data-loading on the form).
(function () {
  const form = document.querySelector('[data-upload-form]');
  if (!form) return;

  const MAX_BYTES = 10 * 1024 * 1024;

  const input = form.querySelector('[data-upload-input]');
  const preview = form.querySelector('[data-upload-preview]');
  const prompt = form.querySelector('[data-upload-prompt]');
  const hint = form.querySelector('[data-upload-hint]');
  const error = form.querySelector('[data-upload-error]');

  let previewUrl = null;

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
    }
  });
})();
