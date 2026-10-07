"""One page's tag rules over its own slices (S10)."""

from typing import TYPE_CHECKING

from .tags import TagTexts, one_item_tag, pin_labels, unit_texts

if TYPE_CHECKING:
    from .types import Column, FunctionSpec, LabelRequest, PagePlan


def _page_requests(
    texts: TagTexts,
    plan: PagePlan,
    columns: tuple[Column, ...],
    specs: tuple[FunctionSpec, ...],
    requests: tuple[LabelRequest, ...],
) -> tuple[LabelRequest, ...]:
    """The page's tag rules over its own slices: the pin decision, one item tag, unit texts."""
    return unit_texts(
        texts,
        plan,
        one_item_tag(columns, specs, pin_labels(texts, requests, columns, specs)),
        specs,
    )
