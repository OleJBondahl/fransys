"""The set of exports a write makes and the patterns of the ones it owns (model-0283, R25).

A function of the model and the unit alone: `write` zips the rows with its producers, and a
stale-file sweep reads the patterns from the same kind table, so the two never drift apart.
"""

from typing import Any

from fransys_model.vocab.tables import documents, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .document_unit import document_unit
from .export_names import document_export_name, export_name, export_ref, export_set_name
from .reports import unit_boards, unit_strips
from .rows_export_set import ExportRow
from .structure import boards
from .unit_racks import unit_racks
from .wiring import terminal_strips

__all__ = ["export_set", "stale_patterns"]

# (kind, extension, stale pattern) of the whole-model reports; `wires` also matches older names.
_REPORTS = (
    ("bom", "csv", "bom.csv"),
    ("plc", "csv", "plc.csv"),
    ("wires", "csv", "wire*.csv"),
    ("designations", "csv", "designations.csv"),
    ("cables", "csv", "cables.csv"),
    ("cores", "csv", "cores.csv"),
)
_OVERVIEW = ("overview", "html", "overview.html")
# (kind, extension) of the per-item exports: `<kind>-<ref>.<ext>`, bare `<kind>.<ext>` for a root.
_ITEMS = (("terminals", "csv"), ("connectors", "csv"), ("wago", "xml"))


def stale_patterns() -> tuple[str, ...]:
    """The top-level file patterns a write owns and sweeps: every kind of `export_set`.

    Per-item kinds give `<kind>-*.<ext>` and the bare `<kind>.<ext>`; PDFs are `*.pdf`.
    """
    items = tuple(p for kind, ext in _ITEMS for p in (f"{kind}-*.{ext}", f"{kind}.{ext}"))
    return ("*.pdf", *(pattern for _kind, _ext, pattern in _REPORTS), *items, _OVERVIEW[2])


def _report_rows(model: Model, unit: Id[Unit] | None) -> list[ExportRow]:
    rows = [(kind, ext) for kind, ext, _pattern in _REPORTS]
    if unit is None:
        rows.append(_OVERVIEW[:2])
    return [
        ExportRow(
            export_kind=kind,
            extension=ext,
            subject=None,
            name=export_name(model, unit, ext, kind=kind),
            hint=None,
        )
        for kind, ext in rows
    ]


def _item_subjects(
    model: Model, unit: Id[Unit] | None
) -> tuple[tuple[Id[Item], ...], tuple[Id[Item], ...], tuple[Id[Item], ...]]:
    """The strips, boards and racks of `unit` (all of them with `unit=None`)."""
    racks = unit_racks(model, unit)
    if unit is None:
        return terminal_strips(model), boards(model), racks
    return unit_strips(model, unit), unit_boards(model, unit), racks


def _item_rows(model: Model, unit: Id[Unit] | None) -> list[ExportRow]:
    by_kind = dict(zip((kind for kind, _ext in _ITEMS), _item_subjects(model, unit), strict=True))
    return [
        ExportRow(
            export_kind=kind,
            extension=ext,
            subject=item,
            name=export_name(model, unit, ext, kind=kind, fragment=export_ref(model, item, unit)),
            hint=None,
        )
        for kind, ext in _ITEMS
        for item in by_kind[kind]
    ]


def _clash_hint(
    model: Model, own_unit: Id[Unit] | None, name: str, release_by_name: dict[str, Id[Any]]
) -> str | None:
    """The unit-set name when `name` is already taken by a document of the same release, else None.

    Records `name`'s release in `release_by_name`.
    """
    if own_unit is None:
        return None
    release_id = units(model)[own_unit].release
    seen = release_by_name.get(name) == release_id
    release_by_name[name] = release_id
    return export_set_name(model, own_unit) if seen else None


def _document_rows(model: Model, unit: Id[Unit] | None) -> list[ExportRow]:
    """One PDF per document of `unit` (every document with `unit=None`).

    The hint is set only when the name was already taken by a document of the SAME release
    (`Unit.release` id, never a name compare), so an ordinary clash gets none.
    """
    entries = documents(model).items()
    if unit is not None:
        entries = [(i, r) for i, r in entries if document_unit(model, r.id) == unit]
    release_by_name: dict[str, Id[Any]] = {}
    rows = []
    for document_id, record in entries:
        name = document_export_name(model, unit, record)
        own_unit = document_unit(model, record.id)
        hint = _clash_hint(model, own_unit, name, release_by_name)
        rows.append(
            ExportRow(export_kind="pdf", extension="pdf", subject=document_id, name=name, hint=hint)
        )
    return rows


def export_set(model: Model, unit: Id[Unit] | None) -> tuple[ExportRow, ...]:
    """Every export a write of `unit` makes (the whole model with `unit=None`), in write order.

    The reports (and the overview for the whole model), one terminal CSV per strip, one connector
    CSV per board, one WAGO XML per rack, then one PDF per document. Names are unplaced: the
    caller puts CSV and XML into `data/`. Two rows may share a name; the caller refuses that.
    """
    return (*_report_rows(model, unit), *_item_rows(model, unit), *_document_rows(model, unit))
