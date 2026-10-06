"""The author-side argument shapes `build` and `write` accept: a `Design`, a `Scope`."""

from fransys_author import Scope
from fransys_author.surface import Design

lazy from fransys_model.kernel import Draft

__all__ = ["Design", "Scope", "drafts_of"]


def drafts_of(items: tuple[Draft | Design, ...]) -> tuple[Draft, ...]:
    """The drafts `items` stand for: a `Design` gives its library then its own draft."""
    drafts: list[Draft] = []
    for item in items:
        if isinstance(item, Design):
            drafts.extend((item.library, item.draft()))
        else:
            drafts.append(item)
    return tuple(drafts)
