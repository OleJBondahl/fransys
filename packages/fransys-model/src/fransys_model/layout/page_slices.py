"""The layout records of one page, per kind, grouped once per model (decision model-0141)."""

from typing import Any, cast

from fransys_model.kernel import DIGEST_CACHE_SIZE, Model, digest_cached

from .membership import Membership
from .results import LinkMarker, Page, PowerSymbol
from .tables import layout_of

_PAGE_KINDS: tuple[type[Any], ...] = (
    PowerSymbol,
    LinkMarker,
    Membership,
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

    `record_type` is one of the page-bound layout kinds: `PowerSymbol`, `LinkMarker`
    or `Membership`.
    The grouping is built once per model digest (`digest_cached`), so reading every page costs
    one pass over each table, not one per page.

    Raises:
        KeyError: `record_type` is not a page-bound kind.
    """
    return cast("tuple[R, ...]", _slices(model)[record_type].get(page.id, ()))


def page_members(model: Model, page: Page) -> tuple[Membership, ...]:
    """The `Membership` rows that put a subject on `page`, in reading `rank` order.

    A rank is unique on a page, so the order is read off by rank, with no sort.
    """
    by_rank = {row.rank: row for row in page_slice(model, Membership, page)}
    return tuple(by_rank[rank] for rank in range(max(by_rank, default=-1) + 1) if rank in by_rank)
