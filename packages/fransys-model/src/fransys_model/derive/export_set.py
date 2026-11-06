"""The set of exports a write makes and the patterns of the ones it owns (model-0283, R25).

A function of the model and the unit alone: `write` zips the rows with its producers, and a
stale-file sweep reads the patterns from the same kind table, so the two never drift apart.
"""

from typing import Any

from fransys_model.vocab.tables import documents, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit

from .document_unit import document_unit
from .export_names import document_export_name, export_name, export_ref, export_set_name
from .facts.house_settings import export_form_of
from .report_scope import terminal_strips, unit_boards, unit_strips
from .rows_export_set import ExportRow
from .structure import boards
from .unit_racks import unit_racks

__all__ = ["REPORT_KINDS", "export_set", "stale_patterns"]

# Per kind of the whole-model reports, its (extension, stale pattern); `wires` also matches older
# names. `[export] reports` names the kinds a write makes; the sweep owns all of them.
_REPORTS = {
    "bom": ("csv", "bom.csv"),
    "plc": ("csv", "plc.csv"),
    "wires": ("csv", "wire*.csv"),
    "designations": ("csv", "designations.csv"),
    "cables": ("csv", "cables.csv"),
    "cores": ("csv", "cores.csv"),
}
REPORT_KINDS: tuple[str, ...] = tuple(_REPORTS)
_OVERVIEW = ("overview", "html", "overview.html")
# (kind, extension) of the per-rack export: `wago-<ref>.xml`, bare `wago.xml` for a root.
_ITEMS = (("wago", "xml"),)
# The lists of every strip and of every board, each one file per write (model-0437).
_LISTS = ("terminals", "connectors")


def stale_patterns() -> tuple[str, ...]:
    """The top-level file patterns a write owns and sweeps: every kind of `export_set`.

    The lists give `<kind>.csv`, and `<kind>-*.csv` still so a release deletes the old per-strip and
    per-board files; the per-rack kind gives `<kind>-*.<ext>` and the bare name; PDFs are `*.pdf`.
    """
    lists = tuple(p for kind in _LISTS for p in (f"{kind}-*.csv", f"{kind}.csv"))
    items = tuple(p for kind, ext in _ITEMS for p in (f"{kind}-*.{ext}", f"{kind}.{ext}"))
    return ("*.pdf", *(pattern for _ext, pattern in _REPORTS.values()), *lists, *items, _OVERVIEW[2])


def _report_rows(model: Model, unit: Id[Unit] | None) -> list[ExportRow]:
    rows = [(kind, _REPORTS[kind][0]) for kind in export_form_of(model).reports]
    if unit is None:
        rows.append(_OVERVIEW[:2])
    return [_whole_row(model, unit, kind, ext) for kind, ext in rows]


def _whole_row(model: Model, unit: Id[Unit] | None, kind: str, ext: str) -> ExportRow:
    return ExportRow(export_kind=kind, extension=ext, subject=None, name=export_name(model, unit, ext, kind=kind), hint=None)


def _list_rows(model: Model, unit: Id[Unit] | None) -> list[ExportRow]:
    """`terminals` when `unit` (the whole model with `None`) has a strip, `connectors` when it has a board."""
    subjects = (terminal_strips(model), boards(model)) if unit is None else (unit_strips(model, unit), unit_boards(model, unit))
    return [_whole_row(model, unit, kind, "csv") for kind, found in zip(_LISTS, subjects, strict=True) if found]


def _item_rows(model: Model, unit: Id[Unit] | None) -> list[ExportRow]:
    return [
        ExportRow(
            export_kind=kind,
            extension=ext,
            subject=rack,
            name=export_name(model, unit, ext, kind=kind, fragment=export_ref(model, rack, unit)),
            hint=None,
        )
        for kind, ext in _ITEMS
        for rack in unit_racks(model, unit)
    ]


def _clash_hint(model: Model, own_unit: Id[Unit] | None, name: str, release_by_name: dict[str, Id[Any]]) -> str | None:
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
        rows.append(ExportRow(export_kind="pdf", extension="pdf", subject=document_id, name=name, hint=hint))
    return rows


def export_set(model: Model, unit: Id[Unit] | None) -> tuple[ExportRow, ...]:
    """Every export a write of `unit` makes (the whole model with `unit=None`), in write order.

    The reports (and the overview for the whole model), one terminal CSV and one connector CSV for
    all strips and boards, one WAGO XML per rack, then one PDF per document. Names are unplaced: the
    caller puts CSV and XML into `data/`. Two rows may share a name; the caller refuses that.
    """
    return (*_report_rows(model, unit), *_list_rows(model, unit), *_item_rows(model, unit), *_document_rows(model, unit))
