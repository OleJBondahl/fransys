"""The build's house text records, one per `settings.toml` table: written once after `freeze()`."""

from typing import TYPE_CHECKING, cast
lazy from collections.abc import Mapping

from fransys_model.kernel import Draft, Origin, SchemaError, evolve
from fransys_model.layout import (
    HOUSE_TEXT_KINDS,
    colour_codes,
    frame_form,
    harness_text,
    reference_text,
    revision_form,
    revision_table_form,
    stub_text,
    title_block_form,
    wire_label_text,
    words,
)

from ._paper import refuse_authored_paper, with_paper

if TYPE_CHECKING:
    from fransys_model.kernel import Model, Record

    from ._settings_merge import Table
    from .settings import Settings

__all__ = ["refuse_authored_house", "with_house"]

_ORIGIN = Origin(file="fransys/_house.py", line=0, note="the build's house text records")


def _str(table: Table, key: str) -> str:
    return cast("str", table[key])


def _strs(table: Table, key: str) -> tuple[str, ...]:
    return cast("tuple[str, ...]", table[key])


def _float(table: Table, key: str) -> float:
    return float(cast("float", table[key]))


def _first(settings: Settings) -> tuple[Record, ...]:
    ref, frame, stub = (settings.table(n) for n in ("reference", "frame", "stub"))
    label, harness = (settings.table(n) for n in ("wire_label", "harness"))
    return (
        reference_text(
            page_prefix=_str(ref, "page_prefix"),
            cell_sep=_str(ref, "cell_sep"),
            location_sign=_str(ref, "location_sign"),
            set_sep=_str(ref, "set_sep"),
            width_sample=_str(ref, "width_sample"),
        ),
        frame_form(
            row_labels=_str(frame, "row_labels"),
            column_labels=_str(frame, "column_labels"),
            row_order=_str(frame, "row_order"),
        ),
        stub_text(
            arrow_in=_str(stub, "arrow_in"),
            arrow_out=_str(stub, "arrow_out"),
            port_sep=_str(stub, "port_sep"),
            port_join=_str(stub, "port_join"),
        ),
        wire_label_text(separator=_str(label, "separator"), show_ends=bool(label["show_ends"])),
        harness_text(branch_sep=_str(harness, "branch_sep")),
    )


def _second(settings: Settings) -> tuple[Record, ...]:
    colours, block = (settings.table(n) for n in ("colours", "title_block"))
    rev_table, rev = settings.table("revision_table"), settings.table("revision")
    return (
        colour_codes(
            pe=_str(colours, "pe"),
            shield=_str(colours, "shield"),
            defaults=cast("Mapping[str, list[str]]", colours["defaults"]),
        ),
        title_block_form(
            fields=_strs(block, "fields"),
            band_mm=_float(block, "band_mm"),
            centre_gap_mm=_float(block, "centre_gap_mm"),
        ),
        revision_table_form(
            columns=_strs(rev_table, "columns"), description_mm=_float(rev_table, "description_mm")
        ),
        revision_form(
            date_format=_str(rev, "date_format"),
            initials_required=bool(rev["initials_required"]),
            printed=_str(rev, "format"),
        ),
        words(cast("Mapping[str, str]", settings.table("words"))),
    )


def _records(settings: Settings) -> tuple[Record, ...]:
    """One record per settings table, built by the model's builders."""
    return (*_first(settings), *_second(settings))


def refuse_authored_house(draft: Draft) -> None:
    """Raise when `draft` holds a paper or house text record: only the facade writes them."""
    refuse_authored_paper(draft)
    for record in draft.records():
        if isinstance(record, HOUSE_TEXT_KINDS):
            msg = f"an input authors a {type(record).__name__} record: the facade writes it"
            raise SchemaError(msg, kind="layout.house_text")


def with_house(model: Model, settings: Settings) -> Model:
    """`model` with the paper records and the house text records of `settings`."""
    return evolve(with_paper(model, settings), put=_records(settings), origin=_ORIGIN)
