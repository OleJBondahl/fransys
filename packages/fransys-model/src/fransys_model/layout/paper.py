"""The record of the paper a build draws on: the default format and one per drawing type (ST4)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record

from .formats import SheetFormat


@record(kind="layout.paper", singleton=True)
class PaperChoice:
    """Which sheet a page is drawn on when it names none, written once by the facade.

    `default` is the format a page of any kind takes; `by_kind` names another format for one
    `PageKind` (keyed by its `value`). Each is the `Id` of a `layout.sheet_format` record the
    facade wrote, keyed by the format's name. The facade writes it after `freeze()` and before
    any pass; an input never authors it and no pass removes it. `sheet_for` reads it (model-0312).
    """

    id: Id[PaperChoice]
    key: AuthoringKey
    default: Id[SheetFormat]
    by_kind: frozendict[str, Id[SheetFormat]] = frozendict()
    ext: frozendict[str, Value] = frozendict()
