"""V1, layout-0112: `without_unused` sends an unwired contact to the spares, switch or not."""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.unused import without_unused
from fransys_model.vocab.tables import functions, items


def _plant(d) -> None:
    """A wired contactor with a coil, and a lamp wired to nothing."""
    psu = d.device("T1", "DEMO-PSU-24")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    d.device("P9", "DEMO-LAMP-24")
    blue = (BU, 0.5)
    d.wire(psu.output["+"], q.coil["A1"], wire=blue)
    d.wire(psu.output["-"], q.coil["A2"], wire=blue)


def _spare_names(*, hide: bool) -> tuple[set[str], set[str]]:
    """The (drawn, spare) function names of Q1 and P9 after `without_unused` with `hide`."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _plant(d)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    inputs = read_inputs(model)
    every = (*inputs.functions, *inputs.spares)
    drawn, spares = without_unused(model, every, inputs.choices, hide=hide)
    tag_of = {one.id: one.key[-1] for one in items(model).values()}

    def names(specs) -> set[str]:
        return {
            f"{tag_of[functions(model)[s.function].item]}.{functions(model)[s.function].name}"
            for s in specs
            if s.function in functions(model)  # a box spec stands for an item
        } & {"Q1.aux", "Q1.aux_nc", "Q1.main", "P9.lamp"}

    return names(drawn), names(spares)


def test_an_unwired_contact_is_a_spare_with_the_switch_off_and_on() -> None:
    """The switch does not matter for a contact: Q1's three contact functions are all spares."""
    # UNDO: read/unused.py:without_unused, `or spec.roles.contact` removed
    for hide in (False, True):
        _, spares = _spare_names(hide=hide)
        assert {"Q1.aux", "Q1.main"} <= spares


def test_an_unwired_function_that_is_no_contact_stays_drawn_with_the_switch_off() -> None:
    """P9's lamp has no conductor: drawn with the switch off, a spare with it on."""
    # UNDO: read/unused.py:without_unused, `(hide or spec.roles.contact)` -> `unused`
    drawn_off, spares_off = _spare_names(hide=False)
    drawn_on, spares_on = _spare_names(hide=True)
    assert "P9.lamp" in drawn_off
    assert "P9.lamp" not in spares_off
    assert "P9.lamp" in spares_on
    assert "P9.lamp" not in drawn_on
