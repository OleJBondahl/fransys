"""Designation numbering pass (design/derive.md).

Treats a `facet.reserved_designation` text as taken too (FD1, FD5, fixed-designations spec).
"""

import dataclasses
from typing import TYPE_CHECKING, Final

from fransys_model.derive.designation import (
    can_print_designation,
    connector_segment,
    designating_ancestors,
    own_designation_or_none,
    port_designation,
    product_designation,
    reference_designation,
    reference_leaves,
    takes_parents_designation,
)
from fransys_model.derive.harness import all_cables, all_unit_cables
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import terminal_items
from fransys_model.derive.passes.numbering_units import (
    instance_tags_in,
    number_unit_tags,
    unit_tag_duplicates,
)
from fransys_model.derive.unit_relative_key import unit_relative_key
from fransys_model.derive.unit_release import unit_release
from fransys_model.kernel import Finding, Model, Severity, evolve, make_id
from fransys_model.kernel.origin import require_origin
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.facets.reserved_designation import ReservedDesignationFacet
from fransys_model.vocab.numbering_codes import item_class_code
from fransys_model.vocab.tables import (
    aspect_nodes,
    facets_of,
    functions,
    items,
    placements,
)

if TYPE_CHECKING:
    from fransys_model.derive.indexes import Indexes
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Item, Port, Unit

DESIGNATION_DUPLICATE: Final[str] = "DESIGNATION_DUPLICATE"
REFERENCE_DESIGNATION_DUPLICATE: Final[str] = "REFERENCE_DESIGNATION_DUPLICATE"
PRODUCT_DESIGNATION_DUPLICATE: Final[str] = "PRODUCT_DESIGNATION_DUPLICATE"
HARNESS_END_AMBIGUOUS: Final[str] = "HARNESS_END_AMBIGUOUS"
PORT_DESIGNATION_DUPLICATE: Final[str] = "PORT_DESIGNATION_DUPLICATE"


def _renders_a_segment(model: Model, item: Id[Item]) -> bool:
    """Whether `reference_designation` renders a `=` or `+` segment for `item`.

    It asks `reference_leaves`: an own `FUNCTION` or `LOCATION` placement, or a terminal's strip's.
    A `PRODUCT` placement, like none, still renders the bare flat designation.
    """
    return bool(reference_leaves(model, item))


def _renders_a_location(model: Model, idx: Indexes, item: Id[Item]) -> bool:
    """Whether `item` has a placement in the location aspect `product_designation` renders.

    Mirrors `_renders_a_segment`, narrowed to `Aspect.LOCATION`: a `FUNCTION` placement is no gate.
    Only a fixed physical location makes two items' printed product tags comparable.
    """
    nodes = aspect_nodes(model)
    all_placements = placements(model)
    return any(
        nodes[all_placements[placement].node].aspect is Aspect.LOCATION
        for placement in idx.placements_by_item.get(item, ())
    )


def _terminal_prints(model: Model, terminal: Item) -> bool:
    """Whether a terminal's reference can be printed: its strip's `item_designation` can be.

    A part-less strip or a board with no class code makes it raise; `ITEM_WITHOUT_PART` says so.
    Such a terminal is left out here; only a raise is asked, never caught.
    """
    return can_print_designation(model, terminal.id if terminal.parent is None else terminal.parent)


def _reference_duplicates(model: Model, terminals: frozenset[Id[Item]]) -> list[Finding]:
    """One finding per full reference designation shared by more than one item.

    Only a designated item that renders a `=` or `+` segment is compared, a terminal by its strip's.
    An item whose ancestor has no designation is left out, not raised on, like `_port_duplicates`.
    """
    by_text: dict[str, list[Item]] = {}
    for item in items(model).values():
        if (
            (
                own_designation_or_none(model, item) is not None
                or (item.id in terminals and _terminal_prints(model, item))
            )
            # guards the shared text; cannot fail on the base, an accessory has no designation
            and not takes_parents_designation(model, item.id)
            and _renders_a_segment(model, item.id)
            # an ancestor board or harness with no designation of its own (model-0107, an
            # untagged structural harness) leaves nothing to compare here either
            and can_print_designation(model, item.id)
        ):
            by_text.setdefault(reference_designation(model, item.id), []).append(item)
    return [
        Finding(
            code=REFERENCE_DESIGNATION_DUPLICATE,
            severity=Severity.ERROR,
            subjects=tuple(sorted(item.id for item in group)),
            message=(
                f"reference designation {text!r} is shared by "
                + ", ".join(sorted("/".join(item.key) for item in group))
            ),
        )
        for text, group in by_text.items()
        if len(group) > 1
    ]


def _connector_prints(model: Model, idx: Indexes, item: Id[Item], product: str) -> list[str]:
    """`item`'s product designation behind each connector segment it prints (`-A1-X1`).

    A connector label equal to a child item's designation is one printed text, so it is compared.
    `connector_segment` is the one place the segment is decided.
    """
    segments = (
        connector_segment(model, function) for function in idx.functions_by_item.get(item, ())
    )
    return [product + segment for segment in segments if segment]


