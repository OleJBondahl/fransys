"""Page script, part 3b: the location fold's place boxes (O9, O14).

A place box opens nothing. The details panel lists the units and loose items it holds, from the
data. The Features handler calls `pickLocFold()` after it sets `state.feat.locfold`.
"""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_PLACES: Final[str] = r"""
/* A place box's members under its title: a unit opens its level, an item in no unit is found. */
const drawHolds = (box) => {
  const held = box.holds ?? [];
  if (held.length === 0) return;
  const list = el('ul', '', { id: 'members' });
  list.append(...held.map(([ref, label]) => {
    const row = el('li');
    const open = () => { if (ref[0] === 'unit') { go(ref[1], null); commit(true); } else locate(ref[1]); };
    row.append(button(label, open));
    return row;
  }));
  $('detail').append(list);
};

/* The switch was set: the system level follows it, to the location view or back to plain. */
const pickLocFold = () => {
  if (levelKind(state.unit, state.level) !== 'system' || !hasView(null, null, 'location', null)) return;
  state.mode = state.feat.locfold ? 'location' : 'plain';
  state.open = null;
  state.sel = null;
};
"""
