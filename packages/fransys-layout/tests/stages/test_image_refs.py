"""layout-0184: with no home drawn, the fallback takes a replica of the own unit first."""

from dataclasses import replace
from typing import Any

from samples import PROFILE, SHEET, hid, page_plan, placed
from test_images import MARKS, _relay_function

from fransys_layout.stages import RequestPartner
from fransys_layout.stages.image_refs import holds_list, listed
from fransys_layout.stages.images import ImageInputs, contact_images

OWN = hid("unit", 1)
PARENT = hid("unit", 9)


def test_a_function_with_no_home_refers_inside_its_own_units_set() -> None:
    """The coil of unit OWN has no home: replicas on its own set 2 and a black box in set 1.

    A boundary rail terminal has this shape. The contact is drawn in set 2, so its reference
    names the replica there (`set 2`), never the parent's black box in set 1.
    """
    coil = replace(_relay_function(1, "coil", "A1", "A2"), unit=OWN)
    make = replace(_relay_function(2, "contact_no", "13", "14"), unit=OWN)
    box = placed(1, x=0, y=0, name="box")
    rail = replace(placed(1, x=0, y=0, name="rail"), drawing_set=2)
    contact = replace(placed(2, x=200, y=0, name="own"), drawing_set=2)
    plans = (
        page_plan(("box",)),
        replace(page_plan(("rail", "own")), drawing_set=2),
    )
    replicas: dict[Any, Any] = {
        (("invented", "box"), coil.function): PARENT,
        (("invented", "rail"), coil.function): OWN,
    }
    inputs = ImageInputs((make, coil), SHEET, PROFILE, MARKS, no_place="N/A", replicas=replicas)
    _, requests = contact_images(plans, [((box,), ()), ((rail, contact), ())], inputs)
    (request,) = requests
    assert request.partners == (
        RequestPartner(port=coil.ports[0].port, drawing_set=2, page=1, x=0),
    )


def test_a_switch_groups_lead_lists_every_contact_and_the_other_refers_to_it() -> None:
    """layout-0237: the lead (function 2) holds the table and lists itself; 3 takes the reference.

    Both switches are blocks of one head (item 9): neither is a contact by kind.
    """
    head = hid("item", 9)
    lead = replace(
        _relay_function(2, "switch", "13", "14", item=2), switch_group=head, actuator=True
    )
    other = replace(
        _relay_function(3, "switch", "21", "22", item=3), switch_group=head, actuator=False
    )
    assert (listed(lead), holds_list(lead), listed(other), holds_list(other)) == (
        True,
        True,
        True,
        False,
    )
    owners = {lead.function: head, other.function: head}
    plans = (page_plan(("a", "b")),)
    page = (placed(2, x=0, y=0, name="a"), placed(3, x=200, y=0, name="b"))
    inputs = ImageInputs((lead, other), SHEET, PROFILE, MARKS, owners, no_place="N/A")
    pages, requests = contact_images(plans, [(page, ())], inputs)
    (table,) = (one for one in pages[0][1] if one.slot == "contacts")
    assert table.subject == lead.function
    assert [p.port for p in table.partners] == [lead.ports[0].port, other.ports[0].port]
    (request,) = requests
    assert (request.subject, request.partners[0].port) == (other.function, lead.ports[0].port)