def _product_duplicates(model: Model, terminals: frozenset[Id[Item]]) -> list[Finding]:
    """One finding per printed product designation shared by more than one item.

    A location-placed item is compared model-wide by text; an unplaced item by `(item.unit, text)`.
    An item whose ancestor has no designation is left out, not raised on, like `_port_duplicates`.
    """
    idx = build_indexes(model)
    by_text: dict[str, list[Item]] = {}
    by_unit_text: dict[tuple[Id[Unit] | None, str], list[Item]] = {}
    for item in items(model).values():
        if (
            item.id in terminals
            or own_designation_or_none(model, item) is None
            # model-0107: an ancestor board or harness with no designation of its own leaves
            # nothing to compare here either
            or not can_print_designation(model, item.id)
        ):
            continue
        text = product_designation(model, item.id)
        located = _renders_a_location(model, idx, item.id)
        for printed in (text, *_connector_prints(model, idx, item.id, text)):
            if located:
                by_text.setdefault(printed, []).append(item)
            else:
                by_unit_text.setdefault((item.unit, printed), []).append(item)
    findings = [
        Finding(
            code=PRODUCT_DESIGNATION_DUPLICATE,
            severity=Severity.ERROR,
            subjects=tuple(sorted(item.id for item in group)),
            message=(
                f"product designation {text!r} is shared by "
                + ", ".join(sorted("/".join(item.key) for item in group))
            ),
        )
        for text, group in by_text.items()
        if len(group) > 1
    ]
    findings.extend(
        Finding(
            code=PRODUCT_DESIGNATION_DUPLICATE,
            severity=Severity.ERROR,
            subjects=tuple(sorted(item.id for item in group)),
            message=(
                f"product designation {text!r} is shared by "
                + ", ".join(sorted("/".join(item.key) for item in group))
            ),
        )
        for (_unit, text), group in by_unit_text.items()
        if len(group) > 1
    )
    return findings


def _harness_end_ambiguities(model: Model) -> list[Finding]:
    """One finding per cable with two or more ends that print the same text.

    Ends come from `all_cables`, grouped by text within one cable alone, never model-wide.
    A unit-owned cable is read again as its unit reads it; a blank end never collides.
    """
    findings: list[Finding] = []
    reported: set[tuple[str, tuple[Id[Item], ...]]] = set()
    for cables, where in (
        (all_cables(model), ""),
        (all_unit_cables(model), " in its unit's document"),
    ):
        for cable in cables:
            by_text: dict[str, list[Id[Item]]] = {}
            for end in cable.ends:
                if end.designation:
                    by_text.setdefault(end.designation, []).append(end.item)
            for text, ends in by_text.items():
                subjects = tuple(sorted((cable.cable, *ends)))
                if len(ends) > 1 and (text, subjects) not in reported:
                    reported.add((text, subjects))
                    findings.append(
                        Finding(
                            code=HARNESS_END_AMBIGUOUS,
                            severity=Severity.ERROR,
                            subjects=subjects,
                            message=(
                                f"two ends of {cable.designation} print {text!r}{where}; "
                                "place the unit instances at locations or tag the strips apart"
                            ),
                        )
                    )
    return findings


def _port_duplicates(model: Model, terminals: frozenset[Id[Item]]) -> list[Finding]:
    """One finding per (item, printed port text) shared by more than one port of that item.

    The text is `port_designation`, the one rule for what a port prints.
    A terminal is left out (its two ports are one point), as is an item that cannot print one.
    """
    idx = build_indexes(model)
    all_functions = functions(model)
    findings: list[Finding] = []
    for item in items(model).values():
        if item.id in terminals or not can_print_designation(model, item.id):
            continue
        by_text: dict[str, list[tuple[Id[Port], str]]] = {}
        for function in idx.functions_by_item.get(item.id, ()):
            for port in idx.ports_by_function.get(function, ()):
                by_text.setdefault(port_designation(model, port), []).append(
                    (port, all_functions[function].name)
                )
        findings.extend(
            Finding(
                code=PORT_DESIGNATION_DUPLICATE,
                severity=Severity.ERROR,
                subjects=tuple(sorted(port for port, _ in group)),
                message=(
                    f"item {'/'.join(item.key)} prints {text!r} for the ports of functions "
                    f"{', '.join(sorted({name for _, name in group}))}; the same text names "
                    "two pins in every list and drawing, so the part's pin markings must "
                    "tell them apart"
                ),
            )
            for text, group in by_text.items()
            if len(group) > 1
        )
    return findings


def _reserved_texts(model: Model, unit: Id[Unit] | None, scope: Id[Item] | None) -> frozenset[str]:
    """Every `facet.reserved_designation` text that counts as taken in this group.

    `unit=None` never matches: the subject is `Id[UnitRelease]` only.
    A top-level group has no release to match against.
    """
    if unit is None:
        return frozenset[str]()
    release_id = unit_release(model, unit).id
    group_scope = unit_relative_key(model, scope) if scope is not None else None
    return frozenset[str](
        facet.text
        for facet in facets_of(model, ReservedDesignationFacet).values()
        if facet.subject == release_id and facet.scope == group_scope
    )


