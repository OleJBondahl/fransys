"""Page script, part 3b: focus (O17). With focus on and a selection, the selection and its neighbours up to k hops stay sharp and the rest fades.

The hops count over the lines drawn on the level shown, read from the cy graph; the page
computes no engineering fact.
"""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_FOCUS: Final[str] = r"""
/* A selected line starts at both of its boxes; a selected box starts at itself. */
const focusSeeds = (view) => {
  const at = Number(state.sel.slice(1));
  return state.sel[0] === 'l' ? [view.lines[at].a, view.lines[at].b] : [at];
};

/* The hop count of each box from the selection, expanding k rounds over the drawn lines. */
const focusHops = (view) => {
  const drawn = new Set(cy.edges().map((edge) => edge.data('line')));
  const hops = new Map(focusSeeds(view).map((box) => [box, 0]));
  for (let level = 0; level < state.feat.k; level += 1) {
    view.lines.forEach((line, i) => {
      if (!drawn.has(i)) return;
      [[line.a, line.b], [line.b, line.a]].forEach(([near, far]) => {
        if (hops.get(near) === level && !hops.has(far)) hops.set(far, level + 1);
      });
    });
  }
  return hops;
};

/* The sharp boxes and lines: a line is sharp when one of its boxes was expanded (hop below k). */
const focusSharp = (view) => {
  const hops = focusHops(view);
  const lines = new Set();
  view.lines.forEach((line, i) => {
    if ((hops.get(line.a) ?? Infinity) < state.feat.k || (hops.get(line.b) ?? Infinity) < state.feat.k) lines.add(i);
  });
  return { boxes: new Set(hops.keys()), lines };
};

/* Runs after every render: a selection with focus on keeps its neighbourhood sharp and fades the rest (O17). */
const applyFocus = (view) => {
  cy.elements().removeClass('faded');
  if (!state.feat.focus || state.sel === null) return;
  const sharp = focusSharp(view);
  cy.elements().forEach((el) => {
    const box = el.data('box');
    const line = el.data('line');
    const keep = box !== undefined ? sharp.boxes.has(box) : sharp.lines.has(line);
    if (keep) el.removeClass('dim'); else el.addClass('faded');
  });
};
"""
