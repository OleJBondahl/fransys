"""A name in an overview view is relative to the innermost opened unit that holds it (O3, A3)."""

from fold_builders import fold_plant
from overview_builders import item_id

from fransys_model.derive import overview_view_rows
from fransys_model.derive.instance_tag import unit_tag
from fransys_model.derive.lookups import unit_chain
from fransys_model.derive.overview_names import display_unit
from fransys_model.vocab.tables import units


def _texts(view) -> list[str]:
    boxes = [t for b in view.boxes for t in (*b.lines, *(b.tabs if hasattr(b, "tabs") else ()))]
    lines = [t for ln in view.lines for t in (ln.text, ln.tab_a, ln.tab_b) if t]
    return [*boxes, *lines]


def test_a_stub_for_an_item_of_an_opened_unit_names_it_without_that_units_tag() -> None:
    """At -U2 (in -U1) the stub for K1 reads `-K1`; breaks if stubs print absolute names."""
    model, outer, _far = fold_plant()
    (nested,) = [u for u, r in units(model).items() if r.parent == outer]
    views = overview_view_rows(model, nested)
    stubs = [b.lines[0] for v in views for b in v.boxes if b.key.at is not None]
    assert stubs
    assert set(stubs) == {"-K1"}


def test_no_text_of_any_view_starts_with_the_tag_of_an_opened_unit() -> None:
    """A3 over every printed text of every view: boxes, tabs, stubs and lines."""
    model, _outer, _far = fold_plant()
    checked = 0
    for unit in (None, *units(model)):
        opened = [] if unit is None else [unit_tag(model, u) for u in unit_chain(model, unit)]
        for view in overview_view_rows(model, unit):
            texts = _texts(view)
            checked += len(texts)
            wrong = [t for t in texts for tag in opened if tag and t.startswith(f"-{tag}-")]
            assert not wrong, (unit, wrong)
    assert checked


def test_display_unit_is_the_innermost_opened_unit_holding_the_item() -> None:
    """K1 is in -U1: viewed from -U2 it prints relative to -U1; a far unit's item does not."""
    model, outer, _far = fold_plant()
    (nested,) = [u for u, r in units(model).items() if r.parent == outer]
    assert display_unit(model, item_id("k1"), nested) == outer
    assert display_unit(model, item_id("z1"), nested) == nested
    assert display_unit(model, item_id("k1"), outer) == outer
    assert display_unit(model, item_id("f1"), nested) == nested
    assert display_unit(model, item_id("f1"), None) is None
