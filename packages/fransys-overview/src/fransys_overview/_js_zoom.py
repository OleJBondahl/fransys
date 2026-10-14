"""Page script, part 3c: continuous zoom (O6).

Zooming into a unit or group box fades its level in, in place: the child view's recorded boxes and
lines, scaled into the box (A4: scaling stored positions is not layout; no new position data).
The extra elements are inert (`events: no`) so a double click still opens the box.
"""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_ZOOM: Final[str] = r"""
const ZOOM_FROM = 160;
const ZOOM_FULL = 360;
const ZOOM_FILL = 0.88;

/* The view a box opens, by the box's own level: a unit its level, a group or strips box its level. */
const childViewOf = (view, box) => {
  if (box.at !== null || box.members.length > 0) return undefined;
  const [kind, index] = box.ref;
  const [unit, level] = kind === 'unit' ? [index, null] : kind === 'group' || kind === 'strips' ? [view.unit, box.ref] : [null, undefined];
  if (level === undefined) return undefined;
  const mode = modesOf(unit, level)[0];
  return mode === undefined ? undefined : views.get(keyOf(unit, level, mode, null));
};
const hasZoom = data.views.some((view) => view.open === null && view.boxes.some((box) => childViewOf(view, box) !== undefined));
const zoomOn = () => hasZoom && state.feat.zoom && !altOn();

/* Where the child view's bounding box lands inside `box`: [scale, x0, y0] in recorded units. */
const zoomFit = (box, inner) => {
  const xs = inner.boxes.map((b) => b.x);
  const ys = inner.boxes.map((b) => b.y);
  const x1 = Math.max(...inner.boxes.map((b) => b.x + b.w));
  const y1 = Math.max(...inner.boxes.map((b) => b.y + b.h));
  const [x0, y0] = [Math.min(...xs), Math.min(...ys)];
  const s = Math.min(box.w * ZOOM_FILL / (x1 - x0), box.h * ZOOM_FILL / (y1 - y0));
  return { s, at: (x, y) => [box.x + box.w / 2 + (x - (x0 + x1) / 2) * s, box.y + box.h / 2 + (y - (y0 + y1) / 2) * s] };
};

const zoomElements = (i, box, inner) => {
  const fit = zoomFit(box, inner);
  const els = [];
  inner.boxes.forEach((b, j) => {
    const [x, y] = fit.at(b.x + b.w / 2, b.y + b.h / 2);
    els.push({ group: 'nodes', classes: 'zoomed',
      data: { id: 'zb' + i + '_' + j, role: 'zbox', label: b.lines.join('\n'), w: b.w * fit.s * K, h: b.h * fit.s * K,
        fs: Math.max(FONT * fit.s, 0.5), stroke: hueOf(state.split, state.split === 'none' ? null : b.cls[SPLIT_AT[state.split]]) },
      position: { x: x * K, y: y * K } });
  });
  inner.lines.forEach((line, j) => {
    const ids = line.pts.map((p, k) => {
      const [x, y] = fit.at(p[0], p[1]);
      els.push({ group: 'nodes', classes: 'zoomed', data: { id: 'zp' + i + '_' + j + '_' + k, role: 'zpt' }, position: { x: x * K, y: y * K } });
      return 'zp' + i + '_' + j + '_' + k;
    });
    ids.slice(1).forEach((to, k) => els.push({ group: 'edges', classes: 'zoomed',
      data: { id: 'ze' + i + '_' + j + '_' + k, role: 'zline', source: ids[k], target: to } }));
  });
  return els;
};

/* 0 below ZOOM_FROM rendered pixels of box width, 1 from ZOOM_FULL. */
const zoomOpacity = (box) => Math.max(0, Math.min(1, (box.w * K * cy.zoom() - ZOOM_FROM) / (ZOOM_FULL - ZOOM_FROM)));
const zoomSeen = (box) => {
  const e = cy.extent();
  return box.x * K < e.x2 && (box.x + box.w) * K > e.x1 && box.y * K < e.y2 && (box.y + box.h) * K > e.y1;
};

const zoomIn = new Map();
/* Add the inside of each box zoomed in on, fade it by zoom, drop it when the box leaves view or zoom (render clears all). */
const zoomUpdate = (fresh) => {
  if (fresh) zoomIn.clear();
  const view = current();
  if (view === undefined) return;
  cy.batch(() => {
    view.boxes.forEach((box, i) => {
      const op = zoomOn() && cy.getElementById('b' + i).nonempty() ? zoomOpacity(box) : 0;
      const inner = op > 0 && zoomSeen(box) ? childViewOf(view, box) : undefined;
      if (inner === undefined || inner.boxes.length === 0) {
        if (zoomIn.has(i)) { zoomIn.get(i).remove(); zoomIn.delete(i); cy.getElementById('b' + i).removeStyle('text-opacity'); }
        return;
      }
      if (!zoomIn.has(i)) zoomIn.set(i, cy.add(zoomElements(i, box, inner)));
      zoomIn.get(i).style('opacity', op);
      cy.getElementById('b' + i).style('text-opacity', 1 - op);
    });
  });
};
const zoomStyle = () => [
  { selector: 'node[role="zbox"]', style: { shape: 'rectangle', label: 'data(label)', width: 'data(w)', height: 'data(h)',
    'font-size': 'data(fs)', 'font-family': 'system-ui, sans-serif', color: css('--fg'), 'text-wrap': 'wrap',
    'text-valign': 'center', 'text-halign': 'center', 'background-color': 'data(stroke)', 'background-opacity': 0.14,
    'border-width': 1, 'border-color': 'data(stroke)', 'z-index': 5, events: 'no' } },
  { selector: 'node[role="zpt"]', style: { width: 1, height: 1, opacity: 0, events: 'no' } },
  { selector: 'edge[role="zline"]', style: { width: 1, 'line-color': css('--line'), 'z-index': 6, events: 'no' } },
];
"""
