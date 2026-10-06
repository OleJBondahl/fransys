"""WP18 tests: the layout namespace in a frozen model (design/kernel-records.md 5.3,
design/kernel-model.md 5.6, design/layout-namespace.md)."""

import pytest
from layout_examples import drawing_set, drawn_function, group_node, page, placement, sheet_format

from fransys_model.kernel import (
    AuthoringKey,
    Draft,
    FreezeError,
    Id,
    Model,
    Origin,
    Record,
    SchemaError,
    Value,
    field_specs,
    freeze,
    record,
)
from fransys_model.layout import Page, SymbolPlacement, derived_layout_ids, layout_of
from fransys_model.vocab.core import Item


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_namespace.py", line=1, note="fixture")
    draft.extend(records, origin=origin)
    return freeze(draft)


def _laid_out(*, x: int) -> Model:
    return _freeze(
        (*drawn_function(), group_node(), sheet_format(), drawing_set(), page(), placement(x=x))
    )


def test_moving_a_symbol_changes_only_the_layout_digest() -> None:
    """Two models differing in one `SymbolPlacement.x` differ in `digests["layout"]` alone."""
    before, after = _laid_out(x=64), _laid_out(x=128)
    assert before.digests["layout"] != after.digests["layout"]
    assert before.digests["core"] == after.digests["core"]
    assert before.digests["facet"] == after.digests["facet"]
    assert before.digest != after.digest


def test_core_kind_referencing_a_layout_kind_is_rejected() -> None:
    """A `core` record type with an `Id[Page]` field fails when its field specs are built."""

    @record(kind="looks_up")
    class LooksUp:
        id: Id[LooksUp]
        key: AuthoringKey
        page: Id[Page]
        ext: frozendict[str, Value] = frozendict()

    with pytest.raises(SchemaError):
        field_specs(LooksUp)


def test_layout_kind_referencing_a_core_kind_is_accepted() -> None:
    """`SymbolPlacement.function` points down into `core`, which is allowed."""
    refs = {spec.name: spec.ref_kind for spec in field_specs(SymbolPlacement)}
    assert refs["function"] == "function"
    assert refs["page"] == "layout.page"


def test_placement_of_a_missing_function_is_a_freeze_error() -> None:
    """A layout record whose engineering subject is absent dangles like any reference."""
    with pytest.raises(FreezeError):
        _freeze((group_node(), sheet_format(), drawing_set(), page(), placement()))


def test_layout_of_returns_the_records_of_one_kind() -> None:
    """`layout_of(model, Page)` returns exactly the pages, keyed by id."""
    model = _laid_out(x=64)
    assert set(layout_of(model, Page)) == {page().id}


def test_layout_of_refuses_a_class_not_in_the_layout_namespace() -> None:
    """`layout_of` is `layout`-kinds only; a `core` class raises naming its own kind."""
    model = _laid_out(x=64)
    with pytest.raises(SchemaError) as excinfo:
        layout_of(model, Item)
    assert excinfo.value.kind == "item"


def test_derived_layout_ids_excludes_authored_kinds() -> None:
    """The sheet format is authored, so it is not among the ids a pass replaces."""
    model = _laid_out(x=64)
    assert set(derived_layout_ids(model)) == {drawing_set().id, page().id, placement().id}
    assert sheet_format().id not in derived_layout_ids(model)
