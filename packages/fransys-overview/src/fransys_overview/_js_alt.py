"""Page script, part 5: the views that stand in place of the drawing (O7, O8, O16).

The matrix and the Signals lens are lists built from the page data with `textContent`: no layout,
no network. With either switch on the pane shows them and the drawing is hidden.
"""

# ruff: noqa: E501 -- the JavaScript source is not wrapped

from typing import Final

JS_ALT: Final[str] = r"""
const altOn = () => state.feat.matrix || state.feat.signals;
let wasAlt = false;

/* Show the pane when a switch asks for it; a drawing shown again is resized for its container. */
const drawAlt = () => {
  const on = altOn();
  if (!state.feat.matrix) state.cell = null;
  const pane = $('alt');
  pane.hidden = !on;
  $('cy').hidden = on;
  pane.replaceChildren(...(on ? [...(state.feat.matrix ? drawMatrix() : []), ...(state.feat.signals ? drawLens() : [])] : []));
  const back = wasAlt && !on;
  wasAlt = on;
  return back;
};
"""
