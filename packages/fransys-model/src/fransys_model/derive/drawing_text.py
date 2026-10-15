"""Text that layout and render must agree on: one fact, one place (decision model-0032).

See derive-text.md.

The layout engine sizes a marker's box and a cross-reference label from their text; render
must print exactly that text but may not import `fransys_layout`. Three pure formatters on
plain values (`frame_column`, `position_text`, `location_prefix`) and a family of readers on a
laid-out model (`marker_text`, `cross_reference_text`, `label_text`) hold that
text so both sides call the same code. `fransys_layout.stages.references` calls the
formatters and keeps no copy; render will call the readers. `port_designation_in` applies
the same location rule to a list's end (`terminal_rows`, `wire_rows` and
`connector_rows` call it).

Not re-exported from `fransys_model.derive`: `fransys-layout`'s import-layering
exception (DESIGN 4, decision layout-0037) is keyed to the qualified module path
`fransys_model.derive.drawing_text`, so every stage imports it directly.
"""

from typing import cast

from fransys_model.derive.contact_image import (
    CONTACT_SLOTS,
    CONTACTS_HEADED,
    coil_heading,
    contact_heading,
    contact_image,
    contact_marks,
    cross_reference_text,
    image_entries,
)
from fransys_model.derive.designation import (
    connector_designation,
    own_nodes,
    port_designation,
)
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
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.location_text import (
    product_location,
    stub_far_end,
)
from fransys_model.derive.lookups import black_box_unit
from fransys_model.derive.marker_targets import marker_lines, more_count, more_text
from fransys_model.derive.marker_text import REF_SLOTS, marker_text, reference_slot
from fransys_model.derive.pole_ports import pole_prefix
from fransys_model.derive.port_marking import marking_text, port_marking
from fransys_model.derive.reference_heads import heads_group
from fransys_model.derive.revision_text import revision_text
from fransys_model.derive.stub_text import (
    line_stub_line,
    off_stub_line,
)
from fransys_model.derive.tag_text import (
    external_note,
    is_device_terminal,
    item_tag_text,
    point_text,
    strip_tag_text,
    tag_text,
    unit_tag_text,
)
from fransys_model.derive.unit_release import unit_release
from fransys_model.derive.wire_ends import ordered_wire_ends
from fransys_model.kernel import Id, Model, SchemaError
from fransys_model.layout import (
    DrawingSet,
    Label,
    LabelKind,
    Page,
    PageGroup,
    layout_of,
)
from fransys_model.vocab.membership import unit_items
from fransys_model.vocab.tables import conductors, functions, items, ports
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Function, Port, Unit, UnitRelease


def wire_label_text(end_a: str, end_b: str) -> str:
    """The text at both ends of a wire, `-B12:96 -Q11:A1`: the join's one home."""
    return f"{end_a} {end_b}"


def wire_text(model: Model, conductor: Id[Conductor], *, unit: Id[Unit] | None = None) -> str:
    """A WIRE label's text via `wire_label_text`; `unit` makes the ends unit-relative."""
    record = conductors(model)[conductor]
    ends = ordered_wire_ends(model, record.a, record.b)
    return wire_label_text(*(port_designation(model, port, unit=unit) for port in ends))


def _own_unit(model: Model, label: Label) -> Id[Unit] | None:
    """The set's unit, when the function is in its subtree (a nested black box too)."""
    unit = layout_of(model, DrawingSet)[layout_of(model, Page)[label.page].drawing_set].unit
    if unit is None or label.function is None:
        return None
    return unit if functions(model)[label.function].item in unit_items(model, unit) else None


def _pin_view_ports(model: Model, label: Label) -> tuple[Id[Port], ...]:
    """The ports of the function a pin view's `tag.pin` or `tag.conn` label sits on.

    Layout writes such a label with its function as the subject, never a port or a conductor.
    """
    function = cast("Id[Function]", label.function)
    return build_indexes(model).ports_by_function.get(function, ())


def _pin_port(model: Model, label: Label) -> Id[Port]:
    """The port a `tag.pin.<name>` label names, among its function's ports."""
    name = label.slot.removeprefix("tag.pin.")
    return next(p for p in _pin_view_ports(model, label) if ports(model)[p].name == name)


def _unit_label_text(model: Model, label: Label, unit: Id[Unit]) -> str | None:
    """`label_text`'s TAG text in `unit`'s own set, from the persisted label."""
    if label.slot.startswith("tag.pin."):
        return unit_tag_text(model, _pin_port(model, label), "tag.pin", unit)
    if label.slot == "tag.conn":
        port = min(_pin_view_ports(model, label))
        return unit_tag_text(model, port, "tag.conn", unit)
    return unit_tag_text(model, cast("Id[Function]", label.function), label.slot, unit)


