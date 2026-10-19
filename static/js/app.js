// Shared bits for every page.
(function () {
  // Banners slide down like iOS notifications. Good news leaves on its own;
  // problems stay until tapped, so nobody misses them.
  document.querySelectorAll('[data-banner]').forEach(function (banner, i) {
    function leave() {
      if (banner.classList.contains('is-leaving')) return;
      banner.classList.add('is-leaving');
      banner.addEventListener('animationend', function () { banner.remove(); }, { once: true });
    }
    banner.addEventListener('click', leave);
    if (!banner.classList.contains('banner--error')) setTimeout(leave, 4500 + i * 600);
  });

  // The phone's status bar takes the colour of whatever field is on screen.
  const meta = document.querySelector('meta[name="theme-color"]');
  function syncThemeColor() {
    const colour = getComputedStyle(document.body).getPropertyValue('--field').trim();
    if (meta && colour) meta.content = colour;
  }
  syncThemeColor();
  new MutationObserver(syncThemeColor).observe(document.body, { attributes: true, attributeFilter: ['class'] });
})();
