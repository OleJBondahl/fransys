"""Text that layout and render must agree on: one fact, one place (decision model-0032).

See derive-text.md.

The layout engine sizes a marker's box and a cross-reference label from their text; render
must print exactly that text but may not import `fransys_layout`. Three pure formatters on
plain values (`frame_column`, `position_text`, `location_prefix`) and a family of readers on a
laid-out model (`marker_text`, `cross_reference_text`) hold that
text so both sides call the same code. `fransys_layout.stages.references` calls the
formatters and keeps no copy; render will call the readers. `port_designation_in` applies
the same location rule to a list's end (`terminal_rows`, `wire_rows` and
`connector_rows` call it).

Not re-exported from `fransys_model.derive`: `fransys-layout`'s import-layering
exception (DESIGN 4, decision layout-0037) is keyed to the qualified module path
`fransys_model.derive.drawing_text`, so every stage imports it directly.
"""

from fransys_model.derive.contact_image import (
    CONTACTS_HEADED,
    coil_heading,
    contact_marks,
)
from fransys_model.derive.designation import connector_designation, port_designation
from fransys_model.derive.frame_position import (
    content_extent,
    frame_column,
    frame_row,
    location_path,
    location_prefix,
    partner_position_text,
    place_text,
    position_text,
    row_letter,
)
from fransys_model.derive.location_text import (
    product_location,
    stub_far_end,
)
from fransys_model.derive.marker_targets import marker_lines, more_count, more_text
from fransys_model.derive.marker_text import REF_SLOTS, marker_text, reference_slot
from fransys_model.derive.pole_ports import pole_prefix
from fransys_model.derive.port_marking import port_marking
from fransys_model.derive.reference_heads import heads_group
from fransys_model.derive.revision_text import revision_text
from fransys_model.derive.stub_text import (
    line_stub_line,
    off_stub_line,
)
from fransys_model.derive.tag_echo import reference_digits, tag_echo_text
from fransys_model.derive.tag_text import (
    external_note,
    is_device_terminal,
    item_tag_text,
    point_text,
    strip_tag_text,
    tag_text,
    unit_tag_text,
)
from fransys_model.derive.unit_nodes import own_nodes
from fransys_model.derive.unit_release import unit_release
from fransys_model.derive.wire_ends import ordered_wire_ends
from fransys_model.kernel import Id, Model, SchemaError
from fransys_model.layout import (
    DrawingSet,
    Page,
    PageGroup,
    layout_of,
)
from fransys_model.vocab.tables import conductors
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Unit, UnitRelease


def wire_label_text(end_a: str, end_b: str) -> str:
    """The text at both ends of a wire, `-B12:96 -Q11:A1`: the join's one home."""
    return f"{end_a} {end_b}"


def wire_text(model: Model, conductor: Id[Conductor], *, unit: Id[Unit] | None = None) -> str:
    """A WIRE label's text via `wire_label_text`; `unit` makes the ends unit-relative."""
    record = conductors(model)[conductor]
    ends = ordered_wire_ends(model, record.a, record.b)
    return wire_label_text(*(port_designation(model, port, unit=unit) for port in ends))


def _release_name(release: UnitRelease) -> str:
    return release.title or release.name


def release_title(release: UnitRelease) -> str:
    """A release as a title block prints it: `"Pump rev 1.1"`.

    The title (else the name) and the revision text: the one home of the text, called by
    `outline_title` and by a finding naming a release.
    """
    return f"{_release_name(release)} rev {revision_text(release.version, release.revision)}"


def unit_label(model: Model, unit: Id[Unit]) -> str:
    """What a drawing, a cover or a title block prints for a unit (decision model-0066).

    The unit's release title (`derive.unit_release`), else its name when the title is empty.
    """
    return _release_name(unit_release(model, unit))


def outline_title(model: Model, unit: Id[Unit] | None) -> str:
    """A black box's title: `"<unit label> rev <revision_text>"`, `"Pump rev 1.1"` (model-0066)."""
    if unit is None:
        msg = "an outline title needs a unit"
        raise SchemaError(msg, kind="unit")
    return release_title(unit_release(model, unit))


def page_title_groups(model: Model, page: Page) -> tuple[PageGroup, ...]:
    """Which of `page.groups` title `page` (model-0097).

    A unit's own groups only, when the page's drawing set has a unit; every group, unfiltered,
    when the set has no unit (a location-subject page). `page_title_forms` calls this, so the
    rule has one home.
    """
    unit = layout_of(model, DrawingSet)[page.drawing_set].unit
    if unit is None:
        return page.groups
    own = own_nodes(model, unit)
    return tuple(group for group in page.groups if group.group in own)


__all__ = [
    "CONTACTS_HEADED",
    "REF_SLOTS",
    "coil_heading",
    "connector_designation",
    "contact_marks",
    "content_extent",
    "external_note",
    "frame_column",
    "frame_row",
    "heads_group",
    "is_device_terminal",
    "item_tag_text",
    "line_stub_line",
    "location_path",
    "location_prefix",
    "marker_lines",
    "marker_text",
    "more_count",
    "more_text",
    "off_stub_line",
    "outline_title",
    "page_title_groups",
    "partner_position_text",
    "place_text",
    "point_text",
    "pole_prefix",
    "port_marking",
    "position_text",
    "product_location",
    "reference_digits",
    "reference_slot",
    "release_title",
    "row_letter",
    "strip_tag_text",
    "stub_far_end",
    "tag_echo_text",
    "tag_text",
    "unit_label",
    "unit_tag_text",
]
