"""One builder per house text record, taking plain values: the facade and the tests share them.

The key of each record is `("build", <table>)`, so a record is the same wherever it is built.
"""

from decimal import Decimal
lazy from collections.abc import Mapping, Sequence

from fransys_model.kernel import make_id

from .house_text import (
    ColourCodes,
    FrameForm,
    HarnessText,
    ReferenceText,
    RevisionForm,
    RevisionTableForm,
    StubText,
    TitleBlockForm,
    WireLabelText,
    Words,
)

__all__ = [
    "colour_codes",
    "frame_form",
    "harness_text",
    "reference_text",
    "revision_form",
    "revision_table_form",
    "stub_text",
    "title_block_form",
    "wire_label_text",
    "words",
]


def reference_text(
    *, page_prefix: str, cell_sep: str, location_sign: str, set_sep: str, width_sample: str
) -> ReferenceText:
    """The `[reference]` record from its five values."""
    return ReferenceText(
        id=make_id(ReferenceText, ("build", "reference")),
        key=("build", "reference"),
        page_prefix=page_prefix,
        cell_sep=cell_sep,
        location_sign=location_sign,
        set_sep=set_sep,
        width_sample=width_sample,
    )


def frame_form(*, row_labels: str, column_labels: str, row_order: str) -> FrameForm:
    """The `[frame]` record from its three values."""
    return FrameForm(
        id=make_id(FrameForm, ("build", "frame")),
        key=("build", "frame"),
        row_labels=row_labels,
        column_labels=column_labels,
        row_order=row_order,
    )


def stub_text(*, arrow_in: str, arrow_out: str, port_sep: str, port_join: str) -> StubText:
    """The `[stub]` record from its four values."""
    return StubText(
        id=make_id(StubText, ("build", "stub")),
        key=("build", "stub"),
        arrow_in=arrow_in,
        arrow_out=arrow_out,
        port_sep=port_sep,
        port_join=port_join,
    )


def wire_label_text(*, separator: str, show_ends: bool) -> WireLabelText:
    """The `[wire_label]` record from its two values."""
    return WireLabelText(
        id=make_id(WireLabelText, ("build", "wire_label")),
        key=("build", "wire_label"),
        separator=separator,
        show_ends=show_ends,
    )


def harness_text(*, branch_sep: str) -> HarnessText:
    """The `[harness]` record from its value."""
    return HarnessText(
        id=make_id(HarnessText, ("build", "harness")),
        key=("build", "harness"),
        branch_sep=branch_sep,
    )


def colour_codes(*, pe: str, shield: str, defaults: Mapping[str, Sequence[str]]) -> ColourCodes:
    """The `[colours]` record: `defaults` maps a wiring row name to its colour and size text."""
    return ColourCodes(
        id=make_id(ColourCodes, ("build", "colours")),
        key=("build", "colours"),
        pe=pe,
        shield=shield,
        defaults=frozendict({row: tuple(spec) for row, spec in defaults.items()}),
    )


def title_block_form(
    *, fields: Sequence[str], band_mm: float, centre_gap_mm: float
) -> TitleBlockForm:
    """The `[title_block]` record; the two lengths are held as exact decimals of the mm."""
    return TitleBlockForm(
        id=make_id(TitleBlockForm, ("build", "title_block")),
        key=("build", "title_block"),
        fields=tuple(fields),
        band_mm=Decimal(str(band_mm)),
        centre_gap_mm=Decimal(str(centre_gap_mm)),
    )


def revision_table_form(*, columns: Sequence[str], description_mm: float) -> RevisionTableForm:
    """The `[revision_table]` record; the width is held as an exact decimal of the mm."""
    return RevisionTableForm(
        id=make_id(RevisionTableForm, ("build", "revision_table")),
        key=("build", "revision_table"),
        columns=tuple(columns),
        description_mm=Decimal(str(description_mm)),
    )


def revision_form(*, date_format: str, initials_required: bool, printed: str) -> RevisionForm:
    """The `[revision]` record; `printed` is the table's `format` key, the form of `1.1`."""
    return RevisionForm(
        id=make_id(RevisionForm, ("build", "revision")),
        key=("build", "revision"),
        date_format=date_format,
        initials_required=initials_required,
        format=printed,
    )


def words(table: Mapping[str, str]) -> Words:
    """The `[words]` record from the whole table, key to text."""
    return Words(
        id=make_id(Words, ("build", "words")),
        key=("build", "words"),
        words=frozendict(table),
    )
