"""Tests: the switches one actuator moves, and the lead (model-0237, ACTUATOR-ONCE AO1, AO2).

A head states `operated_by`; its switch blocks are one group, listed in contact-list order.
"""

from plant import Plant

from fransys_model.derive import (
    actuated_group,
    contact_list_key,
    lead_switch,
    operating_item,
)
from fransys_model.derive.contact_entries import contact_entries
from fransys_model.kernel import make_id
from fransys_model.vocab import FunctionKind, OperatedBy, PartCategory
from fransys_model.vocab.enums import LinkKind, LinkRest, PortRole
from fransys_model.vocab.tables import functions
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, Part, PortTemplate

CLOSED, OPEN = LinkRest.CLOSED, LinkRest.OPEN


def _part(plant: Plant, key: str, operated: OperatedBy | None, kind: FunctionKind, poles) -> Part:
    """Add a part with one function of `kind` and switched `poles` as (a, b, rest) names."""
    part = Part(
        id=make_id(Part, (key,)),
        key=(key,),
        mpn=f"EXAMPLE-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="S",
        operated_by=operated,
    )
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (key, "fn")),
        key=(key, "fn"),
        part=part.id,
        name="fn",
        kind=kind,
    )
    names = sorted({n for a, b, _ in poles for n in (a, b)})
    pins = {
        n: PortTemplate(
            id=make_id(PortTemplate, (key, "fn", n)),
            key=(key, "fn", n),
            function=template.id,
            name=n,
            role=PortRole.GENERIC,
        )
        for n in names
    }
    plant.add(part, template, *pins.values())
    for a, b, rest in poles:
        link = InternalLink(
            id=make_id(InternalLink, (key, a, b)),
            key=(key, a, b),
            a=pins[a].id,
            b=pins[b].id,
            kind=LinkKind.SWITCHED,
            rest=rest,
        )
        plant.add(link)
    return part


def _switch(plant, key, part, parent=None, *, wired=True):
    """An item of `part` with its one switch function and ports; wired to a bus when `wired`."""
    item = plant.item(key, part=part.id, parent=parent)
    template = make_id(FunctionTemplate, (part.key[0], "fn"))
    function = plant.function(item, "fn", template=template, kind=FunctionKind.SWITCH)
    for pin in (p for p in plant.records if isinstance(p, PortTemplate) and p.function == template):
        port = plant.port(function, pin.name, template=pin.id)
        if wired:
            plant.wire(
                port, plant.pin("bus", "bus", f"{key}-{pin.name}"), key=f"w-{key}-{pin.name}"
            )
    return function


def _head(plant: Plant):
    return plant.item(
        "head", part=_part(plant, "head", OperatedBy.MUSHROOM, FunctionKind.GENERIC, []).id
    )


def _three_blocks(plant: Plant, wired=(True, True, True)):
    head = _head(plant)
    pairs = ("11", "12"), ("21", "22"), ("31", "32")
    out = []
    for k, (a, b) in enumerate(pairs):
        part = _part(plant, f"nc{k}", None, FunctionKind.SWITCH, [(a, b, CLOSED)])
        out.append(_switch(plant, f"block{k}", part, head, wired=wired[k]))
    return head, out


def test_three_blocks_under_a_head_are_one_group_in_list_order() -> None:
    plant = Plant()
    head, blocks = _three_blocks(plant)
    model = plant.model()
    assert operating_item(model, blocks[2]) == head
    assert [actuated_group(model, b) for b in blocks] == [tuple(blocks)] * 3
    assert lead_switch(model, blocks[2]) == blocks[0]


def test_the_lead_skips_an_unwired_first_block() -> None:
    plant = Plant()
    _, blocks = _three_blocks(plant, wired=(False, True, True))
    assert lead_switch(plant.model(), blocks[0]) == blocks[1]


def test_a_two_pole_switch_lists_each_pole_by_its_rest_and_is_a_group_of_one() -> None:
    """Amendment 1: one function with several poles is a group of one (AO6)."""
    plant = Plant()
    part = _part(
        plant,
        "dev",
        OperatedBy.TURN,
        FunctionKind.SWITCH,
        [("13", "14", OPEN), ("21", "22", CLOSED)],
    )
    sw = _switch(plant, "dev", part)
    model = plant.model()
    no, nc = contact_entries(model, functions(model)[sw])
    assert [e[2] for e in no] == ["13-14"]
    assert [e[2] for e in nc] == ["21-22"]
    assert lead_switch(model, sw) == sw
    assert actuated_group(model, sw) == (sw,)


def test_a_switch_with_no_operator_and_a_contact_have_no_group() -> None:
    plant = Plant()
    sw = _switch(
        plant, "plain", _part(plant, "plain", None, FunctionKind.SWITCH, [("1", "2", CLOSED)])
    )
    contact = plant.function(plant.item("k"), "no", kind=FunctionKind.CONTACT_NO)
    model = plant.model()
    assert operating_item(model, sw) is None
    assert actuated_group(model, sw) == ()
    assert lead_switch(model, sw) is None
    assert actuated_group(model, contact) == ()
    assert lead_switch(model, contact) is None


def test_a_three_pole_contact_lists_before_a_one_pole_one() -> None:
    plant = Plant()
    three = _part(
        plant,
        "three",
        OperatedBy.TURN,
        FunctionKind.SWITCH,
        [("1", "2", OPEN), ("3", "4", OPEN), ("5", "6", OPEN)],
    )
    one = _part(plant, "one", OperatedBy.TURN, FunctionKind.SWITCH, [("13", "14", OPEN)])
    a, b = _switch(plant, "a", one), _switch(plant, "b", three)
    model = plant.model()
    assert contact_list_key(model, b) < contact_list_key(model, a)
