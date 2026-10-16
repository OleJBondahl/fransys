"""Tests: the contact sites of EL-2 (model-0291) give the same answers whatever they read.

Characterisation over one planted model: each public function of `accessory_blocks`,
`actuated`, `contact_entries`, `contact_lines` and `contacts` is called on every function or
item of it and the output is pinned. The file passes before the sites read roles, and after.
"""

from typing import Any

from plant import Plant

from fransys_model.derive import actuated_group, lead_switch, operated_by, owned_contacts
from fransys_model.derive.accessory_blocks import is_contact_block, operating_item
from fransys_model.derive.contact_entries import contact_entries, contact_list_key
from fransys_model.derive.contact_lines import used_pins
from fransys_model.kernel import Id, make_id
from fransys_model.vocab import FunctionKind, OperatedBy, PartCategory
from fransys_model.vocab.enums import ConductorKind, LinkKind, LinkRest, PortRole
from fransys_model.vocab.tables import functions, items, ports
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, Part, PortTemplate

CLOSED, OPEN = LinkRest.CLOSED, LinkRest.OPEN
G, C, B, M = PortRole.GENERIC, PortRole.COMMON, PortRole.BREAK, PortRole.MAKE


def _part(  # noqa: PLR0913 -- one param per part field the tests vary
    plant: Plant, key: str, kind: FunctionKind, roles: dict[str, PortRole], links, *, op=None
):
    """A part with one template of `kind`, pins `roles` and SWITCHED `links` (a, b, rest)."""
    part = Part(
        id=make_id(Part, (key,)),
        key=(key,),
        mpn=f"EXAMPLE-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="S",
        operated_by=op,
    )
    tpl = FunctionTemplate(
        id=make_id(FunctionTemplate, (key, "fn")),
        key=(key, "fn"),
        part=part.id,
        name="fn",
        kind=kind,
    )
    pins = {
        n: PortTemplate(
            id=make_id(PortTemplate, (key, "fn", n)),
            key=(key, "fn", n),
            function=tpl.id,
            name=n,
            role=r,
        )
        for n, r in roles.items()
    }
    plant.add(part, tpl, *pins.values())
    for a, b, rest in links:
        plant.add(
            InternalLink(
                id=make_id(InternalLink, (key, a, b)),
                key=(key, a, b),
                a=pins[a].id,
                b=pins[b].id,
                kind=LinkKind.SWITCHED,
                rest=rest,
            )
        )
    return part


def _device(plant: Plant, key: str, part: Part, parent=None, *, kind: FunctionKind):
    """An item of `part` (under `parent`) with its one function, a port per pin, each wired."""
    item = plant.item(key, part=part.id, parent=parent)
    template = make_id(FunctionTemplate, (part.key[0], "fn"))
    function = plant.function(item, "fn", template=template, kind=kind)
    for pin in (p for p in plant.records if isinstance(p, PortTemplate) and p.function == template):
        port = plant.port(function, pin.name, template=pin.id)
        plant.wire(port, plant.pin("bus", "bus", f"{key}-{pin.name}"), key=f"w-{key}-{pin.name}")
    return function


