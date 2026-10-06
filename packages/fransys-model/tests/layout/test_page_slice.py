"""`page_slice`: one digest-cached grouping of the page-bound layout kinds (decision model-0141)."""

from dataclasses import replace

import pytest
from test_namespace import _laid_out

from fransys_model.layout import Page, PowerSymbol, Route, SymbolPlacement, layout_of, page_slice
from fransys_model.layout.page_slices import _slices


def test_the_slice_holds_the_pages_records() -> None:
    model = _laid_out(x=64)
    (page,) = layout_of(model, Page).values()
    (placement,) = layout_of(model, SymbolPlacement).values()
    assert page_slice(model, SymbolPlacement, page) == (placement,)


def test_a_kind_with_no_records_and_a_page_without_records_are_empty() -> None:
    model = _laid_out(x=64)
    (page,) = layout_of(model, Page).values()
    assert page_slice(model, Route, page) == ()
    assert (
        page_slice(model, SymbolPlacement, replace(page, id=replace(page.id, value="e" * 32))) == ()
    )


def test_a_kind_that_is_not_page_bound_is_refused() -> None:
    model = _laid_out(x=64)
    (page,) = layout_of(model, Page).values()
    with pytest.raises(KeyError):
        page_slice(model, Page, page)


def test_one_build_serves_every_kind_and_page() -> None:
    model = _laid_out(x=64)
    (page,) = layout_of(model, Page).values()
    _slices.cache_clear()
    page_slice(model, SymbolPlacement, page)
    page_slice(model, PowerSymbol, page)
    page_slice(model, Route, page)
    assert _slices.builds == 1
