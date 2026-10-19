// Upload page: the viewfinder shows your photo as it "develops", and the
// shutter opens the camera/library when there's no photo yet.
(function () {
  const form = document.querySelector('[data-upload-form]');
  if (!form) return;

  const MAX_BYTES = 10 * 1024 * 1024;
  const input = form.querySelector('[data-upload-input]');
  const prompt = form.querySelector('[data-upload-prompt]');
  // The preview <img> only exists once there's a photo to show.
  const preview = document.createElement('img');
  preview.className = 'viewfinder__preview';
  preview.alt = 'your photo';
  preview.hidden = true;
  preview.setAttribute('data-upload-preview', '');
  prompt.before(preview);
  const hint = form.querySelector('[data-upload-hint]');
  const error = form.querySelector('[data-upload-error]');
  const shutter = form.querySelector('[data-shutter]');
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
    preview.classList.remove('is-developing');

    if (!file) {
      prompt.hidden = false;
      return;
    }
    if (file.size > MAX_BYTES) {
      showError('that photo is over 10 mb. try a smaller one.');
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
    void preview.offsetWidth;
    preview.classList.add('is-developing');
  });

  // Some browsers can't display HEIC. The server still can, so just skip the preview.
  preview.addEventListener('error', function () {
    preview.hidden = true;
    prompt.hidden = false;
  });

  // No photo yet? The shutter opens the camera instead of submitting.
  shutter.addEventListener('click', function (event) {
    if (!input.files.length) {
      event.preventDefault();
      input.click();
    }
  });

  form.addEventListener('submit', function (event) {
    if (!input.files.length) {
      event.preventDefault();
      showError('pick or snap a photo first.');
    }
  });
})();
