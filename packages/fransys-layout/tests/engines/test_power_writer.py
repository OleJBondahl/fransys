"""D5 step 6: the writer turns a power end into a `PowerSymbol` and a `MARKING` label, no marker.

On the invented plant of `power_fixture` on a 60 mm sheet: eleven power ends on four pages.
A flagged end writes no `LinkMarker`; the model's tables and the derived-ids clear path know the
new record kind, so a rerun over the written model replaces the symbols instead of piling up.
"""

from functools import cache
from typing import TYPE_CHECKING

from power_fixture import power_model, power_run

from fransys_layout.engines import lay_out_schematic
from fransys_layout.stages.texts.power import power_places
from fransys_model.derive.drawing_text import label_text
from fransys_model.layout import (
    POWER_SLOT,
    Label,
    LabelKind,
    LinkMarker,
    Orientation,
    Page,
    PowerSymbol,
    derived_layout_ids,
    layout_of,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Model


@cache
def _written() -> Model:
    return lay_out_schematic(power_model(60))[0]


def _places():
    return power_places(power_run()[2].layout.markers)


def test_one_power_symbol_per_power_end_on_its_port_and_page() -> None:
    """UNDO: in `write_layout` drop `power_symbols(...)` from the records."""
    records = list(layout_of(_written(), PowerSymbol).values())
    assert len(records) == len(_places()) == 11
    assert sorted((r.port, r.symbol, r.x, r.y) for r in records) == sorted(
        (p.port, p.symbol, p.at.x, p.at.y) for p in _places()
    )
    assert {r.symbol for r in records} == {"power-supply", "ground", "protective-earth"}
    assert all(isinstance(r.orientation, Orientation) for r in records)


def test_each_symbol_is_on_the_page_of_its_end() -> None:
    """UNDO: in `power_symbols` write `page_of[1, 1]` for every symbol."""
    model = _written()
    pages = layout_of(model, PowerSymbol)
    by_page = {r.page for r in pages.values()}
    assert len(by_page) == 4
    sets = layout_of(model, Page)
    wanted = sorted(
        (p.port, sets[r.page].number) for p in _places() for r in [pages[_id(p, pages)]]
    )
    assert wanted == sorted((p.port, p.page) for p in _places())


def _id(place, pages):
    """The id of the written symbol standing on `place`'s port and position."""
    return next(
        i for i, r in pages.items() if (r.port, r.x, r.y) == (place.port, place.at.x, place.at.y)
    )


def test_a_power_end_writes_no_link_marker() -> None:
    """UNDO: in `link_markers` (write) read `results.layout` instead of `without_power(...)`."""
    flagged = {p.port for p in _places()}
    markers = layout_of(_written(), LinkMarker).values()
    assert not flagged & {m.port for m in markers}


def test_each_symbol_with_a_text_has_a_marking_label_on_its_port() -> None:
    """UNDO: in `with_power_labels` return `labels, ()`: the symbols print nothing."""
    labels = [r for r in layout_of(_written(), Label).values() if r.slot == POWER_SLOT]
    wanted = sorted(p.port for p in _places() if p.text)
    assert wanted
    assert sorted(r.port for r in labels if r.port is not None) == wanted
    assert all(r.port is not None for r in labels)
    assert {r.kind for r in labels} == {LabelKind.MARKING}
    assert all(r.function is None and r.conductor is None for r in labels)


def test_the_stage_labels_carry_the_models_power_slot() -> None:
    """UNDO: in `stages/texts/power.py` set `slot="x"` on the `PlacedLabel`: the slots differ."""
    labels = power_run()[2].layout.labels
    wanted = {p.port for p in _places() if p.text}
    assert wanted
    assert {r.subject for r in labels if r.slot == POWER_SLOT} == wanted


def test_a_power_label_prints_the_power_text_not_the_port_marking() -> None:
    """UNDO: in `label_text` drop the `POWER_SLOT` branch: the label prints the port marking."""
    model = _written()
    wanted = {p.port: p.text for p in _places() if p.text}
    labels = [r for r in layout_of(model, Label).values() if r.slot == POWER_SLOT]
    assert labels
    assert {r.port: label_text(model, r) for r in labels} == wanted


def test_a_rerun_over_the_written_model_gives_the_same_symbols() -> None:
    """The derived-ids clear path knows `layout.power_symbol`: a second run replaces, not adds.

    UNDO: in `derived_layout_ids` leave out the power symbol table.
    """
    once = _written()
    twice, _ = lay_out_schematic(once)
    assert set(layout_of(twice, PowerSymbol)) == set(layout_of(once, PowerSymbol))
    assert set(derived_layout_ids(once)) >= set(layout_of(once, PowerSymbol))
