"""`check` (D12): `UNKNOWN_SYMBOL_KEY`, `LIBRARY_VERSION_MISMATCH`, `LAYOUT_MISSING`.

`PIN_MAP_INCOMPLETE` is not render's check any more (decision layout-0041): it lives in
`fransys_layout.stages.resolve`.
"""

from dataclasses import replace

from fransys_render import check
from fransys_render._symbol_geometry import oriented_symbol
from fransys_render.check import LAYOUT_MISSING, LIBRARY_VERSION_MISMATCH, UNKNOWN_SYMBOL_KEY

from electrical_symbols import library_version
from fransys_model.kernel import Draft, Origin, Severity, evolve, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    Orientation,
    Page,
    PageRole,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab import Function, FunctionKind, Item, Port, PortRole

_ORIGIN = Origin(file="packages/fransys-render/tests/test_check.py", line=1, note="invented")

_REAL_KEY = "make-contact"
_BOGUS_KEY = "no-such-symbol-key"
_STALE_VERSION = "stale-version-string"


def _model(*records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _drawing_set(key_part, *, number=1):
    key = ("drawing_set", key_part)
    return DrawingSet(
        id=make_id(DrawingSet, key), key=key, location=None, number=number, produced_by="test"
    )


def _page(key_part, *, drawing_set, number=1):
    key = ("page", key_part)
    return Page(
        id=make_id(Page, key),
        key=key,
        drawing_set=drawing_set.id,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=None,
        groups=(),
        produced_by="test",
    )


def _pin(key_part, designation):
    """A bare item/function/port, one pin (mirrors `test_markers.py:_pin`)."""
    item_key = ("item", key_part)
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag=designation,
        description="Invented",
    )
    function_key = ("function", key_part)
    fn = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    port_key = (*function_key, "1")
    port = Port(
        id=make_id(Port, port_key),
        key=port_key,
        function=fn.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    return item, fn, port


def _placement(  # noqa: PLR0913 -- one keyword per field
    key_part, *, function, page, symbol, library_version_value, x=0, y=0
):
    key = ("symbol_placement", key_part)
    return SymbolPlacement(
        id=make_id(SymbolPlacement, key),
        key=key,
        function=function.id,
        page=page.id,
        x=x,
        y=y,
        orientation=Orientation.R0,
        poles=1,
        symbol=symbol,
        library_version=library_version_value,
        produced_by="test",
    )


# --- 1. UNKNOWN_SYMBOL_KEY: fires for a bogus key, not for a real one ---------------------------


def test_unknown_symbol_key_fires_and_clean_twin_does_not():
    drawing_set = _drawing_set("t1")
    page = _page("t1", drawing_set=drawing_set)
    _bogus_item, bogus_fn, _bogus_port = _pin("t1-bogus", "K1")
    _clean_item, clean_fn, _clean_port = _pin("t1-clean", "K2")
    bogus = _placement(
        "t1-bogus",
        function=bogus_fn,
        page=page,
        symbol=_BOGUS_KEY,
        library_version_value=library_version(),
    )
    clean = _placement(
        "t1-clean",
        function=clean_fn,
        page=page,
        symbol=_REAL_KEY,
        library_version_value=library_version(),
    )
    model = _model(
        drawing_set,
        page,
        _bogus_item,
        bogus_fn,
        _bogus_port,
        bogus,
        _clean_item,
        clean_fn,
        _clean_port,
        clean,
    )

    # The clean twin really does resolve via `oriented_symbol` -- so the assertion below
    # that it triggers no finding cannot pass by accident on a broken lookup.
    assert oriented_symbol(model, clean) is not None

    findings = check(model)
    unknown = [f for f in findings if f.code == UNKNOWN_SYMBOL_KEY]
    assert len(unknown) == 1
    assert unknown[0].subjects == (bogus_fn.id,)
    assert unknown[0].severity is Severity.ERROR
    assert not any(f.code == UNKNOWN_SYMBOL_KEY and f.subjects == (clean_fn.id,) for f in findings)


# --- 2. LIBRARY_VERSION_MISMATCH: fires for a stale version, not for a matching one -------------


def test_library_version_mismatch_fires_and_clean_twin_does_not():
    drawing_set = _drawing_set("t2")
    page = _page("t2", drawing_set=drawing_set)
    _stale_item, stale_fn, _stale_port = _pin("t2-stale", "K1")
    _clean_item, clean_fn, _clean_port = _pin("t2-clean", "K2")
    stale = _placement(
        "t2-stale",
        function=stale_fn,
        page=page,
        symbol=_REAL_KEY,
        library_version_value=_STALE_VERSION,
    )
    clean = _placement(
        "t2-clean",
        function=clean_fn,
        page=page,
        symbol=_REAL_KEY,
        library_version_value=library_version(),
    )
    model = _model(
        drawing_set,
        page,
        _stale_item,
        stale_fn,
        _stale_port,
        stale,
        _clean_item,
        clean_fn,
        _clean_port,
        clean,
    )

    findings = check(model)
    mismatch = [f for f in findings if f.code == LIBRARY_VERSION_MISMATCH]
    assert len(mismatch) == 1
    assert mismatch[0].subjects == (stale_fn.id,)
    assert mismatch[0].severity is Severity.WARNING
    assert not any(
        f.code == LIBRARY_VERSION_MISMATCH and f.subjects == (clean_fn.id,) for f in findings
    )


def test_library_version_mismatch_is_skipped_when_key_is_already_unknown():
    """A placement with both a bogus key and a stale version gives only UNKNOWN_SYMBOL_KEY."""
    drawing_set = _drawing_set("t3")
    page = _page("t3", drawing_set=drawing_set)
    _item, fn, _port = _pin("t3", "K1")
    placement = _placement(
        "t3", function=fn, page=page, symbol=_BOGUS_KEY, library_version_value=_STALE_VERSION
    )
    model = _model(drawing_set, page, _item, fn, _port, placement)

    findings = check(model)
    assert len(findings) == 1
    assert findings[0].code == UNKNOWN_SYMBOL_KEY
    assert not any(f.code == LIBRARY_VERSION_MISMATCH for f in findings)


# --- 3. LAYOUT_MISSING: functions with no page fires; a page, or no functions, does not ---------


def test_layout_missing_fires_for_functions_with_no_page():
    _item, fn, port = _pin("t4", "K1")
    model = _model(_item, fn, port)

    findings = check(model)
    assert len(findings) == 1
    assert findings[0].code == LAYOUT_MISSING
    assert findings[0].subjects == ()
    assert findings[0].severity is Severity.ERROR


def test_layout_missing_does_not_fire_with_at_least_one_page():
    drawing_set = _drawing_set("t5")
    page = _page("t5", drawing_set=drawing_set)
    _item, fn, port = _pin("t5", "K1")
    model = _model(drawing_set, page, _item, fn, port)

    findings = check(model)
    assert not any(f.code == LAYOUT_MISSING for f in findings)


def test_layout_missing_does_not_fire_with_no_functions_and_no_pages():
    model = _model()

    findings = check(model)
    assert findings == ()


# --- 4. Real-data regression: neither golden triggers any of the three codes --------------------


def test_goldens_trigger_none_of_the_three_codes(cabinet_laid_out, cabinet_narrow_laid_out):
    codes = {UNKNOWN_SYMBOL_KEY, LIBRARY_VERSION_MISMATCH, LAYOUT_MISSING}
    for model in (cabinet_laid_out, cabinet_narrow_laid_out):
        findings = check(model)
        assert not any(f.code in codes for f in findings)


def test_a_golden_placement_with_a_real_mismatch_still_fires(cabinet_laid_out):
    """`conftest.py`'s `_with_installed_library_version` normalises the golden fixture to the
    currently-installed version so a release does not spuriously trip this check (decision
    layout-0046) -- proof that normalisation does not also swallow a genuine mismatch: one
    placement's `library_version`, set here to a value that provably differs from installed,
    still fires `LIBRARY_VERSION_MISMATCH` for exactly that placement.
    """
    placement_id, placement = next(iter(layout_of(cabinet_laid_out, SymbolPlacement).items()))
    stale = replace(placement, library_version=_STALE_VERSION)
    mutated = evolve(cabinet_laid_out, remove=(placement_id,), put=(stale,), origin=_ORIGIN)

    findings = check(mutated)
    mismatch = [f for f in findings if f.code == LIBRARY_VERSION_MISMATCH]
    assert len(mismatch) == 1
    assert mismatch[0].subjects == (placement.function,)
