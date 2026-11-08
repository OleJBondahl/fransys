"""The ring-out sheet of one document: the wires, cores and bridges to measure, from their derive homes (R2008)."""

lazy from collections.abc import Mapping

from fransys_model.kernel import render_id
from fransys_model.vocab.tables import conductors
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.document import Document

from .cable_cores import cable_rows
from .contact_places import conductor_places
from .document_unit import document_unit
from .facts.house_settings import word
from .harness import cable_list_rows
from .rows_document_row import document_row
from .rows_ring_out import RingOutKind, RingOutRow, RingOutWords
from .title_block import document_facts
from .wire_ends import ordered_wire_ends
from .wire_list import wire_rows
from .wiring import terminal_rows

__all__ = ["ring_out_cells", "ring_out_headers", "ring_out_rows", "ring_out_statuses", "ring_out_title", "ring_out_words"]

_WORDS = {
    "sheet": "ring_sheet",
    "revision": "revision",
    "no": "ring_no",
    "type": "ring_type",
    "wire": "ring_wire",
    "core": "ring_core",
    "bridge": "bridge",
    "from_": "ring_from",
    "to": "ring_to",
    "label": "ring_label",
    "colour": "ring_colour",
    "mm2": "ring_mm2",
    "drawing": "ring_drawing",
    "status": "ring_status",
    "ok": "ring_ok",
    "wrong": "ring_wrong",
    "untested": "ring_untested",
    "found": "ring_found",
    "comment": "ring_comment",
    "extra": "ring_extra",
}


def ring_out_words(model: Model) -> RingOutWords:
    """The words of the sheet from `[words]`; an absent key raises naming the key."""
    return RingOutWords(**{field: word(model, key) for field, key in _WORDS.items()})


def ring_out_headers(words: RingOutWords) -> tuple[str, ...]:
    """The header cells of the sheet, in column order."""
    return (
        words.no,
        words.type,
        words.from_,
        words.to,
        words.label,
        words.colour,
        words.mm2,
        words.drawing,
        words.status,
        words.found,
        words.comment,
    )


def ring_out_statuses(words: RingOutWords) -> tuple[str, str, str]:
    """The dropdown values of the Status column: OK, wrong, not tested."""
    return (words.ok, words.wrong, words.untested)


def ring_out_cells(row: RingOutRow, number: int, words: RingOutWords) -> tuple[int | str, ...]:
    """The first eight cells of `row`, numbered `number`: No to Drawing; Status to Comment are the electrician's."""
    kind = {RingOutKind.WIRE: words.wire, RingOutKind.CORE: words.core, RingOutKind.BRIDGE: words.bridge}[row.join]
    mm2 = "" if row.cross_section_mm2 is None else str(row.cross_section_mm2)
    return (number, kind, row.from_, row.to, row.label, row.colour, mm2, row.drawing)


def ring_out_title(model: Model, document: Id[Document]) -> str:
    """`<title> <number> <revision word> <revision label>`: the title row, from the title block's own facts."""
    title, number, _customer, revision, _date, _author = document_facts(model, document)
    return " ".join(part for part in (title, number, word(model, "revision"), revision) if part)


def _wire_joins(model: Model, document: Id[Document], places: Mapping[tuple[Id[Conductor], str], str]) -> list[RingOutRow]:
    record = document_row(model, document)
    rows = []
    for row in wire_rows(model, unit=document_unit(model, document), context=record.location):
        conductor = conductors(model)[row.conductor]
        first, _second = ordered_wire_ends(model, conductor.a, conductor.b)
        rows.append(
            RingOutRow(
                join=RingOutKind.WIRE,
                from_=row.from_,
                to=row.to,
                label=row.ends,
                colour=row.colour,
                cross_section_mm2=row.cross_section_mm2,
                drawing=places.get((row.conductor, render_id(first)), ""),
            )
        )
    return rows


def _core_joins(model: Model, document: Id[Document], places: Mapping[tuple[Id[Conductor], str], str]) -> list[RingOutRow]:
    unit = document_unit(model, document)
    return [
        RingOutRow(
            join=RingOutKind.CORE,
            from_=core.end_a_designation,
            to=core.end_b_designation,
            label=f"{core.cable_designation}.{core.index}",
            colour=core.colour,
            cross_section_mm2=listed.gauge_mm2,
            drawing=places.get((core.conductor, render_id(core.end_a)), ""),
        )
        for listed in cable_list_rows(model, unit=unit)
        for core in cable_rows(model, listed.cable, unit=unit)
    ]


def _bridge_joins(model: Model, document: Id[Document]) -> list[RingOutRow]:
    """A group of n bridged terminals gives n-1 rows of consecutive members, in terminal-list order; not drawn, so no place."""
    record = document_row(model, document)
    last: dict[int, str] = {}
    rows = []
    for row in terminal_rows(model, unit=document_unit(model, document), context=record.location):
        if row.jumper_group is None:
            continue
        before = last.get(row.jumper_group)
        last[row.jumper_group] = row.designation
        if before is not None:
            rows.append(
                RingOutRow(join=RingOutKind.BRIDGE, from_=before, to=row.designation, label="", colour="", cross_section_mm2=None, drawing="")
            )
    return rows


def ring_out_rows(model: Model, document: Id[Document]) -> tuple[RingOutRow, ...]:
    """The wires, then the cores, then the bridges of `document`'s unit, each in its home's order.

    Wires are `wire_rows`, cores `cable_rows` of the unit's `cable_list_rows`, a bridge a pair of
    consecutive members of a `TerminalRow.jumper_group`; nothing is sorted here.

    Raises:
        KeyError: `document` names no document of `model`.
    """
    places = conductor_places(model, document)
    return tuple(_wire_joins(model, document, places) + _core_joins(model, document, places) + _bridge_joins(model, document))
