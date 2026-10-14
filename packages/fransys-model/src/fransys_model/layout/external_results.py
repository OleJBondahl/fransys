"""The result record of an item supplied by others on a schematic page (OUTLINES BO7)."""

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record
from fransys_model.vocab.core import Item

from .order import holder_of
from .results import Page


@record(kind="layout.external_outline")
class ExternalOutline:
    """The dashed outline round one run of an external item's symbols on one page.

    `item` is the external root, the outermost item flagged `external`. `x`, `y` is the
    rectangle's top-left corner, `width`/`height` its size, in G. Layout works it out from the
    run's bodies and measured labels; render draws it dashed and measures nothing. The page
    holds the drawing set, as it does for `Outline`. The "by others" note is an ordinary
    `layout.label`, slot `"external_note"`.
    """

    id: Id[ExternalOutline]
    key: AuthoringKey
    item: Id[Item]
    page: Id[Page]
    x: int
    y: int
    width: int
    height: int
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a non-positive `width` or `height`."""
        holder = holder_of(self)
        if type(self.width) is int and self.width <= 0:
            msg = f"an external outline's width must be positive, got {self.width}"
            raise SchemaError(msg, kind="layout.external_outline", record_id=holder)
        if type(self.height) is int and self.height <= 0:
            msg = f"an external outline's height must be positive, got {self.height}"
            raise SchemaError(msg, kind="layout.external_outline", record_id=holder)
