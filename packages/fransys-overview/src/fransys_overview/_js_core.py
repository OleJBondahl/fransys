"""Page script, part 1: the data, the state, the levels and the URL hash (O1, O5, O16, O23).

The script computes no fact: it picks which recorded view to show, and hides what is switched off.
"""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_CORE: Final[str] = r"""
const data = JSON.parse(document.getElementById('overview-data').textContent);
const $ = (id) => document.getElementById(id);
const SPLITS = [['none', 'Nothing'], ['unit', 'Unit'], ['group', 'Function group'],
  ['kind', 'Item kind'], ['location', 'Location']];
const SPLIT_AT = { unit: 0, group: 1, kind: 2, location: 3 };
const ORDER = { unit: ['groups', 'see_through', 'plain', 'lanes'], system: ['plain', 'location', 'fields'],
  group: ['see_through'] };
const MODE_NAME = { groups: 'Function groups', see_through: 'All devices', plain: 'Plain',
  lanes: 'Lanes', location: 'By location', fields: 'Field devices folded' };

const state = { unit: null, level: null, mode: 'plain', open: null, split: 'none',
  hidden: new Set(), off: new Set(), sel: null, cell: null, theme: 'system',
  feat: { zoom: false, matrix: false, signals: false, locfold: false, focus: false, k: 1,
    findings: false, changes: false, changesonly: false } };

/* An open box is its reference, then for a stub the reference of the box it hangs on (O24). */
const oneKey = (ref) => ref[0] + '.' + (ref[1] ?? '');
const refKey = (ref) => (ref === null ? '-' : oneKey(ref) + (ref.length > 2 ? '@' + oneKey(ref.slice(2)) : ''));
const keyOf = (unit, level, mode, open) => [unit ?? '', refKey(level), mode, refKey(open)].join('|');
const views = new Map(data.views.map((view) => [keyOf(view.unit, view.level, view.mode, view.open), view]));
/* A strip is a recorded view. A fold is a box of the closed view whose members the details panel
   lists, so it has no view of its own (B2). `state.open` holds either; one at a time. */
const shownOpen = () => (hasView(state.unit, state.level, state.mode, state.open) ? state.open : null);
const current = () => views.get(keyOf(state.unit, state.level, state.mode, shownOpen()));
const openOf = (box) => (box.at === null ? box.ref : [...box.ref, ...box.at]);
const foldBoxes = () => (views.get(keyOf(state.unit, state.level, state.mode, null))?.boxes ?? [])
  .filter((box) => box.members.length > 0);
const openFold = () => (state.open === null ? null
  : foldBoxes().find((box) => sameRef(openOf(box), state.open)) ?? null);
const hasView = (unit, level, mode, open) => views.has(keyOf(unit, level, mode, open));

/* The label a reference prints: the first text line of the first box that stands for it, its
   place box first, else its first stub (a folded field box has no place box of its own). */
const refLabels = new Map();
const stubLabels = new Map();
for (const view of data.views) {
  for (const box of view.boxes) {
    const key = oneKey(box.ref);
    if (box.at === null && !refLabels.has(key)) refLabels.set(key, box.lines[0] ?? '');
    if (box.at !== null && !stubLabels.has(key)) stubLabels.set(key, box.lines[0] ?? '');
  }
}
const plainLabel = (ref) => refLabels.get(oneKey(ref)) ?? stubLabels.get(oneKey(ref)) ?? refKey(ref);
const labelOf = (ref) => plainLabel(ref) + (ref.length > 2 ? ' on ' + plainLabel(ref.slice(2)) : '');

const levelKind = (unit, level) => (unit === null ? 'system' : level === null ? 'unit' : 'group');
const modesOf = (unit, level) =>
  ORDER[levelKind(unit, level)].filter((mode) => hasView(unit, level, mode, null));

const settle = () => {
  if (!hasView(state.unit, state.level, state.mode, state.open) && openFold() === null) state.open = null;
  if (!hasView(state.unit, state.level, state.mode, null)) state.mode = modesOf(state.unit, state.level)[0] ?? 'plain';
  /* On the system level the Location fold switch and the 'location' mode are one fact (O9). */
  if (levelKind(state.unit, state.level) === 'system' && hasView(null, null, 'location', null)) state.feat.locfold = state.mode === 'location';
};

/* Go to a level, in its first mode (the unit view's default is the function groups). */
const go = (unit, level, mode = null, open = null) => {
  state.unit = unit;
  state.level = level;
  const wantsPlaces = unit === null && state.feat.locfold && hasView(null, null, 'location', null);
  state.mode = mode ?? (wantsPlaces ? 'location' : modesOf(unit, level)[0] ?? 'plain');
  state.open = open;
  state.sel = null;
  settle();
};

/* The levels above the one shown, outermost first, as [label, unit, level]. */
const trail = () => {
  const up = [];
  for (let at = state.unit; at !== null; at = data.unit_parents[at]) up.unshift(at);
  const list = [['System', null, null], ...up.map((u) => [data.units[u], u, null])];
  if (state.level !== null) list.push([labelOf(state.level), state.unit, state.level]);
  return list;
};

const parentLevel = () => {
  const list = trail();
  return list.length > 1 ? list[list.length - 2] : null;
};

/* What a box opens: a unit its level, a function group or the strips box its level, a strip its
   terminals in place, a fold its member list in the panel (O1, O5, O14). A place box opens nothing. */
const target = (box) => {
  const [kind, index] = box.ref;
  if (box.members.length > 0) {
    const open = openOf(box);
    return foldBoxes().some((b) => sameRef(openOf(b), open)) ? { open, fold: true } : null;
  }
  if (box.at !== null) {
    const open = [...box.ref, ...box.at];
    return hasView(state.unit, state.level, state.mode, open) ? { open } : null;
  }
  if (kind === 'unit' && hasView(index, null, modesOf(index, null)[0] ?? 'plain', null)) return { unit: index };
  if (kind === 'group' || kind === 'strips') return { unit: state.unit, level: box.ref };
  if (kind === 'fields' || kind === 'item') {
    return hasView(state.unit, state.level, state.mode, box.ref) ? { open: box.ref } : null;
  }
  return null;
};

/* Null when the box opens nothing, else whether the view refits: a fold never moves it (A13). */
const enter = (box) => {
  const next = target(box);
  if (next === null) return null;
  if (!('open' in next)) { go(next.unit, next.level ?? null); return true; }
  const was = shownOpen();
  state.open = sameRef(state.open, next.open) ? null : next.open;
  state.sel = null;
  return !(next.fold === true && was === null);
};
const sameRef = (a, b) => refKey(a) === refKey(b);

/* The URL hash holds the whole view, so Back and Forward walk it (O23). Ids never reach it. */
const encode = () => {
  const p = new URLSearchParams();
  p.set('u', state.unit ?? '');
  p.set('l', state.level === null ? '' : refKey(state.level));
  p.set('m', state.mode);
  p.set('o', state.open === null ? '' : refKey(state.open));
  p.set('c', state.split);
  p.set('h', [...state.hidden].join(','));
  p.set('i', [...state.off].join(','));
  p.set('s', state.sel ?? '');
  p.set('f', Object.keys(state.feat).filter((id) => state.feat[id] === true).map((id) => (id === 'changesonly' ? 'changes.only' : id)).join(','));
  p.set('k', String(state.feat.k));
  return p.toString();
};
const parseOne = (text) => {
  const parts = text.split('.');
  return parts.length === 2 ? [parts[0], parts[1] === '' ? null : Number(parts[1])] : null;
};
const parseRef = (text) => {
  const [head, tail = null] = (text ?? '').split('@');
  const ref = parseOne(head);
  const at = tail === null ? null : parseOne(tail);
  return ref !== null && at !== null ? [...ref, ...at] : ref;
};
const num = (text) => (text === '' || text === null ? null : Number(text));
const decode = (text) => {
  const p = new URLSearchParams(text);
  state.unit = num(p.get('u'));
  state.level = parseRef(p.get('l'));
  state.mode = p.get('m') ?? 'plain';
  state.open = parseRef(p.get('o'));
  state.split = p.get('c') ?? 'none';
  state.hidden = new Set((p.get('h') ?? '').split(',').filter((x) => x !== ''));
  state.off = new Set((p.get('i') ?? '').split(',').filter((x) => x !== '').map(Number));
  state.sel = p.get('s') === '' ? null : p.get('s');
  const on = new Set((p.get('f') ?? '').split(','));
  for (const id of Object.keys(state.feat)) if (id !== 'k') state.feat[id] = on.has(id);
  state.feat.changesonly = on.has('changes.only');
  state.feat.k = [1, 2, 3].includes(Number(p.get('k'))) ? Number(p.get('k')) : 1;
  settle();
};
"""
