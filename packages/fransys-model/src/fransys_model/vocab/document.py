"""Vocabulary: the authored document, a deliverable's definition (vocabulary.md, decision 0023)."""

from typing import Any, cast

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record

from .aspects import AspectNode
from .core import Item, Unit
from .enums import DocumentPreset, PageKind

_CANONICAL = tuple(PageKind)


def _canonical(found: object) -> tuple[PageKind, ...] | None:
    """`found` in canonical page order, or `None` if it is not a tuple of `PageKind`s."""
    if type(found) is not tuple or not all(type(kind) is PageKind for kind in found):
        return None
    return tuple(sorted(cast("tuple[PageKind, ...]", found), key=_CANONICAL.index))


@record(kind="document")
class Document:
    """The authored definition of one deliverable: a preset, a subject and its texts.

    Example: `Document(preset=CABINET_SCHEMATIC, location=<the +C1 node>, cover="# ...",
    notes=None, add=(), remove=())`. The subject is exactly one of `location`, `item` (a
    harness or a board), `unit` (a unit's own id) and `unit_name` (a `UnitRelease` name, plain
    text resolved by `derive.document_unit`); the `SYSTEM` preset has none. No page number,
    coordinate or layout reference is held; `layout.drawing_set` is found by location.
    `add` and `remove` are page kinds in canonical order, none twice; a kind in both is kept as
    authored and `remove` wins when pages resolve. `cover` is required; `notes` is `None` when
    dropped. The facade stores the Markdown text, so the PDF is a function of the model. `logo`
    is `None` or SVG text for the title block's logo cell, read like `cover` by `fr.document`.
    """

    id: Id[Document]
    key: AuthoringKey
    preset: DocumentPreset
    location: Id[AspectNode] | None
    item: Id[Item] | None
    add: tuple[PageKind, ...]
    remove: tuple[PageKind, ...]
    cover: str
    notes: str | None
    unit: Id[Unit] | None = None
    unit_name: str | None = None
    logo: str | None = None
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a subject not exactly one of `location`, `item`, `unit`, `unit_name`; order kinds.

        The `SYSTEM` preset is the one exception: it must have none of the four chosen.
        Anything that is not a tuple of `PageKind`s is left as it is: `freeze()` reports it.
        """
        holder: Id[Any] | None = self.id if type(self.id) is Id else None
        chosen = sum(
            subject is not None for subject in (self.location, self.item, self.unit, self.unit_name)
        )
        wanted = 0 if self.preset is DocumentPreset.SYSTEM else 1
        if chosen != wanted:
            msg = (
                "a document is about exactly one of a location, an item, a unit and a unit "
                f"release name, not {chosen}"
                if wanted == 1
                else f"the system document has no subject, not {chosen}"
            )
            raise SchemaError(msg, kind="document", record_id=holder)
        for name in ("add", "remove"):
            ordered = _canonical(getattr(self, name))
            if ordered is None:
                continue
            if len(set(ordered)) != len(ordered):
                msg = f"a document lists a page kind twice in {name}"
                raise SchemaError(msg, kind="document", record_id=holder)
            object.__setattr__(self, name, ordered)
