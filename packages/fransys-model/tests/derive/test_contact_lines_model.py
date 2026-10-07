"""Tests for `used_pins`, `contact_counts` and the contact lines of `bom_lines` (model-0170).

A used pin is a connector port where a WIRE or a CORE lands. A `ContactsFacet` fits a contact
part in every used pin, or by pin name; `bom_lines` gives one line per contact part.
"""

import dataclasses

from connector_builders import make_connector
from plant import Plant
from query_builders import make_core, make_part

from fransys_model.derive import TOP_LEVEL, bom_lines
from fransys_model.derive.contact_lines import contact_counts, used_pins
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.facets import ContactFit, ContactsFacet
lazy from fransys_model.vocab.templates import Part

HSG = make_id(Item, ("hsg",))
HSG2 = make_id(Item, ("hsg2",))


def _housing(
    plant: Plant, key: str, designation: str, markings: tuple[str, ...]
) -> dict[str, Id[Port]]:
    """Item `key` with one connector function `j` and a port per marking."""
    plant.item(key, designation=designation, part=make_part(plant, f"{key}-part", f"HSG-{key}"))
    return make_connector(plant, (key, "j"), markings)[1]


def _far(plant: Plant, name: str) -> Id[Port]:
    """A port on the other end of a conductor, on a plain item `far`."""
    return plant.pin("far", "f", name)


def _fit(plant: Plant, item: str, *fits: tuple[str | None, Id[Part]]) -> None:
    key = (item, "contacts")
    plant.add(
        ContactsFacet(
            id=make_id(ContactsFacet, key),
            key=key,
            subject=make_id(Item, (item,)),
            fits=tuple(ContactFit(pin=pin, part=part) for pin, part in fits),
        )
    )


def _mixed_plant() -> tuple[Plant, dict[str, Id[Port]], Id[Port]]:
    """Housing `hsg` pins 1 to 6: 1 WIRE, 2 CORE, 3 JUMPER, 4 MOUNT, 5 BUSBAR, 6 RAIL.

    A second, non-connector function `g` of `hsg` has port `1` with a WIRE as well.
    """
    plant = Plant()
    ports = _housing(plant, "hsg", "P1", tuple("123456"))
    plant.wire(ports["1"], _far(plant, "a"), key="w1")
    cable = plant.item("w9", designation="W9")
    make_core(plant, "c2", cable, (ports["2"], _far(plant, "b")), index=1)
    for pin, kind in (
        ("3", ConductorKind.JUMPER),
        ("4", ConductorKind.MOUNT),
        ("5", ConductorKind.BUSBAR),
        ("6", ConductorKind.RAIL),
    ):
        plant.wire(ports[pin], _far(plant, f"l{pin}"), key=f"l{pin}", kind=kind)
    generic = plant.pin("hsg", "g", "1")
    plant.wire(generic, _far(plant, "g"), key="wg")
    return plant, ports, generic


def test_used_pins_are_the_connector_ports_where_a_wire_or_core_lands() -> None:
    """A WIRE and a CORE count; JUMPER, MOUNT, BUSBAR, RAIL ends and non-connector ports do not."""
    plant, ports, generic = _mixed_plant()
    used = used_pins(plant.model(), HSG)
    assert used == (ports["1"], ports["2"])
    assert generic not in used


def test_a_pin_with_a_lead_on_it_is_used() -> None:
    """HA5: a LEAD end makes its connector pin used; a MOUNT end beside it still does not."""
    plant = Plant()
    ports = _housing(plant, "hsg", "P1", ("1", "2"))
    plant.wire(ports["1"], _far(plant, "a"), key="l1", kind=ConductorKind.LEAD)
    plant.wire(ports["2"], _far(plant, "b"), key="l2", kind=ConductorKind.MOUNT)
    assert used_pins(plant.model(), HSG) == (ports["1"],)


def test_used_pins_follow_port_id_order_and_skip_unwired_ports() -> None:
    """Wired in the reverse order, the pins still come back in id order; an unwired port is out."""
    plant = Plant()
    ports = _housing(plant, "hsg", "P1", ("1", "2", "3"))
    for pin in ("3", "1"):
        plant.wire(ports[pin], _far(plant, pin), key=f"w{pin}")
    assert used_pins(plant.model(), HSG) == tuple(sorted((ports["1"], ports["3"])))


