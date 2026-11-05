"""The house text records: one per `settings.toml` table, written once by the facade (SO3).

Each is a singleton the facade writes after `freeze()` and before any pass; an input never
authors one and no pass removes it. Derive reads a record through its one accessor in
`derive.facts.house_settings`. A field has no default: a model with no record raises there.
"""

from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, Value, record

__all__ = [
    "FrameForm",
    "HarnessText",
    "HouseProfile",
    "ReferenceText",
    "RevisionForm",
    "RevisionTableForm",
    "StubText",
    "TitleBlockForm",
    "WireLabelText",
    "Words",
]


@record(kind="layout.reference_text", singleton=True)
class ReferenceText:
    """The `[reference]` table: the signs of a printed reference, `+A1p3:B2`, and a width sample."""

    id: Id[ReferenceText]
    key: AuthoringKey
    page_prefix: str
    cell_sep: str
    location_sign: str
    set_sep: str
    width_sample: str
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.frame_form", singleton=True)
class FrameForm:
    """The `[frame]` table: how a frame's rows and columns are named and counted."""

    id: Id[FrameForm]
    key: AuthoringKey
    row_labels: str
    column_labels: str
    row_order: str
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.stub_text", singleton=True)
class StubText:
    """The `[stub]` table: the arrows of a stub and the signs between its far end and ports."""

    id: Id[StubText]
    key: AuthoringKey
    arrow_in: str
    arrow_out: str
    port_sep: str
    port_join: str
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.wire_label_text", singleton=True)
class WireLabelText:
    """The `[wire_label]` table: the sign between a wire label's ends and whether it shows both."""

    id: Id[WireLabelText]
    key: AuthoringKey
    separator: str
    show_ends: bool
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.harness_text", singleton=True)
class HarnessText:
    """The `[harness]` table: the sign that opens a harness line's branch, `-W13.n`."""

    id: Id[HarnessText]
    key: AuthoringKey
    branch_sep: str
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.title_block_form", singleton=True)
class TitleBlockForm:
    """The `[title_block]` table: the cells of the block, the band's height in mm and the capital heights its stack is authored for."""

    id: Id[TitleBlockForm]
    key: AuthoringKey
    fields: tuple[str, ...]
    band_mm: Decimal
    centre_gap_mm: Decimal
    label_height_mm: Decimal
    value_height_mm: Decimal
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.revision_table_form", singleton=True)
class RevisionTableForm:
    """The `[revision_table]` table: the column keys (of `[words]`) and the wrapping width in mm."""

    id: Id[RevisionTableForm]
    key: AuthoringKey
    columns: tuple[str, ...]
    description_mm: Decimal
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.revision_form", singleton=True)
class RevisionForm:
    """The `[revision]` table: the date pattern, whether initials are needed, the printed form."""

    id: Id[RevisionForm]
    key: AuthoringKey
    date_format: str
    initials_required: bool
    format: str
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.words", singleton=True)
class Words:
    """The flat `[words]` table: every printed word of the model's text, by key."""

    id: Id[Words]
    key: AuthoringKey
    words: frozendict[str, str]
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.house_profile", singleton=True)
class HouseProfile:
    """The `[profile]` table: the house numbers of the layout rules, which an authored `Profile` replaces.

    Penalties are unitless; `marker_padding` is the clearance, in `G`, between a cable
    drawing's text and its outline, on every edge (R1032: cables only).
    """

    id: Id[HouseProfile]
    key: AuthoringKey
    marker_padding: int
    route_turn_penalty: int
    route_crossing_penalty: int
    ext: frozendict[str, Value] = frozendict()
