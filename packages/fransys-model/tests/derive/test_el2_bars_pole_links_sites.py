"""EL-2 bars and pole links: `poles_of` pins today's pole rule over every kind pair (model-0298).

Pins 3 and 4 carry the link under test; pins 1 and 2 pair only when no link is a pole.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "vocab"))

from plant import Plant

from fransys_model.derive.pole_lists import poles_of
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import FunctionKind, LinkKind, PortRole
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, PortTemplate

_POLE_LINKS = {LinkKind.SWITCHED, LinkKind.PROTECTIVE}


def _poles(kind: FunctionKind, link: LinkKind) -> list[tuple[str, str]]:
    """The printed pole names `poles_of` finds for a template of `kind` with one `link`."""
    plant = Plant()
    part, template, _p1, _p2 = plant.relay_part()
    template = FunctionTemplate(
        id=template.id, key=template.key, part=part.id, name="fn", kind=kind
    )
    plant.records = [r for r in plant.records if r.id != template.id]
    plant.add(template)
    pins = {"1": _p1, "2": _p2}
    for name in ("3", "4", "PE"):
        role = PortRole.PE if name == "PE" else PortRole.GENERIC
        pin = PortTemplate(
            id=make_id(PortTemplate, ("relay", "fn", name)),
            key=("relay", "fn", name),
            function=template.id,
            name=name,
            role=role,
        )
        pins[name] = pin
        plant.add(pin)
    plant.add(
        InternalLink(
            id=make_id(InternalLink, ("l",)), key=("l",), a=pins["3"].id, b=pins["4"].id, kind=link
        )
    )
    model = plant.model()
    found = poles_of(model, [p.id for p in pins.values()])
    return [(a.name, b.name) for a, b in (pole.ends for pole in found)]


@pytest.mark.parametrize("kind", list(FunctionKind))
@pytest.mark.parametrize("link", list(LinkKind))
def test_a_pole_is_a_switched_or_protective_link_or_a_protections_conductive_one(
    kind: FunctionKind, link: LinkKind
) -> None:
    """A pole link wins; otherwise the non-earth pins pair 1-2, 3-4."""
    is_pole = link in _POLE_LINKS or (
        kind is FunctionKind.PROTECTION and link is LinkKind.CONDUCTIVE
    )
    assert _poles(kind, link) == ([("3", "4")] if is_pole else [("1", "2"), ("3", "4")])
