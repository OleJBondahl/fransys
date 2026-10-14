"""Page script, part 5a: the matrix index (O7): a table of cable counts per pair of boxes, no layout."""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_MATRIX: Final[str] = r"""
/* The stored matrix has row < col; a count shows in both triangles and picks the stored pair. */
const matrixCell = (m, a, b) => {
  const [row, col] = a < b ? [a, b] : [b, a];
  const found = m.cells.find((c) => c[0] === row && c[1] === col);
  if (found === undefined || a === b) return el('td');
  const key = row + '.' + col;
  const cell = el('td');
  cell.append(button(String(found[2]), () => { state.cell = key; commit(false); },
    { 'aria-pressed': state.cell === key ? 'true' : 'false' }));
  return cell;
};

const drawMatrix = () => {
  const m = data.matrix;
  if (m === null) return [el('p', 'No matrix: the system level has no boxes.')];
  const head = el('tr');
  head.append(el('td'), ...m.axis.map((label) => el('th', label, { scope: 'col' })));
  const rows = m.axis.map((label, a) => {
    const tr = el('tr');
    tr.append(el('th', label, { scope: 'row' }), ...m.axis.map((_, b) => matrixCell(m, a, b)));
    return tr;
  });
  const table = el('table');
  table.append(head, ...rows);
  return [el('h2', 'Unit matrix: cables between each pair'), table];
};

/* The details of the picked cell: its cables, each finding its item when the page holds one. */
const drawCell = () => {
  const m = data.matrix;
  const [row, col] = state.cell.split('.').map(Number);
  const cell = m.cells.find((c) => c[0] === row && c[1] === col);
  detail(m.axis[row] + ' - ' + m.axis[col], [cell[2] + ' cable(s)']);
  const list = el('ul');
  list.append(...cell[3].map(([ix, label]) => {
    const li = el('li');
    li.append(ix === null ? el('span', label) : button(label, () => locate(ix)));
    return li;
  }));
  $('detail').append(list);
};
"""
