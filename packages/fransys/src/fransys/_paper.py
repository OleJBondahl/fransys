"""The build's paper records: written once after `freeze()`, refused if authored (ST4)."""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

from fransys_model.kernel import Draft, Origin, SchemaError, evolve
from fransys_model.layout import (
    PaperChoice,
    SheetFormat,
    layout_of,
    paper_choice,
    sheet_format_record,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Model

    from ._settings_merge import Table
    from .settings import Settings

__all__ = ["refuse_authored_paper", "with_paper"]

_KEY = ("build", "paper")
_CHOICE_KIND = "layout.paper"
_ORIGIN = Origin(file="fransys/_paper.py", line=0, note="the build's paper formats and choice")


def _sheet(name: str, table: Table, module_mm: object) -> SheetFormat:
    """The `layout.sheet_format` record of format `name`, keyed by the name."""
    numbers = {k: int(cast("int", v)) for k, v in table.items() if k != "name"}
    return sheet_format_record((*_KEY, name), str(table["name"]), numbers, Decimal(str(module_mm)))


def _records(settings: Settings) -> tuple[SheetFormat | PaperChoice, ...]:
    """One sheet record per format the build uses, then the `PaperChoice`."""
    formats = cast("Table", settings.paper["formats"])
    default = str(settings.paper["default"])
    used = tuple(dict.fromkeys((default, *settings.paper_by_kind.values())))
    module = settings.grid["module_mm"]
    sheets = {name: _sheet(name, cast("Table", formats[name]), module) for name in used}
    by_kind = {kind.value: sheets[name].id for kind, name in settings.paper_by_kind.items()}
    choice = paper_choice(_KEY, default=sheets[default].id, by_kind=by_kind)
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