def _duplicates(model: Model, siblings: list[Item], reserved: frozenset[str]) -> list[Finding]:
    """One finding per item whose printed own text collides with a sibling's, or a released one.

    Counts every own text, not tags alone, so a tag equal to another item's own text is caught.
    An assigned text never collides with another assigned one (`_assigned`'s `taken` set).
    """
    counts: dict[str, int] = {}
    texts: dict[Id[Item], str | None] = {}
    for item in siblings:
        text = own_designation_or_none(model, item)
        texts[item.id] = text
        if text is not None:
            counts[text] = counts.get(text, 0) + 1
    findings = []
    for item in siblings:
        text = texts[item.id]
        if text is None:
            continue
        if counts[text] > 1:
            reason = "another item with the same unit and parent has too"
        elif text in reserved:
            reason = "a released revision of this unit's own version has already retired or moved"
        else:
            continue
        findings.append(
            Finding(
                code=DESIGNATION_DUPLICATE,
                severity=Severity.ERROR,
                subjects=(item.id,),
                message=f"item {'/'.join(item.key)} has the designation {text!r}, which {reason}",
            )
        )
    return findings


def _assigned(
    model: Model,
    siblings: list[Item],
    reserved: frozenset[str],
) -> list[AssignedDesignationFacet]:
    """One `facet.assigned_designation` for each unnumbered sibling that can be numbered.

    Each takes the first `code + str(n)`, from n = 1, not already an exact string in the group.
    An item with an own text is skipped and its text taken; an accessory uses up no number.
    """
    taken = {
        text for item in siblings if (text := own_designation_or_none(model, item)) is not None
    } | reserved
    if siblings and not designating_ancestors(model, siblings[0].id):
        taken |= instance_tags_in(model, siblings[0].unit)  # UT3: one count with the instances
    numbered: list[AssignedDesignationFacet] = []
    for item in sorted(siblings, key=lambda item: (item.key, item.id)):
        if own_designation_or_none(model, item) is not None or takes_parents_designation(
            model, item.id
        ):
            continue
        code = item_class_code(model, item.id)
        if not code:
            continue
        counter = 1
        while f"{code}{counter}" in taken:
            counter += 1
        candidate = f"{code}{counter}"
        taken.add(candidate)
        key = (*item.key, "assigned_designation")
        numbered.append(
            AssignedDesignationFacet(
                id=make_id(AssignedDesignationFacet, key), key=key, subject=item.id, text=candidate
            )
        )
    return numbered


def number(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Number every item that has no own designation from its `Part.class_code`.

    Each such item gets a `facet.assigned_designation` of class code plus a counter, one
    counter per sibling group (unit, nearest designating ancestor, class code).
    A tag or existing facet is kept; terminals, partless items and accessories are skipped.
    Also reports the `*_DUPLICATE` and `HARNESS_END_AMBIGUOUS` findings (all `ERROR`).

    Args:
        model: The model to number.

    Returns:
        `model` itself if nothing was numbered, else evolved with the new facets; and the
        findings, sorted by `(code, subjects, message)`.
    """
    terminals = terminal_items(model)
    # The group's second element is the item's nearest read-through ancestor (a board or
    # harness), not its structural `parent` (C3b): still an item id or `None`.
    by_group: dict[tuple[Id[Unit] | None, Id[Item] | None], list[Item]] = {}
    for item in items(model).values():
        if item.id not in terminals:
            ancestors = designating_ancestors(model, item.id)
            scope = ancestors[-1] if ancestors else None
            by_group.setdefault((item.unit, scope), []).append(item)
    findings: list[Finding] = []
    numbered: list[AssignedDesignationFacet] = []
    for (unit, scope), siblings in by_group.items():
        reserved = _reserved_texts(model, unit, scope)
        findings.extend(_duplicates(model, siblings, reserved))
        numbered.extend(_assigned(model, siblings, reserved))
    if numbered:
        # Each facet takes its item's origin (`Model.origins` is outside every digest), so an
        # error about it still cites the author.
        authored = {facet.id: require_origin(model.origins, facet.subject) for facet in numbered}
        evolved = evolve(model, put=numbered, origin=authored[numbered[0].id])
        origins = frozendict({**evolved.origins, **authored})
        result = dataclasses.replace(evolved, origins=origins)
    else:
        result = model
    result = number_unit_tags(result, _reserved_texts)
    findings.extend(unit_tag_duplicates(result, DESIGNATION_DUPLICATE))
    findings.extend(_reference_duplicates(result, terminals))
    findings.extend(_product_duplicates(result, terminals))
    findings.extend(_harness_end_ambiguities(result))
    findings.extend(_port_duplicates(result, terminals))
    ordered = tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))
    return result, ordered