def label_text(model: Model, label: Label) -> str:
    """The text `label` shows, dispatched by its `kind`.

    TAG, MARKING, WIRE and CROSS_REFERENCE are rendered from the model.

    Raises:
        SchemaError: `label` names a subject field that does not match its `kind` (TAG and
            CROSS_REFERENCE want `function`, MARKING wants `port`). A WIRE label always has a
            `conductor`: `Label.__post_init__` enforces it, so this reader trusts it rather
            than checking it again.
    """
    if label.kind is LabelKind.TAG:
        return _tag_label_text(model, label)
    if label.kind is LabelKind.MARKING:
        if label.port is None:
            msg = "a MARKING label has no port"
            raise SchemaError(msg, kind="layout.label", record_id=label.id)
        return marking_text(model, label.port, label.slot)
    if label.kind is LabelKind.WIRE:
        page = layout_of(model, Page)[label.page]
        drawing_set = layout_of(model, DrawingSet)[page.drawing_set]
        return wire_text(model, cast("Id[Conductor]", label.conductor), unit=drawing_set.unit)
    return _cross_reference_label_text(model, label)


def _black_box_unit(model: Model, label: Label) -> Id[Unit] | None:
    """The unit whose black box a title names: `black_box_unit` of the item's unit on its page."""
    unit = items(model)[functions(model)[cast("Id[Function]", label.function)].item].unit
    if unit is None:
        return None
    page = layout_of(model, Page)[label.page]
    return black_box_unit(model, unit, layout_of(model, DrawingSet)[page.drawing_set].unit)


def _tag_label_text(model: Model, label: Label) -> str:
    """`label_text` for a TAG label: the unit's own text, else the slot's text."""
    if label.function is None:
        msg = "a TAG label has no function"
        raise SchemaError(msg, kind="layout.label", record_id=label.id)
    if label.slot == "outline_title":  # A black box's title, from its item's unit
        return outline_title(model, _black_box_unit(model, label))
    if label.slot == "external_note":  # An external item's note, the same text everywhere
        return external_note()
    unit = _own_unit(model, label)
    if unit is not None:
        own = _unit_label_text(model, label, unit)  # the unit's own set
        if own is not None:
            return own
    return _tag_slot_text(model, label, label.function)


def _tag_slot_text(model: Model, label: Label, function: Id[Function]) -> str:
    """`label_text` for a TAG label outside a unit's own set, by its slot."""
    if label.slot.startswith("tag.pin."):  # one pin of a connector
        return port_designation(model, _pin_port(model, label))
    if label.slot == "tag.strip":
        return strip_tag_text(model, function)
    if label.slot == "tag.item":  # a mixed-kind row of one item, its item's tag
        return item_tag_text(model, functions(model)[function].item)
    if label.slot == "tag.conn":  # a pin row's one connector designation (model-0073)
        return connector_designation(model, function)
    if label.slot == "tag.point":
        return point_text(model, function)
    return tag_text(model, function)


def _cross_reference_label_text(model: Model, label: Label) -> str:
    """`label_text` for a CROSS_REFERENCE label: the contact image or the position text."""
    if label.function is None:
        msg = "a CROSS_REFERENCE label has no function"
        raise SchemaError(msg, kind="layout.label", record_id=label.id)
    if label.slot in CONTACT_SLOTS:  # the contact image, one line per row
        no, nc = contact_image(model, label)
        rows = max(len(no), len(nc))
        cells = [
            ("NO", "NC"),
            *zip(no + [""] * (rows - len(no)), nc + [""] * (rows - len(nc)), strict=True),
        ]
        head = contact_heading(model, label)
        lines = [f"{a} | {b}" for a, b in cells]
        return "\n".join([head, *lines] if head else lines)
    return cross_reference_text(model, label)


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
    "CONTACT_SLOTS",
    "REF_SLOTS",
    "coil_heading",
    "connector_designation",
    "contact_heading",
    "contact_image",
    "contact_marks",
    "content_extent",
    "external_note",
    "frame_column",
    "frame_row",
    "heads_group",
    "image_entries",
    "is_device_terminal",
    "item_tag_text",
    "label_text",
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
    "reference_slot",
    "release_title",
    "row_letter",
    "strip_tag_text",
    "stub_far_end",
    "tag_text",
    "unit_label",
    "unit_tag_text",
]
