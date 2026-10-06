"""The overview page's script: hand-written ES2020, no framework, no build step.

Its rules (`textContent` only, no randomness, clock or network, background click) are in the README.
"""

from typing import Final

APP_JS: Final[str] = r"""'use strict';
(function () {
  const data = JSON.parse(document.getElementById('overview-data').textContent);
  const detail = document.getElementById('detail');
  const search = document.getElementById('search');
  const byId = new Map(data.nodes.map((node) => [node.id, node]));

  /* The items an item sits in, nearest first; a parent cycle ends the walk. */
  const ancestors = (id) => {
    const seen = new Set([id]);
    const up = [];
    for (let at = byId.get(id).parent; at != null && !seen.has(at); at = byId.get(at).parent) {
      seen.add(at);
      up.push(at);
    }
    return up;
  };

  /* An item and every item nested in it. */
  const family = (id) => {
    const found = new Set([id]);
    for (const node of data.nodes) {
      if (ancestors(node.id).includes(id)) found.add(node.id);
    }
    return found;
  };

  const linkLabel = (link) => {
    const parts = [];
    if (link.via !== null) parts.push(link.via);
    if (link.count > 1) parts.push('x' + link.count);
    return parts.join(' ');
  };

  const elements = [
    ...data.nodes.map((node) => ({
      data: {
        id: node.id,
        label: node.label,
        installed: node.installed,
        ...(node.parent === null ? {} : { parent: node.parent }),
      },
    })),
    ...data.links.map((link, index) => ({
      data: {
        id: 'link' + index,
        source: link.a,
        target: link.b,
        kind: link.kind,
        label: linkLabel(link),
      },
    })),
  ];

  const cy = cytoscape({
    container: document.getElementById('cy'),
    elements: elements,
    minZoom: 0.05,
    maxZoom: 4,
    autounselectify: true,
    boxSelectionEnabled: false,
    style: [
      { selector: 'node', style: {
        'label': 'data(label)', 'font-size': 11, 'text-valign': 'center', 'text-halign': 'center',
        'shape': 'round-rectangle', 'width': 'label', 'height': 'label', 'padding': '7px',
        'background-color': '#dbe7f3', 'border-width': 1, 'border-color': '#4a6785',
        'color': '#1c2b39' } },
      { selector: ':parent', style: {
        'text-valign': 'top', 'background-color': '#f1f5f9', 'background-opacity': 0.7,
        'padding': '14px' } },
      { selector: 'node[!installed]', style: { 'border-style': 'dashed' } },
      { selector: 'edge', style: {
        'curve-style': 'bezier', 'width': 1.5, 'line-color': '#555', 'label': 'data(label)',
        'font-size': 10, 'text-background-color': '#ffffff', 'text-background-opacity': 0.9,
        'text-background-padding': '2px', 'color': '#1c2b39' } },
      { selector: 'edge[kind = "cable"]', style: { 'width': 5, 'line-color': '#333333' } },
      { selector: 'edge[kind = "mate"]', style: { 'line-style': 'dotted', 'width': 3 } },
      { selector: '.dim', style: { 'opacity': 0.15 } },
      { selector: 'node.hi', style: { 'border-color': '#d9480f', 'border-width': 3 } },
      { selector: 'edge.hi', style: { 'line-color': '#d9480f', 'z-index': 10 } },
    ],
  });

  /* The same layout every time, and no random number anywhere: each item is packed inside its
     parent in rows, in the order of the data, and the top level is packed the same way. The
     positions go to Cytoscape's built-in preset layout; a compound box wraps its children. */
  const GAP = 34;
  const PAD = 16;
  const HEAD = 18;
  const childrenOf = new Map();
  for (const node of data.nodes) {
    const key = node.parent === null ? '' : node.parent;
    if (!childrenOf.has(key)) childrenOf.set(key, []);
    childrenOf.get(key).push(node.id);
  }

  /* Rows of boxes, left to right, wrapped near a square: the size of the whole and each offset. */
  const pack = (boxes) => {
    const area = boxes.reduce((sum, box) => sum + (box.w + GAP) * (box.h + GAP), 0);
    const limit = Math.max(Math.sqrt(area) * 1.15, ...boxes.map((box) => box.w));
    const at = new Map();
    let x = 0;
    let y = 0;
    let rowHeight = 0;
    let width = 0;
    for (const box of boxes) {
      if (x > 0 && x + box.w > limit) {
        y += rowHeight + GAP;
        x = 0;
        rowHeight = 0;
      }
      at.set(box.id, { x: x, y: y });
      x += box.w + GAP;
      rowHeight = Math.max(rowHeight, box.h);
      width = Math.max(width, x - GAP);
    }
    return { w: width, h: y + rowHeight, at: at };
  };

  const sizes = new Map();
  const measure = (id) => {
    const inside = childrenOf.get(id);
    if (inside === undefined) {
      sizes.set(id, { w: 6.5 * byId.get(id).label.length + 24, h: 30, inner: null });
    } else {
      const inner = pack(inside.map((child) => ({ id: child, ...measure(child) })));
      sizes.set(id, { w: inner.w + 2 * PAD, h: inner.h + 2 * PAD + HEAD, inner: inner });
    }
    return sizes.get(id);
  };
  const place = (id, left, top) => {
    const size = sizes.get(id);
    if (size.inner === null) {
      cy.getElementById(id).position({ x: left + size.w / 2, y: top + size.h / 2 });
      return;
    }
    for (const [child, at] of size.inner.at) {
      place(child, left + PAD + at.x, top + PAD + HEAD + at.y);
    }
  };
  const roots = childrenOf.get('') ?? [];
  const whole = pack(roots.map((id) => ({ id: id, ...measure(id) })));
  for (const [id, at] of whole.at) place(id, at.x, at.y);
  cy.layout({ name: 'preset', fit: true, padding: 30 }).run();

  const text = (tag, content) => {
    const element = document.createElement(tag);
    element.textContent = content;
    return element;
  };

  const setDetail = (title, lines) => {
    detail.replaceChildren(text('h2', title), ...lines.map((line) => text('p', line)));
  };

  const signalText = (signal) =>
    signal.map((port) => byId.get(port.item).label + ' (' + port.marking + ')').join('  -  ');

  const signalLines = (touching) => {
    const lines = [touching.length + ' signal(s) through here'];
    for (const signal of touching.slice(0, 25)) lines.push(signalText(signal));
    if (touching.length > 25) lines.push('... and ' + (touching.length - 25) + ' more');
    return lines;
  };

  const clear = () => cy.elements().removeClass('dim hi');

  /* Light the items of the given signals, and the links between two items of one signal;
     dim the rest. `focus` (what was clicked) and the items it sits in always stay visible. */
  const show = (touching, focus) => {
    const sets = touching.map((signal) => new Set(signal.map((port) => port.item)));
    cy.elements().removeClass('hi').addClass('dim');
    for (const set of sets) {
      for (const id of set) {
        cy.getElementById(id).removeClass('dim').addClass('hi');
        for (const up of ancestors(id)) cy.getElementById(up).removeClass('dim');
      }
    }
    cy.edges().forEach((edge) => {
      const ends = [edge.data('source'), edge.data('target')];
      if (sets.some((set) => ends.every((end) => set.has(end)))) {
        edge.removeClass('dim').addClass('hi');
      }
    });
    focus.removeClass('dim');
    if (focus.isNode()) focus.ancestors().removeClass('dim');
  };

  const traceItem = (element) => {
    const id = element.id();
    const inside = family(id);
    const touching = data.signals.filter((signal) => signal.some((port) => inside.has(port.item)));
    const node = byId.get(id);
    show(touching, element);
    const facts = [];
    if (node.mpn !== null) facts.push('MPN ' + node.mpn);
    if (node.location !== null) facts.push('Location ' + node.location);
    if (!node.installed) facts.push('Not installed');
    setDetail(node.label, facts.concat(signalLines(touching)));
  };

  const traceLink = (element) => {
    const one = family(element.data('source'));
    const other = family(element.data('target'));
    const touching = data.signals.filter(
      (signal) =>
        signal.some((port) => one.has(port.item)) && signal.some((port) => other.has(port.item)),
    );
    show(touching, element);
    const title = element.data('label') === '' ? element.data('kind') : element.data('label');
    setDetail(
      title + ' (' + element.data('kind') + ')',
      [
        byId.get(element.data('source')).label + ' - ' + byId.get(element.data('target')).label,
      ].concat(signalLines(touching)),
    );
  };

  const reset = () => {
    clear();
    search.value = '';
    setDetail('Nothing selected', ['Click an item or a link to trace its signals.']);
    cy.fit(undefined, 30);
  };

  cy.on('tap', 'node', (event) => traceItem(event.target));
  cy.on('tap', 'edge', (event) => traceLink(event.target));
  /* No handler for a tap on the background: it must not clear a trace. */

  search.addEventListener('input', () => {
    const query = search.value.trim().toLowerCase();
    if (query === '') {
      reset();
      return;
    }
    const matches = data.nodes.filter((node) => node.label.toLowerCase().includes(query));
    const chosen = matches.find((node) => node.label.toLowerCase() === query) ?? matches[0];
    if (chosen === undefined) {
      clear();
      setDetail('No item matches', [search.value]);
      return;
    }
    const element = cy.getElementById(chosen.id);
    traceItem(element);
    cy.center(element);
  });

  document.getElementById('reset').addEventListener('click', reset);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') reset();
  });

  setDetail('Nothing selected', ['Click an item or a link to trace its signals.']);
})();
"""
