// "Gemini calls per day" on the admin analytics page: a stacked column per day
// (succeeded at the bottom, failed on top) drawn as SVG, with a tooltip on
// hover and keyboard focus. Data comes from the json_script tag in the template.
(function () {
  const container = document.querySelector('[data-daily-chart]');
  const dataTag = document.getElementById('daily-data');
  const tooltip = document.querySelector('[data-chart-tooltip]');
  if (!container || !dataTag || !tooltip) return;

  const days = JSON.parse(dataTag.textContent);
  const SVG = 'http://www.w3.org/2000/svg';
  const MARGIN = { top: 8, right: 8, bottom: 24, left: 32 };
  const MAX_BAR = 24; // columns never fill their slot
  const GAP = 2; // surface gap between stacked segments
  const RADIUS = 4; // rounded data end, square at the baseline

  function el(name, attrs) {
    const node = document.createElementNS(SVG, name);
    Object.entries(attrs || {}).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }

  // Round the axis up to a clean number and pick 3-5 clean ticks.
  function niceTicks(max) {
    if (max <= 4) return [0, 1, 2, 3, 4].slice(0, Math.max(max, 1) + 1);
    const rough = max / 4;
    const power = Math.pow(10, Math.floor(Math.log10(rough)));
    const step = [1, 2, 5, 10].map((m) => m * power).find((s) => s >= rough);
    const ticks = [];
    for (let v = 0; v <= max + step - 1; v += step) ticks.push(v);
    return ticks;
  }

  // A bar whose top corners are rounded and bottom corners square.
  function topRoundedBar(x, y, width, height) {
    const r = Math.min(RADIUS, width / 2, height);
    return el('path', {
      d: `M${x},${y + height} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} ` +
         `Q${x + width},${y} ${x + width},${y + r} V${y + height} Z`,
    });
  }

  function formatDate(iso) {
    return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, {
      weekday: 'short', day: 'numeric', month: 'short',
    });
  }

  function showTooltip(day, anchor) {
    tooltip.replaceChildren();
    const date = document.createElement('div');
    date.className = 'chart-tooltip__date';
    date.textContent = formatDate(day.date);
    tooltip.appendChild(date);
    [['Succeeded', day.succeeded, 'var(--series-ok)'], ['Failed or refused', day.failed, 'var(--series-failed)']]
      .forEach(([label, value, color]) => {
        const row = document.createElement('div');
        row.className = 'chart-tooltip__row';
        const key = document.createElement('span');
        key.className = 'chart-tooltip__key';
        key.style.background = color;
        const strong = document.createElement('strong');
        strong.textContent = value;
        const name = document.createElement('span');
        name.textContent = label;
        row.append(key, strong, name);
        tooltip.appendChild(row);
      });
    tooltip.hidden = false;
    const box = anchor.getBoundingClientRect();
    const tip = tooltip.getBoundingClientRect();
    const left = Math.min(Math.max(8, box.left + box.width / 2 - tip.width / 2), window.innerWidth - tip.width - 8);
    const top = box.top - tip.height - 8 < 8 ? box.bottom + 8 : box.top - tip.height - 8;
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  }

  function hideTooltip() {
    tooltip.hidden = true;
  }

  function render() {
    const width = container.clientWidth;
    const height = container.clientHeight;
    const plotW = width - MARGIN.left - MARGIN.right;
    const plotH = height - MARGIN.top - MARGIN.bottom;
    const max = Math.max(...days.map((d) => d.succeeded + d.failed), 1);
    const ticks = niceTicks(max);
    const top = ticks[ticks.length - 1];
    const y = (value) => MARGIN.top + plotH - (value / top) * plotH;
    const slot = plotW / days.length;
    const barW = Math.max(2, Math.min(MAX_BAR, slot - GAP));

    const svg = el('svg', { width, height, viewBox: `0 0 ${width} ${height}` });

    ticks.forEach((tick) => {
      svg.appendChild(el('line', {
        class: tick === 0 ? 'baseline' : 'grid',
        x1: MARGIN.left, x2: width - MARGIN.right, y1: y(tick), y2: y(tick),
      }));
      const label = el('text', { class: 'tick', x: MARGIN.left - 6, y: y(tick) + 4, 'text-anchor': 'end' });
      label.textContent = tick;
      svg.appendChild(label);
    });

    // One date label per ~64px, plus the last day; skip any regular label that
    // would crowd the last one.
    const last = days.length - 1;
    const every = Math.max(1, Math.ceil(days.length / Math.max(2, Math.floor(plotW / 64))));
    days.forEach((day, i) => {
      const x = MARGIN.left + i * slot + slot / 2;
      if (i === last || (i % every === 0 && (last - i) * slot >= 56)) {
        const label = el('text', { class: 'tick', x, y: height - 6, 'text-anchor': 'middle' });
        label.textContent = new Date(day.date + 'T00:00:00')
          .toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
        svg.appendChild(label);
      }

      const group = el('g', { class: 'column' });
      const barX = x - barW / 2;
      const okH = y(0) - y(day.succeeded);
      const failedH = y(0) - y(day.failed);
      if (day.succeeded) {
        const ok = day.failed
          ? el('rect', { x: barX, y: y(day.succeeded), width: barW, height: okH })
          : topRoundedBar(barX, y(day.succeeded), barW, okH);
        ok.setAttribute('class', 'bar seg-ok');
        group.appendChild(ok);
      }
      if (day.failed) {
        // The gap is carved out of the top segment, so the column's total height stays true.
        const gap = day.succeeded ? GAP : 0;
        const segTop = y(day.succeeded + day.failed);
        const failed = topRoundedBar(barX, segTop, barW, Math.max(failedH - gap, 1));
        failed.setAttribute('class', 'bar seg-failed');
        group.appendChild(failed);
      }
      // The whole slot is the hover/focus target, not just the painted bar.
      const hit = el('rect', {
        class: 'hit', x: MARGIN.left + i * slot, y: MARGIN.top, width: slot, height: plotH, tabindex: 0,
        'aria-label': `${formatDate(day.date)}: ${day.succeeded} succeeded, ${day.failed} failed`,
      });
      hit.addEventListener('pointerenter', () => showTooltip(day, hit));
      hit.addEventListener('focus', () => showTooltip(day, hit));
      hit.addEventListener('pointerleave', hideTooltip);
      hit.addEventListener('blur', hideTooltip);
      group.appendChild(hit);
      svg.appendChild(group);
    });

    container.replaceChildren(svg);
  }

  render();
  new ResizeObserver(render).observe(container);
  window.addEventListener('scroll', hideTooltip, { passive: true });
})();
