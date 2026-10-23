"""The two questions pdf asks of a page kind, both read from `derive.page_preset` (pdf-0052)."""

from typing import TYPE_CHECKING

from fransys_model.derive import PageForm, page_preset

if TYPE_CHECKING:
    from fransys_model.vocab import PageKind

__all__ = ["has_form", "list_pages"]


def has_form(pages: tuple[PageKind, ...], form: PageForm) -> bool:
    """True when a page of `form` stands in `pages`."""
    return any(page_preset(kind).form is form for kind in pages)


def list_pages(pages: tuple[PageKind, ...]) -> tuple[PageKind, ...]:
    """The list kinds of `pages` (those with a `ListKey`), in `pages` order."""
    return tuple(kind for kind in pages if page_preset(kind).list_key is not None)
