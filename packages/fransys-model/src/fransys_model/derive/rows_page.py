"""The row shape of a page kind's preset (model-0311)."""

from fransys_model.kernel import value
from fransys_model.vocab.enums import PageKind
from fransys_model.vocab.page_forms import ListKey, PageForm

__all__ = ["ListKey", "PageForm", "PagePreset"]


@value
class PagePreset:
    """What a page kind is: the `form` its builder takes, its `list_key`, whether it frames itself.

    `list_key` is set for the seven list kinds and `None` otherwise. A `self_framed` page sets its
    own page frame; every other page gets the section margin and background.
    """

    kind: PageKind
    form: PageForm
    list_key: ListKey | None
    self_framed: bool
