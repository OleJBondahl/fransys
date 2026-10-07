"""The layout records of one page, per kind, grouped once per model (RW2, decision model-0141)."""

from typing import Any, cast

from fransys_model.kernel import DIGEST_CACHE_SIZE, Model, digest_cached

from .harness_results import ConnectorBox, HarnessFanOut, HarnessLine
from .results import Label, LinkMarker, Outline, Page, PowerSymbol, Route, SymbolPlacement
from .tables import layout_of

_PAGE_KINDS: tuple[type[Any], ...] = (
    SymbolPlacement,
    PowerSymbol,
    Route,
    LinkMarker,
    Label,
    Outline,
    HarnessLine,
    ConnectorBox,
    HarnessFanOut,
)


@digest_cached(DIGEST_CACHE_SIZE)
def _slices(model: Model) -> dict[type, dict[Any, tuple[Any, ...]]]:
    """Per page-bound kind, per page id: its records sorted by id, grouped in one pass per kind."""
    out: dict[type, dict[Any, tuple[Any, ...]]] = {}
    for kind in _PAGE_KINDS:
        groups: dict[Any, list[Any]] = {}
        for record in layout_of(model, kind).values():
            groups.setdefault(record.page, []).append(record)
        out[kind] = {
            page: tuple(sorted(records, key=lambda record: record.id))
            for page, records in groups.items()
        }
    return out


def page_slice[R](model: Model, record_type: type[R], page: Page) -> tuple[R, ...]:
    """Every `record_type` record on `page`, ordered by id; empty when there are none.

    `record_type` is one of the page-bound layout kinds: `SymbolPlacement`, `PowerSymbol`,
    `Route`, `LinkMarker`, `Label`, `Outline`, `HarnessLine`, `ConnectorBox` or `HarnessFanOut`.
    The grouping is built once per model digest (`digest_cached`), so reading every page costs
    one pass over each table, not one per page.

    Raises:
        KeyError: `record_type` is not a page-bound kind.
    """
    return cast("tuple[R, ...]", _slices(model)[record_type].get(page.id, ()))
