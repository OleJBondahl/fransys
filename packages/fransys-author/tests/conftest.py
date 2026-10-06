"""A tiny hand-made parts `Draft` for `fransys_author`'s own tests (WP order DEPENDENCY note).

Built directly from `fransys_model`, not from `fransys_parts`: Part A/B target the
model alone. All identity here is invented for this repo; none of it names a real product.
"""

from decimal import Decimal

import pytest

from fransys_model.kernel import Draft, Origin, make_id
from fransys_model.vocab import (
    CableProductFacet,
    ConnectorFacet,
    FunctionKind,
    FunctionTemplate,
    Gender,
    InternalLink,
    LinkKind,
    Part,
    PartCategory,
    PartLibrary,
    PortRole,
    PortTemplate,
)

_ORIGIN = Origin(file="<parts fixture>", line=1, note="test catalogue")


def _library(draft: Draft, name: str) -> PartLibrary:
    key = ("part_library", name)
    library = PartLibrary(id=make_id(PartLibrary, key), key=key, name=name, version="1.0.0")
    draft.add(library, origin=_ORIGIN)
    return library


def _part(  # noqa: PLR0913 -- test-fixture builder: every field a `Part` needs, once
    draft: Draft,
    library: PartLibrary,
    *,
    manufacturer: str,
    mpn: str,
    category: PartCategory,
    letter: str,
) -> Part:
    key = ("part", manufacturer, mpn)
    part = Part(
        id=make_id(Part, key),
        key=key,
        mpn=mpn,
        manufacturer=manufacturer,
        description=f"test part {mpn}",
        category=category,
        class_code=letter,
        library=library.id,
    )
    draft.add(part, origin=_ORIGIN)
    return part


def _function(draft: Draft, part: Part, name: str, kind: FunctionKind) -> FunctionTemplate:
    key = (*part.key, "function", name)
    function = FunctionTemplate(
        id=make_id(FunctionTemplate, key), key=key, part=part.id, name=name, kind=kind
    )
    draft.add(function, origin=_ORIGIN)
    return function


def _port(
    draft: Draft, function: FunctionTemplate, name: str, role: PortRole = PortRole.GENERIC
) -> PortTemplate:
    key = (*function.key, "port", name)
    port = PortTemplate(
        id=make_id(PortTemplate, key), key=key, function=function.id, name=name, role=role
    )
    draft.add(port, origin=_ORIGIN)
    return port


def _link(
    draft: Draft, function: FunctionTemplate, a: PortTemplate, b: PortTemplate, kind: LinkKind
) -> None:
    key = (*function.key, "link", a.name, b.name)
    draft.add(
        InternalLink(id=make_id(InternalLink, key), key=key, a=a.id, b=b.id, kind=kind),
        origin=_ORIGIN,
    )


def build_test_catalogue() -> Draft:
    """A `Draft` with one library and: a relay, a terminal, a cable and a connector part.

    Also two parts sharing one MPN across two manufacturers (spec A5's ambiguity case).
    """
    draft = Draft()
    library = _library(draft, "test-parts")

    relay = _part(
        draft,
        library,
        manufacturer="TestCo",
        mpn="TEST-RLY-2CO",
        category=PartCategory.ELECTROMECHANICAL,
        letter="K",
    )
    coil = _function(draft, relay, "coil", FunctionKind.COIL)
    _port(draft, coil, "A1")
    _port(draft, coil, "A2")
    no1 = _function(draft, relay, "no_1", FunctionKind.CONTACT_NO)
    p13, p14 = _port(draft, no1, "13"), _port(draft, no1, "14")
    _link(draft, no1, p13, p14, LinkKind.SWITCHED)
    co2 = _function(draft, relay, "co_2", FunctionKind.CONTACT_CO)
    p21, p22, p24 = _port(draft, co2, "21"), _port(draft, co2, "22"), _port(draft, co2, "24")
    _link(draft, co2, p21, p22, LinkKind.SWITCHED)
    _link(draft, co2, p21, p24, LinkKind.SWITCHED)

    # two functions sharing a marking (spec A4's ambiguous-marking case at item()/[] level).
    clash = _part(
        draft,
        library,
        manufacturer="TestCo",
        mpn="TEST-CLASH",
        category=PartCategory.GENERIC,
        letter="A",
    )
    _port(draft, _function(draft, clash, "co_1", FunctionKind.CONTACT_CO), "13")
    _port(draft, _function(draft, clash, "co_2", FunctionKind.CONTACT_CO), "13")

    terminal = _part(
        draft,
        library,
        manufacturer="TestCo",
        mpn="TEST-TB",
        category=PartCategory.TERMINAL,
        letter="X",
    )
    tfn = _function(draft, terminal, "terminal", FunctionKind.TERMINAL)
    inner = _port(draft, tfn, "internal", PortRole.INTERNAL)
    outer = _port(draft, tfn, "external", PortRole.EXTERNAL)
    _link(draft, tfn, inner, outer, LinkKind.CONDUCTIVE)

    # a "terminal" with no external port: exercises Terminal.outer's own not-found case.
    one_sided = _part(
        draft,
        library,
        manufacturer="TestCo",
        mpn="TEST-TB-ONE-SIDED",
        category=PartCategory.TERMINAL,
        letter="X",
    )
    _port(
        draft,
        _function(draft, one_sided, "terminal", FunctionKind.TERMINAL),
        "internal",
        PortRole.INTERNAL,
    )

    cable = _part(
        draft,
        library,
        manufacturer="TestCo",
        mpn="TEST-CBL-2",
        category=PartCategory.CABLE,
        letter="W",
    )
    key = (*cable.key, "cable_product")
    draft.add(
        CableProductFacet(
            id=make_id(CableProductFacet, key),
            key=key,
            subject=cable.id,
            core_colours=("brown", "blue"),
            gauge_mm2=Decimal("0.75"),
            shielded=False,
        ),
        origin=_ORIGIN,
    )

    housing = _part(
        draft,
        library,
        manufacturer="TestCo",
        mpn="TEST-CONN-2P",
        category=PartCategory.CONNECTOR,
        letter="X",
    )
    conn = _function(draft, housing, "conn", FunctionKind.CONNECTOR)
    _port(draft, conn, "1")
    _port(draft, conn, "2")
    key = (*conn.key, "connector")
    draft.add(
        ConnectorFacet(
            id=make_id(ConnectorFacet, key),
            key=key,
            subject=conn.id,
            style="test",
            pincount=2,
            gender=Gender.FEMALE,
        ),
        origin=_ORIGIN,
    )

    edge = _part(
        draft,
        library,
        manufacturer="TestCo",
        mpn="TEST-EDGE-2P",
        category=PartCategory.CONNECTOR,
        letter="X",
    )
    econn = _function(draft, edge, "conn", FunctionKind.CONNECTOR)
    _port(draft, econn, "1")
    _port(draft, econn, "2")

    # spec A5: one MPN, two manufacturers -> ambiguous at item() time.
    _part(
        draft,
        library,
        manufacturer="Alpha",
        mpn="TEST-SHARED",
        category=PartCategory.GENERIC,
        letter="A",
    )
    _part(
        draft,
        library,
        manufacturer="Beta",
        mpn="TEST-SHARED",
        category=PartCategory.GENERIC,
        letter="A",
    )

    return draft


@pytest.fixture
def parts() -> Draft:
    """A fresh test catalogue `Draft` (spec A1: `Design(parts)`)."""
    return build_test_catalogue()