def _planted() -> tuple[Any, dict[str, Id[Any]]]:
    """Contacts of every kind, a head over two switch blocks, a connector with every conductor."""
    plant, ids = Plant(), {}
    k = FunctionKind
    no = _part(plant, "no", k.CONTACT_NO, {"13": G, "14": G}, [("13", "14", None)])
    nc = _part(plant, "nc", k.CONTACT_NC, {"21": G, "22": G}, [("21", "22", None)])
    co = _part(
        plant,
        "co",
        k.CONTACT_CO,
        {"11": C, "12": B, "14": M},
        [("11", "12", None), ("11", "14", None)],
    )
    head = plant.item(
        "head", part=_part(plant, "head", k.GENERIC, {}, [], op=OperatedBy.MUSHROOM).id
    )
    sw_nc = _part(plant, "sw_nc", k.SWITCH, {"31": G, "32": G}, [("31", "32", CLOSED)])
    sw_no = _part(plant, "sw_no", k.SWITCH, {"43": G, "44": G}, [("43", "44", OPEN)])
    ids["no"] = _device(plant, "no", no, kind=k.CONTACT_NO)
    ids["nc"] = _device(plant, "nc", nc, kind=k.CONTACT_NC)
    ids["co"] = _device(plant, "co", co, kind=k.CONTACT_CO)
    ids["sw_nc"] = _device(plant, "sw_nc", sw_nc, head, kind=k.SWITCH)
    ids["sw_no"] = _device(plant, "sw_no", sw_no, head, kind=k.SWITCH)
    ids["coil"] = plant.function(plant.item("coil"), "fn", kind=k.COIL)
    ids["head"] = head
    conn = plant.function(plant.item("conn"), "fn", kind=k.CONNECTOR)
    ids["conn"] = conn
    for kind in ConductorKind:
        port = plant.port(conn, kind.value)
        other = plant.pin("far", "far", kind.value)
        if kind is ConductorKind.CORE:
            plant.core(port, other, key=kind.value, carrier=plant.item("cable"))
        else:
            plant.wire(port, other, key=kind.value, kind=kind)
    return plant.model(), ids


MODEL, IDS = _planted()


ITEM = {i: r.key[0] for i, r in items(MODEL).items()}
OWNER = {i: ITEM[f.item] for i, f in functions(MODEL).items()}


def test_which_items_are_contact_blocks_with_and_without_held_switches() -> None:
    got = {
        ITEM[i]: (is_contact_block(MODEL, i), is_contact_block(MODEL, i, held_switches=False))
        for i in items(MODEL)
        if is_contact_block(MODEL, i)
    }
    assert got == {
        "no": (True, True),
        "nc": (True, True),
        "co": (True, True),
        "sw_no": (True, False),
        "sw_nc": (True, False),
    }


def test_a_device_owns_its_contacts_and_not_a_held_switch() -> None:
    got = {ITEM[i]: [OWNER[f] for f in owned_contacts(MODEL, i)] for i in items(MODEL)}
    assert {k: v for k, v in got.items() if v} == {"no": ["no"], "nc": ["nc"], "co": ["co"]}


def test_contact_entries_and_the_list_key_of_each_function() -> None:
    got = {k: contact_entries(MODEL, functions(MODEL)[IDS[k]]) for k in IDS if k != "head"}
    assert got == {
        "no": ([(False, 13, "13-14")], []),
        "nc": ([], [(False, 21, "21-22")]),
        "co": ([(True, 11, "11-14")], [(True, 11, "11-12")]),
        "sw_nc": ([], [(False, 31, "31-32")]),
        "sw_no": ([(False, 43, "43-44")], []),
        "coil": ([], []),
        "conn": ([], []),
    }
    keys = {k: contact_list_key(MODEL, IDS[k]) for k in ("no", "co", "coil")}
    assert [keys["no"][0], keys["co"][0], keys["coil"]] == [True, False, (True, ())]


def test_the_switches_one_head_moves_are_a_group_led_by_the_first() -> None:
    sw_nc, sw_no = IDS["sw_nc"], IDS["sw_no"]
    for each in (sw_nc, sw_no):
        assert operating_item(MODEL, each) == IDS["head"]
        assert operated_by(MODEL, each) is OperatedBy.MUSHROOM
        assert actuated_group(MODEL, each) == (sw_nc, sw_no)
        assert lead_switch(MODEL, each) == sw_nc
    for other in ("no", "nc", "co", "coil"):
        assert operating_item(MODEL, IDS[other]) is None
        assert actuated_group(MODEL, IDS[other]) == ()
        assert lead_switch(MODEL, IDS[other]) is None


def test_a_used_pin_is_where_a_wire_core_or_lead_lands_not_a_jumper() -> None:
    item = functions(MODEL)[IDS["conn"]].item
    assert sorted(ports(MODEL)[p].name for p in used_pins(MODEL, item)) == ["core", "lead", "wire"]
