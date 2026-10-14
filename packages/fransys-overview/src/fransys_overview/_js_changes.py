"""Page script, part 3b: the changes layer (O19).

The data holds what each view marks, and the things no box carries; this only
colours, filters and lists them (A4: nothing is computed that the data does not hold).
"""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_CHANGES: Final[str] = r"""
const hasChanges = data.changes !== null;
const changesOn = () => hasChanges && state.feat.changes;

/* The marks of a view, by box and by line; empty while the switch is off. */
const marksOf = (view) => {
  const rows = changesOn() ? data.changes.views[data.views.indexOf(view)] : [[], []];
  return { boxes: new Map(rows[0]), lines: new Map(rows[1]) };
};

/* "Changes only": the marked boxes, and the ends of the marked lines; `null` when not filtering. */
const changeKeep = (view) => {
  if (!changesOn() || !state.feat.changesonly) return null;
  const marks = marksOf(view);
  const boxes = new Set(marks.boxes.keys());
  for (const at of marks.lines.keys()) { boxes.add(view.lines[at].a); boxes.add(view.lines[at].b); }
  return { boxes, lines: new Set(marks.lines.keys()) };
};

const markChanges = (view, els) => {
  const marks = marksOf(view);
  for (const one of els) {
    const d = one.data;
    const kind = d.role === 'box' ? marks.boxes.get(d.box) : d.role === 'line' ? marks.lines.get(d.line) : undefined;
    if (kind === undefined) continue;
    d.chg = kind;
  }
  return els;
};

const CHANGE_STYLE = [
  { selector: 'node[chg="added"]', style: { 'border-color': '#2e7d32', 'border-width': 4 } },
  { selector: 'node[chg="changed"]', style: { 'border-color': '#e69500', 'border-width': 4 } },
  { selector: 'edge[chg="added"]', style: { 'line-color': '#2e7d32', width: 4 } },
  { selector: 'edge[chg="changed"]', style: { 'line-color': '#e69500', width: 4 } },
];

/* While the switch is on, the legend names the marks: colour and border, never a text prefix. */
const legendChanges = () => {
  if (!changesOn()) return;
  $('legend').append(el('span', 'Changes: green border added, orange border changed.'));
};

/* The things no box carries (removed ones, and any with no box on a view): one group per kind. */
const drawRemoved = () => {
  if (!changesOn()) return;
  const rest = data.changes.rest;
  $('detail').append(el('h3', 'Since ' + data.changes.since));
  if (rest.length === 0) $('detail').append(el('p', 'Every change is on a box or a line.'));
  for (const [kind, name] of [['removed', 'Removed'], ['added', 'Added'], ['changed', 'Changed']]) {
    const group = rest.filter((r) => r[0] === kind);
    if (group.length === 0) continue;
    const list = el('ul', '', { id: 'changes-' + kind });
    list.append(...group.map((r) => el('li', r[1])));
    $('detail').append(el('h4', name + ' (' + group.length + ')'), list);
  }
};
"""
