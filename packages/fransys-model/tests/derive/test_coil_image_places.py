"""Tests: a coil's contact table prints each reached contact's place once the caller has it."""

from plant import Plant
from test_el2_contacts_sites import IDS, MODEL, _part

from fransys_model.derive import coil_table_texts, owned_contacts
from fransys_model.derive.contact_image import coil_image_cells, table_contacts
from fransys_model.kernel import make_id
from fransys_model.vocab import FunctionKind
from fransys_model.vocab.enums import PortRole
from fransys_model.vocab.tables import functions
from fransys_model.vocab.templates import FunctionTemplate, PortTemplate

G = PortRole.GENERIC


def _contact(plant: Plant, item, name: str, part, kind):
    """A contact function `name` of `item` from `part`'s one template, each port wired."""
    template = make_id(FunctionTemplate, (part.key[0], "fn"))
    function = plant.function(item, name, template=template, kind=kind)
    for pin in (p for p in plant.records if isinstance(p, PortTemplate) and p.function == template):
        port = plant.port(function, pin.name, template=pin.id)
        plant.wire(port, plant.pin("bus", "bus", f"{name}-{pin.name}"), key=f"w-{name}-{pin.name}")
    return function


def _contactor():
    """One contactor item: its coil, a NO and an NC contact."""
    plant, k = Plant(), FunctionKind
    no = _part(plant, "no", k.CONTACT_NO, {"13": G, "14": G}, [("13", "14", None)])
    nc = _part(plant, "nc", k.CONTACT_NC, {"21": G, "22": G}, [("21", "22", None)])
    item = plant.item("k1")
    coil = plant.function(item, "coil", kind=k.COIL)
    no_f = _contact(plant, item, "no", no, k.CONTACT_NO)
    nc_f = _contact(plant, item, "nc", nc, k.CONTACT_NC)
    return plant.model(), coil, no_f, nc_f


def test_a_reached_contact_prints_its_place_after_its_mark() -> None:
    model, coil, no, nc = _contactor()
    assert set(owned_contacts(model, functions(model)[coil].item)) == {no, nc}
    assert coil_image_cells(model, coil) == (["13-14"], ["21-22"])
    assert coil_image_cells(model, coil, {no: "2A", nc: "p1:3B"}) == (["13-14 2A"], ["21-22 p1:3B"])
    assert coil_table_texts(model, coil, {no: "2A"})[1:] == (("13-14 2A", "21-22"),)


def test_a_contact_without_a_place_keeps_its_bare_mark() -> None:
    model, coil, no, _ = _contactor()
    assert coil_image_cells(model, coil, {})[0] == ["13-14"]
    assert coil_image_cells(model, coil, {no: "1A"})[1] == ["21-22"]


def test_a_coil_owns_its_contacts_and_a_lead_switch_its_actuated_group() -> None:
    model, coil, no, nc = _contactor()
    assert set(table_contacts(model, coil)) == {no, nc}
    assert table_contacts(model, no) == ()
    sw_nc, sw_no = IDS["sw_nc"], IDS["sw_no"]
    assert table_contacts(MODEL, sw_nc) == (sw_nc, sw_no)
    assert table_contacts(MODEL, sw_no) == ()
    assert coil_image_cells(MODEL, sw_nc) == (["43-44"], ["31-32"])
    assert coil_table_texts(MODEL, sw_no) == ()
