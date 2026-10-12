"""A render finding names its placement's page as a reference prints it, and its function."""

from dataclasses import replace

from fransys_render import check

from fransys_model.derive import function_designation
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import Page, SymbolPlacement, layout_of


def test_an_unknown_symbol_names_its_page_and_function(cabinet_laid_out) -> None:
    model = cabinet_laid_out
    placement = next(iter(layout_of(model, SymbolPlacement).values()))
    broken = evolve(
        model,
        remove=[placement.id],
        put=[replace(placement, symbol="no-such-symbol")],
        origin=Origin(file=__file__, line=1, note="test"),
    )
    (found,) = [f for f in check(broken) if f.subjects == (placement.function,)]
    page = layout_of(broken, Page)[placement.page]
    suffix = found.message.rsplit(" (", 1)[1]
    assert f"p{page.number}" in suffix
    assert suffix.endswith(f": {function_designation(broken, placement.function)})")
