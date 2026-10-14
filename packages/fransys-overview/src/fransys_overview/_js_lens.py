"""Page script, part 5b: the Signals lens (O8): PLC module, channel, field device, no layout."""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_LENS: Final[str] = r"""
const KIND_LABEL = { digital_in: 'Digital in', digital_out: 'Digital out', analogue_in: 'Analogue in', analogue_out: 'Analogue out' };

/* A name that finds its item when the page holds one and shows; plain text otherwise. */
const lensName = (text, item) => (item === null || state.off.has(item) ? el('span', text) : button(text, () => locate(item)));

const lensRow = (ch) => {
  const tr = el('tr');
  const device = ch.device === null ? el('span', 'spare') : lensName(ch.device, ch.device_item);
  const cell = el('td');
  cell.append(device);
  tr.append(el('td', String(ch.number)), el('td', KIND_LABEL[ch.kind] ?? ch.kind), el('td', ch.signal ?? ''), cell);
  return tr;
};

const lensModule = (m) => {
  const head = el('tr');
  head.append(...['Channel', 'Kind', 'Signal', 'Field device'].map((t) => el('th', t, { scope: 'col' })));
  const table = el('table');
  table.append(head, ...m.channels.map(lensRow));
  const title = el('h3');
  title.append(lensName(m.designation, m.item));
  return [title, table];
};

const drawLens = () => {
  if (data.lens.length === 0) return [el('p', 'No PLC channels in this model.')];
  const shown = data.lens.filter((m) => m.item === null || !state.off.has(m.item));
  return [el('h2', 'Signals: PLC module, channel, field device'), ...shown.flatMap(lensModule)];
};
"""
