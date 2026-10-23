"""The record of the paper a build draws on: the default format and one per drawing type (ST4)."""

lazy from collections.abc import Mapping
lazy from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, Value, make_id, record

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


def sheet_format_record(
    key: AuthoringKey, name: str, numbers: Mapping[str, int], module_mm: Decimal
) -> SheetFormat:
    """A `SheetFormat` of `key` named `name`; `numbers` holds its other whole-mm and grid fields.

    The keys of `numbers` are the record's own: `width_mm`, `height_mm`, `content_x_mm`,
    `content_y_mm`, `content_width_mm`, `content_height_mm`, `frame_columns`, `frame_rows`.
    The facade writes one per paper format the build uses.
    """
    return SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name=name,
        width_mm=numbers["width_mm"],
        height_mm=numbers["height_mm"],
        content_x_mm=numbers["content_x_mm"],
        content_y_mm=numbers["content_y_mm"],
        content_width_mm=numbers["content_width_mm"],
        content_height_mm=numbers["content_height_mm"],
        frame_columns=numbers["frame_columns"],
        frame_rows=numbers["frame_rows"],
        module_mm=module_mm,
    )


def paper_choice(
    key: AuthoringKey, *, default: Id[SheetFormat], by_kind: Mapping[str, Id[SheetFormat]]
) -> PaperChoice:
    """The `PaperChoice` of `key`: the default sheet and one per `PageKind` value."""
    return PaperChoice(
        id=make_id(PaperChoice, key), key=key, default=default, by_kind=frozendict(by_kind)
    )
