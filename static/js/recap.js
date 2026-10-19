// The recap: colour slides, one fact each.
//   Landing  [data-stage]: an example recap that plays by itself, like stories.
//   Exhibit  [data-recap]: the object's own recap, scrolled or tapped through.
(function () {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Headings marked data-split arrive word by word. Screen readers get the
  // whole heading from aria-label; the word spans are hidden from them.
  document.querySelectorAll('[data-split]').forEach(function (heading) {
    const text = heading.textContent.trim().replace(/\s+/g, ' ');
    heading.setAttribute('aria-label', text);
    heading.textContent = '';
    text.split(' ').forEach(function (word) {
      const span = document.createElement('span');
      span.className = 'word';
      span.setAttribute('aria-hidden', 'true');
      span.textContent = word;
      heading.append(span, ' ');
    });
  });

  // Within each slide, things arrive in reading order.
  document.querySelectorAll('[data-slide]').forEach(function (slide) {
    slide.querySelectorAll('[data-reveal], .word').forEach(function (el, i) {
      if (!el.style.getPropertyValue('--i')) el.style.setProperty('--i', Math.min(i, 12));
    });
  });

  function fieldOf(el) {
    return Array.from(el.classList).find(function (c) { return c.startsWith('field--'); });
  }

  // The page (and so the glass bar, progress and dock) takes the slide's colour.
  function setPageField(field) {
    Array.from(document.body.classList)
      .filter(function (c) { return c.startsWith('field--'); })
      .forEach(function (c) { document.body.classList.remove(c); });
    document.body.classList.add(field);
  }

  // "refilled 1,400 times": numbers count up when their slide lands.
  function countUp(slide) {
    slide.querySelectorAll('[data-count]').forEach(function (el) {
      const target = Number(el.dataset.count);
      if (reduce || !target) return;
      const started = performance.now();
      function frame(now) {
        const t = Math.min(1, (now - started) / 1100);
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = Math.round(target * eased).toLocaleString('en-US');
        if (t < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    });
  }

  function buildProgress(nav, slides, pick) {
    slides.forEach(function (_, i) {
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('aria-label', 'slide ' + (i + 1) + ' of ' + slides.length);
      button.addEventListener('click', function (event) {
        event.stopPropagation();
        pick(i);
      });
      nav.append(button);
    });
    return Array.from(nav.children);
  }

  function markProgress(bars, current) {
    bars.forEach(function (bar, i) {
      bar.classList.toggle('is-done', i < current);
      bar.classList.toggle('is-current', i === current);
      if (i === current) bar.setAttribute('aria-current', 'step');
      else bar.removeAttribute('aria-current');
    });
  }

  // ------------------------------------------------------------ Landing: autoplay
  const stage = document.querySelector('[data-stage]');
  if (stage) {
    const SLIDE_MS = 4600;
    const slides = Array.from(stage.querySelectorAll('[data-slide]'));
    const pauseButton = stage.querySelector('[data-stage-pause]');
    let current = -1;
    let paused = false;
    let userPaused = reduce; // no autoplay when motion is reduced
    let timer = null;
    let remaining = SLIDE_MS;
    let startedAt = 0;
    let wipe = 0; // which wipe is the latest, so a fast tap doesn't recolour late
    stage.style.setProperty('--slide-ms', SLIDE_MS + 'ms');

    const bars = buildProgress(stage.querySelector('[data-progress]'), slides, function (i) { go(i); });

    function schedule() {
      clearTimeout(timer);
      if (paused || userPaused) return;
      startedAt = performance.now();
      timer = setTimeout(function () { go(current + 1); }, remaining);
    }

    function pause() {
      if (paused) return;
      paused = true;
      clearTimeout(timer);
      remaining -= performance.now() - startedAt;
      stage.style.setProperty('--play', 'paused');
    }

    function resume() {
      if (!paused || userPaused) return;
      paused = false;
      stage.style.setProperty('--play', 'running');
      schedule();
    }

    function go(next, origin) {
      next = (next + slides.length) % slides.length;
      if (next === current) return;
      const previous = slides[current];
      const slide = slides[next];

      // The leaving slide keeps its content while the new colour wipes over it;
      // only the incoming slide replays its entrance.
      slides.forEach(function (s) {
        if (s !== previous) s.classList.remove('is-current', 'is-leaving', 'is-seen');
      });
      if (previous) previous.classList.remove('is-current');
      slide.classList.remove('is-seen');
      slide.classList.add('is-current');
      void slide.offsetWidth; // restart the entrance
      slide.classList.add('is-seen');

      // A colour wipe from wherever you tapped. The bar, progress and dock take
      // the new colour as the circle reaches them, not before.
      const thisWipe = ++wipe;
      if (previous && !reduce && slide.animate) {
        previous.classList.add('is-leaving');
        previous.classList.add('is-seen');
        const at = origin || '85% 75%';
        slide.animate(
          [{ clipPath: 'circle(0% at ' + at + ')' }, { clipPath: 'circle(150% at ' + at + ')' }],
          { duration: 700, easing: 'cubic-bezier(0.16, 1, 0.3, 1)' }
        ).finished.then(function () { previous.classList.remove('is-leaving'); });
        setTimeout(function () {
          if (thisWipe === wipe) setPageField(fieldOf(slide));
        }, 380);
      } else {
        setPageField(fieldOf(slide));
      }
      countUp(slide);
      current = next;
      markProgress(bars, current);
      const bar = bars[current];
      bar.classList.remove('is-current');
      void bar.offsetWidth; // restart the fill
      bar.classList.add('is-current');
      remaining = SLIDE_MS;
      if (!paused) stage.style.setProperty('--play', userPaused ? 'paused' : 'running');
      schedule();
    }

    function setUserPaused(value) {
      userPaused = value;
      pauseButton.setAttribute('aria-label', value ? 'play' : 'pause');
      pauseButton.querySelector('use').setAttribute('href', value ? '#i-play' : '#i-pause');
      stage.style.setProperty('--play', value ? 'paused' : 'running');
      if (value) { clearTimeout(timer); remaining = SLIDE_MS; } else { paused = false; schedule(); }
    }

    pauseButton.addEventListener('click', function (event) {
      event.stopPropagation();
      setUserPaused(!userPaused);
    });

    // Tap the right side for next, the left side for back, swipe sideways,
    // or hold to pause.
    let holdTimer = null;
    let held = false;
    let downX = 0;
    let downY = 0;
    stage.addEventListener('pointerdown', function (event) {
      if (event.target.closest('a, button')) return;
      held = false;
      downX = event.clientX;
      downY = event.clientY;
      holdTimer = setTimeout(function () { held = true; pause(); }, 220);
    });
    stage.addEventListener('pointercancel', function () { clearTimeout(holdTimer); resume(); });
    stage.addEventListener('pointerup', function (event) {
      clearTimeout(holdTimer);
      if (event.target.closest('a, button')) return;
      const dx = event.clientX - downX;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(event.clientY - downY)) {
        held = false;
        resume();
        go(dx < 0 ? current + 1 : current - 1);
        return;
      }
      if (held) { held = false; resume(); return; }
      const box = stage.getBoundingClientRect();
      const x = event.clientX - box.left;
      const y = event.clientY - box.top;
      go(x < box.width * 0.3 ? current - 1 : current + 1, x + 'px ' + y + 'px');
    });

    // Stop when nobody is watching
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) pause(); else resume();
    });
    // Scrolled down past the example: pause it, and let the page take the
    // colour of what's on screen instead of the last slide's.
    const below = stage.nextElementSibling;
    new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) {
        if (current >= 0) setPageField(fieldOf(slides[current]));
        resume();
      } else {
        pause();
        if (below && fieldOf(below)) setPageField(fieldOf(below));
      }
    }, { threshold: 0.4 }).observe(stage);

    if (reduce) setUserPaused(true);
    go(0);
  }

  // ------------------------------------------------------------ Exhibit: scroll or tap through
  const recap = document.querySelector('[data-recap]');
  if (recap) {
    const slides = Array.from(recap.querySelectorAll('[data-slide]'));
    function show(i) {
      slides[i].scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    }
    const bars = buildProgress(recap.querySelector('[data-progress]'), slides, show);

    // Whichever slide crosses the middle of the screen is the current one.
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-seen');
        markProgress(bars, slides.indexOf(entry.target));
        setPageField(fieldOf(entry.target));
      });
    }, { rootMargin: '-45% 0px -45% 0px' });
    slides.forEach(function (slide) { observer.observe(slide); });

    // Share the end card where the phone can share (the page itself is private,
    // so it shares the words, not a link).
    const share = recap.querySelector('[data-share]');
    if (share && navigator.share) {
      share.hidden = false;
      share.addEventListener('click', function () {
        navigator.share({ title: 'object biographies', text: share.dataset.shareText }).catch(function () {});
      });
    }

    // Tapping a slide (not a control, not while selecting text) moves to the next one.
    recap.addEventListener('click', function (event) {
      if (event.target.closest('a, button, input, textarea, label, .card, .placard')) return;
      if (String(getSelection())) return;
      const i = slides.indexOf(event.target.closest('[data-slide]'));
      if (i >= 0 && i < slides.length - 1) show(i + 1);
    });
  }
})();
