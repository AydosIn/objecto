// iOS-style sheets and alerts built on <dialog>.
//   <a href="/fallback/page/" data-open-dialog="delete-alert">  opens #delete-alert
//   <button type="button" data-close-dialog>                    closes its dialog
// Openers are real links, so without JavaScript (or <dialog>) they still lead to a page.
(function () {
  if (typeof HTMLDialogElement === 'undefined') return; // links do their normal thing

  // A sheet the server opened (?rename=1) becomes a proper modal once JS runs.
  document.querySelectorAll('dialog[open]').forEach(function (dialog) {
    dialog.close();
    dialog.showModal();
  });

  function isOutside(dialog, event) {
    const box = dialog.getBoundingClientRect();
    return event.clientX < box.left || event.clientX > box.right ||
      event.clientY < box.top || event.clientY > box.bottom;
  }

  // Only a tap that starts AND ends on the dimmed area closes the dialog, so
  // dragging out of a text field (selecting text) doesn't throw away the sheet.
  let downOnBackdrop = false;
  document.addEventListener('pointerdown', function (event) {
    downOnBackdrop = event.target instanceof HTMLDialogElement && isOutside(event.target, event);
  });

  document.addEventListener('click', function (event) {
    const opener = event.target.closest('[data-open-dialog]');
    if (opener) {
      const dialog = document.getElementById(opener.dataset.openDialog);
      if (dialog && typeof dialog.showModal === 'function') {
        event.preventDefault();
        if (!dialog.open) dialog.showModal();
      }
      return;
    }

    const closer = event.target.closest('[data-close-dialog]');
    if (closer) {
      event.preventDefault();
      closer.closest('dialog').close();
      return;
    }

    if (downOnBackdrop && event.target instanceof HTMLDialogElement && isOutside(event.target, event)) {
      event.target.close();
    }
    downOnBackdrop = false;
  });
})();