def test_a_single_fit_counts_every_used_pin() -> None:
    """`pin=None` fits all used pins: two wires, two contacts."""
    plant, _ports, _generic = _mixed_plant()
    crimp = make_part(plant, "crimp", "CRIMP-1")
    _fit(plant, "hsg", (None, crimp))
    assert contact_counts(plant.model()) == {crimp: {HSG: 2}}


def test_a_pin_named_fit_beats_the_default_and_a_pin_with_no_fit_counts_nothing() -> None:
    """Pin `1` takes `special`, pin `2` the default; with no default, pin `2` counts nothing."""
    plant, _ports, _generic = _mixed_plant()
    crimp = make_part(plant, "crimp", "CRIMP-1")
    special = make_part(plant, "special", "CRIMP-S")
    _fit(plant, "hsg", (None, crimp), ("1", special))
    assert contact_counts(plant.model()) == {crimp: {HSG: 1}, special: {HSG: 1}}
    only_named = Plant()
    ports = _housing(only_named, "hsg", "P1", ("1", "2"))
    for pin in ("1", "2"):
        only_named.wire(ports[pin], _far(only_named, pin), key=f"w{pin}")
    part = make_part(only_named, "special", "CRIMP-S")
    _fit(only_named, "hsg", ("1", part))
    assert contact_counts(only_named.model()) == {part: {HSG: 1}}


def _two_housings() -> tuple[Plant, Id[Part]]:
    """`P1` with 2 wired pins and `P2` with 3, sharing one contact part."""
    plant = Plant()
    crimp = make_part(plant, "crimp", "CRIMP-1")
    for key, designation, count in (("hsg", "P1", 2), ("hsg2", "P2", 3)):
        ports = _housing(plant, key, designation, tuple("12345"))
        for pin in "12345"[:count]:
            plant.wire(ports[pin], _far(plant, f"{key}{pin}"), key=f"{key}-w{pin}")
        _fit(plant, key, (None, crimp))
    return plant, crimp


def _contact_line(plant: Plant, scope=TOP_LEVEL):
    (line,) = [line for line in bom_lines(plant.model(), scope) if line.mpn == "CRIMP-1"]
    return line


def test_the_bom_gives_one_contact_line_summing_the_used_pins_of_both_housings() -> None:
    """Five used pins over `-P1` and `-P2` make one line with count 5 and both designations."""
    plant, crimp = _two_housings()
    line = _contact_line(plant)
    assert (line.part, line.count, line.designations) == (crimp, 5, ("-P1", "-P2"))


def test_one_more_wire_raises_the_contact_count_by_one() -> None:
    """Acceptance 8: the count is read from the wires, never stored."""
    plant, _crimp = _two_housings()
    before = _contact_line(plant).count
    plant.wire(make_id(Port, ("hsg", "j", "3")), _far(plant, "extra"), key="extra")
    assert _contact_line(plant).count == before + 1


def test_an_uninstalled_or_external_housing_gives_no_contact_line() -> None:
    """Both housings out of the BOM leave no contact line."""
    plant, _crimp = _two_housings()
    for n, record in enumerate(plant.records):
        if record.id in (HSG, HSG2):
            plant.records[n] = dataclasses.replace(
                record, installed=record.id == HSG2, external=record.id == HSG2
            )
    assert "CRIMP-1" not in {line.mpn for line in bom_lines(plant.model(), TOP_LEVEL)}


def test_an_uninstalled_housing_leaves_the_other_housings_pins_only() -> None:
    """Only `-P2` is installed: count 3, one designation."""
    plant, _crimp = _two_housings()
    for n, record in enumerate(plant.records):
        if record.id == HSG:
            plant.records[n] = dataclasses.replace(record, installed=False)
    line = _contact_line(plant)
    assert (line.count, line.designations) == (3, ("-P2",))


def test_an_item_scope_narrows_the_contact_line_to_that_housing() -> None:
    """Scope `hsg2`: count 3 and only `-P2`."""
    plant, _crimp = _two_housings()
    line = _contact_line(plant, HSG2)
    assert (line.count, line.designations) == (3, ("-P2",))


def test_without_a_contacts_facet_the_bom_is_the_other_lines_unchanged() -> None:
    """Dropping the facets removes exactly the contact line and no other."""
    plant, _crimp = _two_housings()
    with_facets = bom_lines(plant.model(), TOP_LEVEL)
    plant.records[:] = [r for r in plant.records if not isinstance(r, ContactsFacet)]
    without = bom_lines(plant.model(), TOP_LEVEL)
    assert without == tuple(line for line in with_facets if line.mpn != "CRIMP-1")
    assert len(without) == len(with_facets) - 1
