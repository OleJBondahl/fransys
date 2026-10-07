"""Field case: a jumper bar bought with a bridged run is an accessory of its strip.

The engineering shape: a terminal strip X1 with a run of three terminals bridged together, which
feeds a lamp. The bridge is physically a jumper bar, a part with no function that sits on the strip.
The author states it once: `d.device(None, part, name=..., parent=X1)`.

The bug: `parent=` took only a device, so a strip, a run or a terminal as parent crashed with a bare
`AttributeError: '_item'`.

Fixing decision: author-0025 (`parent=` also takes a strip, the accessory prints the strip's
designation and the BOM counts it; a run or a terminal raises `AuthorError` naming the strip).
"""

import fransys as fr
import pytest

from fransys_model.derive import bom_lines, item_designation

_BAR = "DEMO-JUMPER-BAR-3P"


def _design() -> tuple[fr.Design, fr.TerminalStrip]:
    """Strip X1 with a bridged run of three feeding the lamp H1."""
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
    run = x1.run("L", 3, bridged=True)
    h1 = d.device("H1", "DEMO-LAMP-24")
    d.wire(h1[1], run[1], wire=("BK", 1.5))
    return d, x1


def test_a_jumper_bar_on_the_strip_has_a_bom_line_printing_the_strip() -> None:
    """One bar, the strip's designation, one BOM line counting it."""
    d, x1 = _design()
    bar = d.device(None, _BAR, name="bar", parent=x1)
    model = fr.build(d).model
    assert item_designation(model, bar.id) == "X1"
    (line,) = [ln for ln in bom_lines(model) if ln.mpn == _BAR]
    assert line.count == 1
    assert line.designations == ("-X1",)


def test_a_run_as_parent_raises_an_author_error_naming_its_strip() -> None:
    d, x1 = _design()
    run = x1.run("M", 2)
    with pytest.raises(fr.AuthorError, match=r"a device or a strip.*X1"):
        d.device(None, _BAR, name="bar", parent=run)


def test_a_terminal_as_parent_raises_an_author_error_naming_its_strip() -> None:
    d, x1 = _design()
    with pytest.raises(fr.AuthorError, match=r"a device or a strip.*X1"):
        d.device(None, _BAR, name="bar", parent=x1[2])  # ty: ignore[no-matching-overload] -- the refusal is the case


def test_any_other_handle_as_parent_raises_an_author_error() -> None:
    d, _ = _design()
    with pytest.raises(fr.AuthorError, match="a device or a strip"):
        d.device(None, _BAR, name="bar", parent="X1")  # ty: ignore[no-matching-overload] -- the refusal is the case
