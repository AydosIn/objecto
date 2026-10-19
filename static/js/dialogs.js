// iOS-style sheets and alerts built on <dialog>.
//   <a href="/fallback/page/" data-open-dialog="delete-alert">  opens #delete-alert
//   <button type="button" data-close-dialog>                    closes its dialog
// Links keep their href, so without JavaScript they still lead to a normal page.
(function () {
  document.addEventListener('click', function (event) {
    const opener = event.target.closest('[data-open-dialog]');
    if (opener) {
      const dialog = document.getElementById(opener.dataset.openDialog);
      if (dialog && typeof dialog.showModal === 'function') {
        event.preventDefault();
        dialog.showModal();
      }
      return;
    }

    const closer = event.target.closest('[data-close-dialog]');
    if (closer) {
      closer.closest('dialog').close();
      return;
    }

    // Tapping the dimmed area outside a sheet or alert dismisses it, like iOS.
    if (event.target instanceof HTMLDialogElement) {
      const box = event.target.getBoundingClientRect();
      const outside =
        event.clientX < box.left || event.clientX > box.right ||
        event.clientY < box.top || event.clientY > box.bottom;
      if (outside) event.target.close();
    }
  });
})();
