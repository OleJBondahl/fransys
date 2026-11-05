"""EL-2 bars and pole links: `poles_of` pins today's pole rule over every kind pair (model-0298).

Pins 3 and 4 carry the link under test; pins 1 and 2 pair only when no link is a pole.
"""

import pytest
from plant import Plant

from fransys_model.derive import functions
from fransys_model.derive.pole_lists import function_poles, poles_of
from fransys_model.elecdef import LinkKind, PinRole
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import FunctionKind, PortBoundary
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, PortTemplate

_POLE_LINKS = {LinkKind.SWITCHED, LinkKind.PROTECTIVE}


def _poles(kind: FunctionKind, link: LinkKind) -> list[tuple[str, str]]:
    """The printed pole names `poles_of` finds for a template of `kind` with one `link`."""
    plant = Plant()
    part, template, _p1, _p2 = plant.relay_part()
    template = FunctionTemplate(id=template.id, key=template.key, part=part.id, name="fn", kind=kind)
    plant.records = [r for r in plant.records if r.id != template.id]
    plant.add(template)
    pins = {"1": _p1, "2": _p2}
    for name in ("3", "4", "PE"):
        role = PinRole.PE if name == "PE" else PortBoundary.GENERIC
        pin = PortTemplate(
            id=make_id(PortTemplate, ("relay", "fn", name)),
            key=("relay", "fn", name),
            function=template.id,
            name=name,
            boundary=role if isinstance(role, PortBoundary) else PortBoundary.GENERIC,
            pin_role=role if isinstance(role, PinRole) else None,
        )
        pins[name] = pin
        plant.add(pin)
    plant.add(InternalLink(id=make_id(InternalLink, ("l",)), key=("l",), a=pins["3"].id, b=pins["4"].id, kind=link))
    model = plant.model()
    found = poles_of(model, [p.id for p in pins.values()])
    return [(a.name, b.name) for a, b in (pole.ends for pole in found)]


@pytest.mark.parametrize("kind", list(FunctionKind))
@pytest.mark.parametrize("link", list(LinkKind))
def test_a_pole_is_a_switched_or_protective_link_or_a_protections_conductive_one(kind: FunctionKind, link: LinkKind) -> None:
    """A pole link wins; otherwise the non-earth pins pair 1-2, 3-4."""
    is_pole = link in _POLE_LINKS or (kind is FunctionKind.PROTECTION and link is LinkKind.CONDUCTIVE)
    assert _poles(kind, link) == ([("3", "4")] if is_pole else [("1", "2"), ("3", "4")])


def test_a_function_poles_fall_back_on_every_link_when_none_is_a_pole() -> None:
    """`function_poles`: a conductive link of a generic function is no pole by role, yet it is the fallback pole."""
    plant = Plant()
    _part, template, p1, p2 = plant.relay_part()
    plant.link(p1, p2, LinkKind.CONDUCTIVE)
    fid = plant.function(plant.item("k1"), "fn", template=template.id)
    found = function_poles(plant.model(), functions(plant.model())[fid])
    assert [(a.name, b.name) for a, b in (pole.ends for pole in found)] == [("1", "2")]
