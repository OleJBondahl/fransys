"""The build's paper records: written once after `freeze()`, refused if authored (ST4)."""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

from fransys_model.kernel import Draft, Origin, SchemaError, evolve, make_id
from fransys_model.layout import PaperChoice, SheetFormat, layout_of

if TYPE_CHECKING:
    from fransys_model.kernel import Model

    from ._settings_merge import Table
    from .settings import Settings

__all__ = ["refuse_authored_paper", "with_paper"]

_KEY = ("build", "paper")
_CHOICE_KIND = "layout.paper"
_ORIGIN = Origin(file="fransys/_paper.py", line=0, note="the build's paper formats and choice")


def _number(table: Table, field: str) -> int:
    return int(cast("int", table[field]))


def _sheet(name: str, table: Table, module_mm: object) -> SheetFormat:
    """The `layout.sheet_format` record of format `name`, keyed by the name."""
    key = (*_KEY, name)

    return SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name=str(table["name"]),
        width_mm=_number(table, "width_mm"),
        height_mm=_number(table, "height_mm"),
        content_x_mm=_number(table, "content_x_mm"),
        content_y_mm=_number(table, "content_y_mm"),
        content_width_mm=_number(table, "content_width_mm"),
        content_height_mm=_number(table, "content_height_mm"),
        frame_columns=_number(table, "frame_columns"),
        frame_rows=_number(table, "frame_rows"),
        module_mm=Decimal(str(module_mm)),
    )


def _records(settings: Settings) -> tuple[SheetFormat | PaperChoice, ...]:
    """One sheet record per format the build uses, then the `PaperChoice`."""
    formats = cast("Table", settings.paper["formats"])
    default = str(settings.paper["default"])
    used = tuple(dict.fromkeys((default, *settings.paper_by_kind.values())))
    module = settings.grid["module_mm"]
    sheets = {name: _sheet(name, cast("Table", formats[name]), module) for name in used}
    by_kind = {kind.value: sheets[name].id for kind, name in settings.paper_by_kind.items()}
    choice = PaperChoice(
        id=make_id(PaperChoice, _KEY),
        key=_KEY,
        default=sheets[default].id,
        by_kind=frozendict(by_kind),
    )
    return (*sheets.values(), choice)


def _refusal(kind: str) -> SchemaError:
    msg = f"an input authors a {kind} record named for the build's paper: the facade writes it"
    return SchemaError(msg, kind=kind)


def _authored(record: object) -> str | None:
    """The kind of `record` when it is the facade's paper, else `None`."""
    if isinstance(record, PaperChoice):
        return _CHOICE_KIND
    if isinstance(record, SheetFormat) and record.key[:2] == _KEY:
        return "layout.sheet_format"
    return None


def refuse_authored_paper(draft: Draft) -> None:
    """Raise when the merged `draft` holds a `PaperChoice` or a sheet keyed `build/paper/<name>`."""
    for record in draft.records():
        if (kind := _authored(record)) is not None:
            raise _refusal(kind)


def with_paper(model: Model, settings: Settings) -> Model:
    """`model` with the paper records of `settings`; raises when it already carries a choice."""
    if layout_of(model, PaperChoice):
        raise _refusal(_CHOICE_KIND)
    return evolve(model, put=_records(settings), origin=_ORIGIN)
