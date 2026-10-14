"""Page script, part 4: the Features panel (O16).

Every switch lives in `state.feat`. Focus is live (O17), zoom needs a box with a level inside (O6). Changes only is a choice inside the changes switch,
shown while it is on (O19). The unit view's four values are the unit level's modes.
"""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_FEATURES: Final[str] = r"""
const FEATURES = [['zoom', 'Continuous zoom'], ['matrix', 'Matrix'],
  ['signals', 'Signals lens'], ['locfold', 'Location fold'],
  ['focus', 'Focus'], ['findings', 'Findings'], ['changes', 'Changes']];
const UNIT_VIEWS = [['groups', 'Groups folded'], ['see_through', 'All devices'], ['lanes', 'Lanes'],
  ['plain', 'Plain']];
/* The location fold is listed only when the plant has a place view to fold into. */
const hasLocFold = data.views.some((v) => v.mode === 'location');
const hasMatrix = data.matrix !== null;
const hasFindings = data.findings !== null;
const ROWS = FEATURES.filter(([id]) => (id !== 'zoom' || hasZoom) && (id !== 'locfold' || hasLocFold) && (id !== 'matrix' || hasMatrix)
  && (id !== 'findings' || hasFindings) && (id !== 'changes' || hasChanges));

const switchRow = ([id, name]) => {
  const box = el('input', '', { type: 'checkbox', 'data-switch': id });
  const row = el('label');
  row.append(box, ' ' + name);
  if (id === 'focus') {
    const k = el('select', '', { 'data-switch': 'k', 'aria-label': 'Focus hops' });
    k.append(...[1, 2, 3].map((n) => el('option', 'k = ' + n, { value: String(n) })));
    row.append(' ', k);
  }
  if (id === 'changes') {
    const only = el('span');
    only.append(el('input', '', { type: 'checkbox', 'data-switch': 'changesonly' }), ' Changes only');
    row.append(' ', only);
  }
  return row;
};
const viewRow = ([mode, name]) => {
  const radio = el('input', '', { type: 'radio', name: 'unitview', value: mode, 'data-unitview': mode });
  const row = el('label');
  row.append(radio, ' ' + name);
  return row;
};
const buildFeatures = () => {
  const view = el('fieldset');
  view.append(el('legend', 'Unit view'), ...UNIT_VIEWS.map(viewRow));
  $('feat-body').replaceChildren(...ROWS.map(switchRow), view);
};

/* Show `state` in the panel: the unit view's values exist only on a unit level. */
const syncFeatures = () => {
  const unitLevel = levelKind(state.unit, state.level) === 'unit';
  for (const box of $('feat-body').querySelectorAll('input, select')) {
    const id = box.dataset.switch;
    const mode = box.dataset.unitview;
    if (mode !== undefined) {
      box.disabled = !unitLevel || !hasView(state.unit, state.level, mode, null);
      box.checked = unitLevel && state.mode === mode;
    } else if (id === 'k') {
      box.value = String(state.feat.k);
      box.disabled = !state.feat.focus;
    } else if (id === 'changesonly') {
      box.checked = state.feat.changesonly;
      box.parentElement.hidden = !state.feat.changes;
    } else {
      box.checked = state.feat[id];
      box.disabled = false;
    }
  }
};

$('feat-body').addEventListener('change', (event) => {
  const box = event.target;
  if (box.dataset.unitview !== undefined) {
    state.mode = box.value;
    state.open = null;
    state.sel = null;
    commit(true);
    return;
  }
  if (box.dataset.switch === 'k') state.feat.k = Number(box.value);
  else state.feat[box.dataset.switch] = box.checked;
  if (box.dataset.switch === 'locfold') pickLocFold();
  commit(false);
});
buildFeatures();
"""
