"""The catalogue's internal links, each indexed under the part that owns its port."""

import fransys_parts
import pytest
from fransys_author.design import Design

from fransys_model.elecdef import LinkKind
from fransys_model.kernel import Draft, Origin, make_id
from fransys_model.vocab import FunctionTemplate, InternalLink, PortBoundary, PortTemplate

_ORIGIN = Origin(file="<catalogue-guards fixture>", line=1, note="test catalogue")


@pytest.fixture(scope="module")
def demo():
    return fransys_parts.load("demo_parts")


def test_the_feedthrough_terminal_s_internal_link_is_indexed_in_the_catalogue(demo):
    """`_catalogue.build_catalogue`'s InternalLink-indexing loop (`_catalogue.py:169-176`)
    attributes `terminal-feedthrough-2_5.toml`'s one link to its own part, keyed by the owning
    function template's part, not by the link's own id or table order."""
    catalogue = Design(demo)._catalogue
    part = catalogue.find("DEMO-TB-2.5")
    (template,) = catalogue.function_templates[part.id]
    ports = {port.name: port for port in catalogue.port_templates[template.id]}
    (link,) = catalogue.internal_links[part.id]
    assert {link.a, link.b} == {ports["internal"].id, ports["external"].id}


def test_an_internal_link_whose_port_owns_no_function_template_raises_loudly():
    """Ruling 2026-09-27, S-A: `_catalogue.build_catalogue`'s InternalLink-indexing
    loop indexes `port_template_function` and `function_template_part` directly, with no
    guard. A part file can never produce this state (parts lint's `LINK_PORT_UNKNOWN` rejects
    a link naming a port its own function does not own), so it is hand-built here: two port
    """
    draft = Draft()
    phantom_function = make_id(FunctionTemplate, ("phantom", "function"))
    port_a = PortTemplate(
        id=make_id(PortTemplate, ("phantom", "a")),
        key=("phantom", "a"),
        function=phantom_function,
        name="a",
        boundary=PortBoundary.GENERIC,
    )
    port_b = PortTemplate(
        id=make_id(PortTemplate, ("phantom", "b")),
        key=("phantom", "b"),
        function=phantom_function,
        name="b",
        boundary=PortBoundary.GENERIC,
    )
    draft.add(port_a, origin=_ORIGIN)
    draft.add(port_b, origin=_ORIGIN)
    draft.add(
        InternalLink(
            id=make_id(InternalLink, ("phantom", "link")),
            key=("phantom", "link"),
            a=port_a.id,
            b=port_b.id,
            kind=LinkKind.CONDUCTIVE,
        ),
        origin=_ORIGIN,
    )
    with pytest.raises(KeyError):
        Design(draft)
