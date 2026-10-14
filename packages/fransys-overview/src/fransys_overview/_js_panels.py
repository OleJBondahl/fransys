"""Page script, part 3: the panels around the drawing (O1, O5, O10-O14).

Every text comes from the data with `textContent`; a panel only filters or lists what it holds.
"""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_PANELS: Final[str] = r"""
const el = (tag, content = '', attrs = {}) => {
  const node = document.createElement(tag);
  node.textContent = content;
  for (const [name, value] of Object.entries(attrs)) node.setAttribute(name, value);
  return node;
};
const button = (content, onclick, attrs = {}) => {
  const node = el('button', content, { type: 'button', ...attrs });
  node.addEventListener('click', onclick);
  return node;
};
let commit = () => {};

const drawCrumbs = () => {
  const list = trail();
  const kids = [];
  list.forEach((crumb, n) => {
    if (n > 0) kids.push(document.createTextNode(' / '));
    if (n === list.length - 1) kids.push(el('span', crumb[0], { class: 'here' }));
    else kids.push(button(crumb[0], () => { go(crumb[1], crumb[2]); commit(true); }));
  });
  $('crumbs').replaceChildren(...kids);
  $('up').disabled = parentLevel() === null;
};

const drawPickers = () => {
  const split = $('split');
  split.replaceChildren(...SPLITS.map(([id, name]) => el('option', name, { value: id })));
  split.value = state.split;
  const mode = $('mode');
  mode.replaceChildren(...modesOf(state.unit, state.level).map((m) => el('option', MODE_NAME[m], { value: m })));
  mode.value = state.mode;
  mode.disabled = mode.options.length < 2;
};

/* The boxes of the level shown that sit in each class of the chosen split. */
const countClasses = (view) => {
  const counts = new Map();
  for (const box of view.boxes) {
    const cls = box.cls[SPLIT_AT[state.split]];
    counts.set(cls, (counts.get(cls) ?? 0) + 1);
  }
  return counts;
};

const drawLegend = (view) => {
  if (state.split === 'none') {
    $('legend').replaceChildren(el('span',
      'Lines: wire thin, cable thick, mate dotted. Hollow box: a stub. Dashed: by others.'));
    return;
  }
  const counts = countClasses(view);
  const note = el('span', 'Hollow box: a stub. Dashed: by others.');
  const items = [...counts.keys()].filter((c) => c !== null)
    .sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
  $('legend').replaceChildren(note, ...items.map((cls) => {
    const swatch = el('i');
    swatch.style.color = hueOf(state.split, cls);
    const key = classKey(cls);
    const node = button('', () => {
      if (state.hidden.has(key)) state.hidden.delete(key); else state.hidden.add(key);
      commit(false);
    }, { 'aria-pressed': String(!state.hidden.has(key)), class: state.hidden.has(key) ? 'off' : '' });
    node.append(swatch, document.createTextNode(cls + ' (' + counts.get(cls) + ')'));
    return node;
  }));
};

const drawChips = () => {
  const chips = [...state.hidden].map((key) => {
    const chip = el('span', key.replace(':', ': '), { class: 'chip' });
    chip.append(button('x', () => { state.hidden.delete(key); commit(false); }, { 'aria-label': 'Show ' + key }));
    return chip;
  });
  $('chips').replaceChildren(...chips);
};

/* The things the level can open: a strip, or a fold listed in the panel. One at a time (O5). */
const drawOpens = () => {
  const here = [...views.values()].filter((v) => v.unit === state.unit && sameRef(v.level, state.level)
    && v.mode === state.mode && v.open !== null).map((v) => v.open);
  const folds = foldBoxes().map(openOf).filter((open) => !here.some((o) => sameRef(o, open)));
  const kids = [...here, ...folds].map((open) => button((sameRef(open, state.open) ? 'Close ' : 'Open ') + labelOf(open), () => {
    state.open = sameRef(open, state.open) ? null : open;
    state.sel = null;
    commit(false);
  }));
  $('opens').replaceChildren(...kids);
};

const facts = (item) => {
  const out = ['Kind: ' + item.kind];
  if (item.unit !== null) out.push('Unit: ' + data.units[item.unit]);
  if (item.location !== null) out.push('Location: ' + item.location);
  if (item.group !== null) out.push('Function group: ' + item.group);
  if (item.mpn !== null) out.push('Part: ' + item.mpn);
  if (!item.installed) out.push('Not installed');
  return out;
};

const signalsOf = (index) => {
  const found = data.signals.filter((s) => s.some((p) => p[0] === index));
  const lines = found.length === 0 ? [] : [found.length + ' signal(s) through here'];
  for (const s of found.slice(0, 12)) {
    const shown = s.slice(0, 6).map((p) => data.items[p[0]].label + ' (' + p[1] + ')').join('  -  ');
    lines.push(s.length > 6 ? shown + '  ... ' + (s.length - 6) + ' more' : shown);
  }
  return lines;
};

/* The drawing pages of an item link to the PDF's named destinations (O21); the data holds the links. */
const pageLinks = (index) => {
  const pages = index === null ? [] : data.items[index].pages;
  if (pages.length === 0) return [];
  const links = pages.map(([href, text]) => el('a', text, { href, class: 'page' }));
  const row = el('p', 'Drawn on: ');
  links.forEach((a, n) => { if (n > 0) row.append(document.createTextNode(', ')); row.append(a); });
  return [row];
};
const detail = (title, lines, index = null) =>
  $('detail').replaceChildren(el('h2', title), ...lines.map((l) => el('p', l)), ...pageLinks(index));

/* An open fold: its members in the order the data gives, each a row that finds its item (O14). */
const drawFold = (fold) => {
  detail(fold.lines[0], [fold.members.length + ' member row(s). Click one to find it.']);
  const list = el('ul', '', { id: 'members' });
  list.append(...fold.members.map((m) => {
    const row = el('li');
    row.append(button(m.text, () => locate(m.ref[1])));
    return row;
  }));
  $('detail').append(list);
};

/* O18: the codes the selected box or line holds with a count each, worst severity first. */
const drawFindings = (view, which, at) => {
  if (!(state.feat.findings && hasFindings)) return;
  const flag = data.findings[data.views.indexOf(view)][which].find((f) => f[0] === at);
  if (flag === undefined) return;
  const list = el('ul', '', { id: 'findings' });
  list.append(...flag[3].map((r) => {
    const row = el('li', r[1] + ' (' + r[0] + ') x ' + r[2]);
    const texts = el('ul');
    texts.append(...r[3].map((m) => el('li', m)));
    row.append(texts);
    return row;
  }));
  const total = flag[3].reduce((n, r) => n + r[2], 0);
  $('detail').append(el('h3', 'Findings (' + total + ')'), list);
};

const drawDetail = (view) => {
  if (state.feat.matrix && state.cell !== null) { drawCell(); return; }
  const fold = openFold();
  if (fold !== null && (state.sel === null || state.sel === 'b' + view.boxes.indexOf(fold))) {
    drawFold(fold);
    return;
  }
  if (state.sel === null && altOn()) {
    detail(state.feat.matrix ? 'Matrix' : 'Signals',
      [state.feat.matrix ? 'Click a count to list its cables.' : 'Click a module or a field device to find it.']);
    return;
  }
  if (state.sel === null) {
    detail(view.boxes.length + ' boxes, ' + view.lines.length + ' lines',
      ['Click a box or a line to trace its connections. Double-click a box, or press Enter, to open it.']);
    return;
  }
  const at = Number(state.sel.slice(1));
  if (state.sel[0] === 'l') {
    const line = view.lines[at];
    detail((line.text === '' ? line.kind : line.text) + ' (' + line.kind + ')',
      [view.boxes[line.a].lines[0] + ' - ' + view.boxes[line.b].lines[0]]);
    drawFindings(view, 1, at);
    return;
  }
  const box = view.boxes[at];
  const own = box.ref[0] === 'item' ? data.items[box.ref[1]] : null;
  detail(box.lines[0], [...box.lines.slice(1), ...(own === null ? [] : facts(own)),
    ...(own === null ? [] : signalsOf(box.ref[1]))], own === null ? null : box.ref[1]);
  drawHolds(box);
  drawFindings(view, 0, at);
};

/* The parts tree (O12): units, then their items, strips last, as `derive.overview_tree` gives the
   rows. Each item has a show box. Children are built when a node is opened, so a large plant
   costs nothing until it is read. */
const kidsOf = new Map();
data.tree.forEach((row, i) => {
  const key = row.parent === null ? -1 : row.parent;
  if (!kidsOf.has(key)) kidsOf.set(key, []);
  kidsOf.get(key).push(i);
});
const treeName = (row) => {
  if (!row.is_unit) return button(row.label, () => locate(row.item));
  if (row.unit === null) return el('span', row.label);
  return button(row.label, () => { go(row.unit, null); commit(true); });
};
const treeNode = (r) => {
  const row = data.tree[r];
  const head = [];
  if (!row.is_unit) {
    const box = el('input', '', { type: 'checkbox', 'aria-label': 'Show ' + row.label });
    box.checked = !state.off.has(row.item);
    box.addEventListener('change', () => {
      if (box.checked) state.off.delete(row.item); else state.off.add(row.item);
      commit(false);
    });
    head.push(box);
  }
  head.push(treeName(row));
  const kids = kidsOf.get(r);
  if (kids === undefined) { const leaf = el('li'); leaf.append(...head); return leaf; }
  const node = el('details');
  const summary = el('summary');
  summary.append(...head);
  node.append(summary);
  node.addEventListener('toggle', () => {
    if (node.open && node.querySelector('ul') === null) {
      const list = el('ul');
      list.append(...kids.map((k) => { const li = el('li'); li.append(treeNode(k)); return li; }));
      node.append(list);
    }
  });
  return node;
};
const drawTree = () => {
  const list = el('ul');
  list.append(...(kidsOf.get(-1) ?? []).map((i) => { const li = el('li'); li.append(treeNode(i)); return li; }));
  $('tree').replaceChildren(list);
};

/* Where an item is drawn: the smallest level that holds its box, else a view that opens it. */
const placeOf = (item) => {
  const holds = (v) => v.boxes.some((b) => b.at === null && b.ref[0] === 'item' && b.ref[1] === item);
  const plain = data.views.filter((v) => v.open === null && holds(v));
  const pool = plain.length > 0 ? plain : data.views.filter(holds);
  return pool.reduce((best, v) => (best === null || v.boxes.length < best.boxes.length ? v : best), null);
};
const locate = (item) => {
  const view = placeOf(item);
  if (view === null) { detail(data.items[item].label, ['Not drawn on any level.']); return; }
  go(view.unit, view.level, view.mode, view.open);
  state.sel = 'b' + view.boxes.findIndex((b) => b.at === null && b.ref[0] === 'item' && b.ref[1] === item);
  commit(true);
};

const hitsFor = (query) => {
  const q = query.trim().toLowerCase();
  if (q === '') return [];
  const found = data.items.map((item, i) => [item.label.toLowerCase(), i]).filter(([text]) => text.includes(q));
  found.sort((a, b) => (a[0].startsWith(q) ? 0 : 1) - (b[0].startsWith(q) ? 0 : 1));
  return found.slice(0, 10).map(([, i]) => i);
};
const drawHits = () => {
  const hits = hitsFor($('search').value);
  $('hits').replaceChildren(...hits.map((i, n) => {
    const row = el('li', data.items[i].label, { role: 'option', 'aria-selected': String(n === 0) });
    row.addEventListener('mousedown', (event) => { event.preventDefault(); locate(i); $('search').value = ''; drawHits(); });
    return row;
  }));
  $('search').setAttribute('aria-expanded', String(hits.length > 0));
};
"""
