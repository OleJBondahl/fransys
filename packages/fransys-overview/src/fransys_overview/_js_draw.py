"""Page script, part 2: the colours, what is hidden, and the view as Cytoscape elements (O10, O26).

Positions are the recorded ones, scaled; every element has a preset position, so no layout runs.
"""

from typing import Final

JS_DRAW: Final[str] = r"""
const th = data.text_height;
const K = 13 / th;
const dark = () => document.documentElement.getAttribute('data-theme') === 'dark'
  || (document.documentElement.getAttribute('data-theme') !== 'light'
    && window.matchMedia('(prefers-color-scheme: dark)').matches);
const tone = () => (dark() ? 'dark' : 'light');
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/* One class value per colour split; the hue of a class is its place in the sorted classes. */
const classesOf = (split) => {
  const found = new Set();
  for (const view of data.views) for (const box of view.boxes) found.add(box.cls[SPLIT_AT[split]]);
  found.delete(null);
  return [...found].sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
};
const hueOf = (split, cls) => {
  if (split === 'none' || cls === null) return data.palette.neutral[tone()];
  const hues = data.palette.hues;
  return hues[classesOf(split).indexOf(cls) % hues.length][tone()];
};
const classKey = (cls) => state.split + ':' + cls;

/* Items hidden in the parts tree hide their descendants too. */
const itemOff = (item) => {
  for (let at = item; at !== null && at !== undefined; at = data.items[at].parent) {
    if (state.off.has(at)) return true;
  }
  return false;
};
const boxHidden = (box) => {
  if (box.ref[0] === 'item' && itemOff(box.ref[1])) return true;
  const cls = state.split === 'none' ? null : box.cls[SPLIT_AT[state.split]];
  return cls !== null && state.hidden.has(classKey(cls));
};

const FONT = th * K;
const boxNode = (box, i) => ({
  group: 'nodes',
  data: { id: 'b' + i, role: 'box', box: i, label: box.lines.join('\n'), w: box.w * K, h: box.h * K,
    stroke: hueOf(state.split, state.split === 'none' ? null : box.cls[SPLIT_AT[state.split]]),
    dashed: box.dashed, stub: box.at !== null,
    open: state.open !== null && box.members.length > 0 && sameRef(openOf(box), state.open) },
  position: { x: (box.x + box.w / 2) * K, y: (box.y + box.h / 2) * K },
});
const tabNodes = (box, i) => box.tabs.map((tab, j) => ({
  group: 'nodes',
  data: { id: 't' + i + '_' + j, role: 'tab', box: i, label: tab[3] ?? '',
    w: (tab[2] + th) * K, h: (th * 2) * K },
  position: { x: (tab[0] + (tab[2] + th) / 2) * K, y: (tab[1] + th) * K },
}));
const lineNodes = (line, i) => {
  const nodes = line.pts.map((p, k) => ({
    group: 'nodes', data: { id: 'p' + i + '_' + k, role: 'pt', line: i },
    position: { x: p[0] * K, y: p[1] * K } }));
  const edges = line.pts.slice(1).map((_, k) => ({
    group: 'edges', data: { id: 'e' + i + '_' + k, role: 'line', line: i, kind: line.kind,
      source: 'p' + i + '_' + k, target: 'p' + i + '_' + (k + 1) } }));
  const label = line.text === '' ? [] : [{ group: 'nodes',
    data: { id: 'l' + i, role: 'text', line: i, label: line.text },
    position: { x: line.tx * K, y: line.ty * K } }];
  return [...nodes, ...edges, ...label];
};

/* O18: a badge by severity on each box and line a finding names (worst severity, count). */
const BADGE = { error: "#c62828", warning: "#e69500", info: "#1e6fd0" };
const BADGE_H = FONT * 1.6;
const badgeW = (label) => Math.max(BADGE_H, label.length * FONT * 0.6 + FONT * 0.8);
const badgeNode = (id, at, flag, extra) => ({ group: "nodes",
  data: { id, role: "badge", label: String(flag[2]), w: badgeW(String(flag[2])),
    color: BADGE[flag[1]], ...extra },
  position: { x: at[0] * K, y: at[1] * K } });
const badgesOf = (view, shown) => {
  const on = state.feat.findings && hasFindings;
  const rows = on ? data.findings[data.views.indexOf(view)] : [[], []];
  const boxes = rows[0].filter((f) => shown.has(f[0])).map((f) => {
    const box = view.boxes[f[0]];
    return badgeNode("fb" + f[0], [box.x + box.w, box.y], f, { box: f[0] });
  });
  const drawn = (f) => shown.has(view.lines[f[0]].a) && shown.has(view.lines[f[0]].b);
  const lines = rows[1].filter(drawn).map((f) => {
    const pts = view.lines[f[0]].pts;
    return badgeNode("fl" + f[0], pts[Math.floor(pts.length / 2)], f, { line: f[0] });
  });
  return [...boxes, ...lines];
};

/* O4: a lane's text, drawn from its recorded corner; the label hangs right. */
const headNodes = (view) => view.heads.map((h, i) => ({
  group: 'nodes', data: { id: 'h' + i, role: 'head', label: h[0] },
  position: { x: h[1] * K, y: (h[2] + th / 2) * K } }));

const elementsOf = (view) => {
  const shown = new Set();
  const els = [];
  const keep = changeKeep(view);
  view.boxes.forEach((box, i) => {
    if (boxHidden(box) || (keep !== null && !keep.boxes.has(i))) return;
    shown.add(i);
    els.push(boxNode(box, i), ...tabNodes(box, i));
  });
  view.lines.forEach((line, i) => {
    const wanted = keep === null || keep.lines.has(i);
    if (shown.has(line.a) && shown.has(line.b) && wanted) els.push(...lineNodes(line, i));
  });
  els.push(...headNodes(view), ...badgesOf(view, shown));
  return markChanges(view, els);
};

const styleSheet = () => {
  const fg = css('--fg');
  const bg = css('--bg');
  const line = css('--line');
  const base = { 'font-size': FONT, 'font-family': 'system-ui, sans-serif', color: fg };
  return [
    { selector: 'node[role="box"]', style: { ...base, shape: 'rectangle', label: 'data(label)',
      width: 'data(w)', height: 'data(h)', 'text-wrap': 'wrap', 'text-valign': 'center',
      'text-halign': 'center', 'background-color': 'data(stroke)', 'background-opacity': 0.14,
      'border-width': 2, 'border-color': 'data(stroke)', 'line-height': 1.25 } },
    { selector: 'node[?stub]', style: {
      'background-opacity': 0, 'border-width': 1, 'border-style': 'solid' } },
    { selector: 'node[?open]', style: {
      'background-opacity': 0.3, 'border-width': 4, 'border-style': 'double' } },
    { selector: 'node[?dashed]', style: { 'border-style': 'dashed' } },
    { selector: 'node[role="tab"]', style: { ...base, shape: 'rectangle', label: 'data(label)',
      width: 'data(w)', height: 'data(h)', 'text-valign': 'center', 'text-halign': 'center',
      'background-color': bg, 'border-width': 1, 'border-color': line, 'font-size': FONT * 0.9 } },
    { selector: 'node[role="badge"]', style: { shape: 'round-rectangle', label: 'data(label)',
      width: 'data(w)', height: BADGE_H, 'corner-radius': BADGE_H / 2,
      'background-color': 'data(color)', color: '#fff',
      'font-size': FONT * 0.9,
      'text-valign': 'center', 'text-halign': 'center', 'z-index': 20, 'border-width': 1,
      'border-color': bg } },
    { selector: 'node[role="head"]', style: { ...base, width: 1, height: 1, 'background-opacity': 0,
      label: 'data(label)', 'text-valign': 'center', 'text-halign': 'right',
      'font-weight': 'bold', events: 'no' } },
    { selector: 'node[role="pt"]', style: { width: 1, height: 1, opacity: 0, events: 'no' } },
    { selector: 'node[role="text"]', style: { ...base, shape: 'rectangle', label: 'data(label)',
      width: 'label', height: 'label', padding: 1, 'background-color': bg,
      'background-opacity': 0.85, 'text-valign': 'center', 'text-halign': 'center' } },
    { selector: 'edge', style: { width: 1.5, 'line-color': line, 'curve-style': 'straight' } },
    { selector: 'edge[kind="cable"]', style: { width: 3 } },
    { selector: 'edge[kind="mate"]', style: { 'line-style': 'dotted', width: 2.5 } },
    { selector: '.dim', style: { opacity: 0.18 } },
    { selector: '.faded', style: { opacity: 0.08 } },
    { selector: 'node.hi[role="box"]', style: { 'border-width': 4 } },
    { selector: 'edge.hi', style: { 'line-color': css('--accent'), width: 4, 'z-index': 10 } },
    ...CHANGE_STYLE,
    ...zoomStyle(),
  ];
};
"""
