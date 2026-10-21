// Sending an exhibit: copy its link, or hand the link or the PDF to the phone's own
// share sheet (telegram, messages, whatsapp, whatever is installed).
//   <div data-share data-share-url data-share-text data-pdf-url data-pdf-name>
// The telegram, messages and download rows are plain links and work without this.
(function () {
  function noop() {}

  document.querySelectorAll('[data-share]').forEach(function (card) {
    const url = card.dataset.shareUrl;
    const text = card.dataset.shareText;

    // Copy the link. Where the clipboard is off limits, the link is selected instead,
    // so it can be copied by hand.
    const copy = card.querySelector('[data-copy]');
    if (copy) {
      const field = card.querySelector('input');
      const status = copy.querySelector('[data-copy-status]');
      copy.addEventListener('click', function () {
        field.select();
        if (!navigator.clipboard) return;
        navigator.clipboard.writeText(url).then(function () {
          status.textContent = 'copied';
          setTimeout(function () { status.textContent = ''; }, 2000);
        }, noop);
      });
    }

    const link = card.querySelector('[data-share-link]');
    if (link && navigator.share) {
      link.hidden = false;
      link.addEventListener('click', function () {
        navigator.share({ title: 'object biographies', text: text, url: url }).catch(noop);
      });
    }

    // The PDF as a file. iPhones only open the share sheet straight from a tap, not after
    // waiting for a download, so the file is fetched as soon as its row comes into view.
    const sendPdf = card.querySelector('[data-share-pdf]');
    const probe = new File([''], 'probe.pdf', { type: 'application/pdf' });
    if (!sendPdf || !navigator.canShare || !navigator.canShare({ files: [probe] })) return;

    const status = sendPdf.querySelector('[data-pdf-status]');
    let file = null;
    let fetching = false;
    sendPdf.hidden = false;
    sendPdf.disabled = true;
    status.textContent = 'one sec';

    function fetchPdf() {
      if (file || fetching) return;
      fetching = true;
      fetch(card.dataset.pdfUrl, { credentials: 'same-origin' })
        .then(function (response) {
          if (!response.ok) throw new Error(response.status);
          return response.blob();
        })
        .then(function (blob) {
          file = new File([blob], card.dataset.pdfName, { type: 'application/pdf' });
          sendPdf.disabled = false;
          status.textContent = '';
        })
        .catch(function () {
          // The download row still works.
          sendPdf.hidden = true;
        });
    }

    new IntersectionObserver(function (entries, observer) {
      if (entries.some(function (entry) { return entry.isIntersecting; })) {
        observer.disconnect();
        fetchPdf();
      }
    }).observe(sendPdf);

    sendPdf.addEventListener('click', function () {
      if (file) navigator.share({ files: [file], title: text }).catch(noop);
    });
  });
})();
