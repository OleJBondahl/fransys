"""Page script, part 4: the drawing, its events, the theme and the URL hash (O1, O14, O20, O23)."""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_MAIN: Final[str] = r"""
const cy = cytoscape({ container: $('cy'), elements: [], minZoom: 0.05, maxZoom: 6,
  autounselectify: true, boxSelectionEnabled: false });

const applyTheme = () => {
  const root = document.documentElement;
  if (state.theme === 'system') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', state.theme);
};
try { state.theme = localStorage.getItem('overview-theme') ?? 'system'; } catch (error) { state.theme = 'system'; }

/* The connections of the selected box or line stay sharp on the level shown; the rest dims. */
const trace = (view) => {
  cy.elements().removeClass('dim hi');
  if (state.sel === null) return;
  const at = Number(state.sel.slice(1));
  const lit = new Set();
  const edges = new Set();
  view.lines.forEach((line, i) => {
    const mine = state.sel[0] === 'l' ? i === at : line.a === at || line.b === at;
    if (!mine) return;
    edges.add(i);
    lit.add(line.a);
    lit.add(line.b);
  });
  if (state.sel[0] === 'b') lit.add(at);
  cy.elements().addClass('dim');
  cy.nodes().forEach((node) => {
    const own = node.data('box');
    const line = node.data('line');
    if ((own !== undefined && lit.has(own)) || (line !== undefined && edges.has(line))) node.removeClass('dim');
    if (own === at && state.sel[0] === 'b') node.addClass('hi');
  });
  cy.edges().forEach((edge) => {
    if (edges.has(edge.data('line'))) edge.removeClass('dim').addClass('hi');
  });
};

/* An open strip or stub (O5, O24): the boxes that appear only when it opens, and the boxes their
   lines join, with the lines of those boxes (`lines`, by index). Null for a closed view and for
   a field box, which fit as the whole view. */
const stripSet = (view) => {
  if (view.open === null || (view.open[0] !== 'item' && view.open.length < 3)) return null;
  const closed = views.get(keyOf(view.unit, view.level, view.mode, null));
  const shut = (box) => sameRef(box.ref, view.open.slice(0, 2))
    && (view.open.length > 2 ? box.at !== null && sameRef(box.at, view.open.slice(2)) : box.at === null);
  if (closed === undefined || !closed.boxes.some(shut)) return null;
  const was = new Set(closed.boxes.map((box) => refKey(box.ref) + '@' + box.at));
  const terminals = new Set();
  view.boxes.forEach((box, i) => { if (!was.has(refKey(box.ref) + '@' + box.at)) terminals.add(i); });
  const boxes = new Set(terminals);
  const lines = new Set();
  view.lines.forEach((line, i) => {
    if (terminals.has(line.a) || terminals.has(line.b)) lines.add(i);
    if (terminals.has(line.a)) boxes.add(line.b);
    if (terminals.has(line.b)) boxes.add(line.a);
  });
  return terminals.size === 0 ? null : { boxes, lines };
};

// Fitting never zooms in past 100 % (O1): a small view stays at true size, centred.
const fitView = () => {
  const view = current();
  const strip = view === undefined ? null : stripSet(view);
  const nodes = strip === null ? undefined : cy.nodes().filter((node) => strip.boxes.has(node.data('box'))
    || (node.data('role') === 'pt' && strip.lines.has(node.data('line'))));
  cy.fit(nodes, 30);
  if (cy.zoom() > 1) { cy.zoom(1); cy.center(nodes); }
  return { zoom: cy.zoom(), pan: { ...cy.pan() } };
};

/* With nothing selected, an open strip dims what its fit set does not hold, as trace() dims the rest. */
const dimOutsideStrip = (view) => {
  const strip = state.sel === null ? stripSet(view) : null;
  if (strip === null) return;
  cy.elements().forEach((el) => {
    const own = el.data('box');
    const line = el.data('line');
    let keep = true;
    if (own !== undefined) keep = strip.boxes.has(own);
    else if (line !== undefined) keep = strip.boxes.has(view.lines[line].a) && strip.boxes.has(view.lines[line].b);
    if (!keep) el.addClass('dim');
  });
};

let lastHash = '';
const render = (animate) => {
  settle();
  applyTheme();
  const view = current();
  const shownAgain = drawAlt();
  cy.batch(() => {
    cy.elements().remove();
    cy.style(styleSheet());
    if (view !== undefined && !altOn()) cy.add(elementsOf(view));
  });
  if (shownAgain) cy.resize();
  if ((animate && !altOn()) || shownAgain) {
    const target = fitView();
    cy.zoom({ level: target.zoom * 0.82, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
    cy.animate({ zoom: target.zoom, pan: target.pan }, { duration: 200 });
  }
  drawCrumbs();
  drawPickers();
  syncFeatures();
  if (view === undefined) { detail('No overview', ['The model has no placed overview.']); return; }
  drawLegend(view);
  legendChanges();
  $('legend').hidden = altOn();
  drawChips();
  drawOpens();
  drawDetail(view);
  drawRemoved();
  trace(view);
  dimOutsideStrip(view);
  applyFocus(view);
  zoomUpdate(true);
};
commit = (animate) => {
  render(animate);
  lastHash = encode();
  window.location.hash = lastHash;
};

cy.on('zoom pan', () => zoomUpdate(false));
/* The reader's own zoom or pan ends the fit animation of a new view; it would reset them to the fit when it ends. */
['wheel', 'pointerdown'].forEach((name) => $('cy').addEventListener(name, () => cy.stop(), { capture: true, passive: true }));
cy.on('tap', 'node, edge', (event) => {
  const role = event.target.data('role');
  if (role === 'line' || role === 'text' || (role === 'badge' && event.target.data('line') !== undefined)) state.sel = 'l' + event.target.data('line');
  else if (event.target.data('box') !== undefined) state.sel = 'b' + event.target.data('box');
  else return;
  commit(false);
});
cy.on('dbltap', 'node', (event) => {
  const index = event.target.data('box');
  const refit = index === undefined ? null : enter(current().boxes[index]);
  if (refit !== null) commit(refit);
});

$('split').addEventListener('change', () => { state.split = $('split').value; commit(false); });
$('mode').addEventListener('change', () => { state.mode = $('mode').value; state.open = null; state.sel = null; commit(true); });
$('theme').addEventListener('change', () => {
  state.theme = $('theme').value;
  try { localStorage.setItem('overview-theme', state.theme); } catch (error) { /* a preference only */ }
  render(false);
});
const pngUrl = () => cy.png({ full: false, scale: 2,
  bg: getComputedStyle(document.documentElement).getPropertyValue('--bg').trim() });
window.overviewPng = pngUrl;
$('png').addEventListener('click', () => {
  const link = el('a', '', { href: pngUrl(), download: 'overview.png' });
  document.body.append(link);
  link.click();
  link.remove();
});
$('up').addEventListener('click', () => {
  const up = parentLevel();
  if (up !== null) { go(up[1], up[2]); commit(true); }
});
$('search').addEventListener('input', drawHits);
$('search').addEventListener('keydown', (event) => {
  const first = hitsFor($('search').value)[0];
  if (event.key === 'Enter' && first !== undefined) { locate(first); $('search').value = ''; drawHits(); }
  if (event.key === 'Escape') { $('search').value = ''; drawHits(); }
});
document.addEventListener('keydown', (event) => {
  if (event.target.tagName === 'INPUT' || event.target.tagName === 'SELECT') return;
  if (event.key === 'Escape') { state.sel = null; commit(false); }
  if (event.key === 'Enter' && state.sel !== null && state.sel[0] === 'b') {
    const refit = enter(current().boxes[Number(state.sel.slice(1))]);
    if (refit !== null) commit(refit);
  }
});
window.addEventListener('hashchange', () => {
  const text = window.location.hash.slice(1);
  if (text === lastHash) return;
  lastHash = text;
  decode(text);
  render(true);
});

$('theme').value = state.theme;
drawTree();
const start = window.location.hash.slice(1);
if (start !== '') { decode(start); lastHash = start; } else { go(null, null); }
render(false);
fitView();
lastHash = encode();
"""
