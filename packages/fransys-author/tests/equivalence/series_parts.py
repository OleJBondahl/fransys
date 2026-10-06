"""Invented stub parts for the series tests (EA5, EA6): breaker, contactor, motor, PSU, cables.

`series_library()` extends `build_test_catalogue()`. Each part lists its F9 facts in one comment.
"""

from decimal import Decimal

import fransys_parts

from fransys_model.kernel import Draft, make_id, merge
from fransys_model.vocab import (
    CableProductFacet,
    ConductorMark,
    FunctionKind,
    FunctionTemplate,
    LinkKind,
    Operating,
    OperatingFacet,
    Part,
    PartCategory,
    PoleSide,
    PortRole,
    PortTemplate,
    ProtectionType,
)

from ..conftest import _ORIGIN, _function, _library, _link, _part, build_test_catalogue  # noqa: TID252 -- importlib mode puts tests/ on no path

LINE, LOAD = PoleSide.LINE, PoleSide.LOAD
L1, L2, L3 = ConductorMark.L1, ConductorMark.L2, ConductorMark.L3
PLUS, MINUS = ConductorMark.L_PLUS, ConductorMark.L_MINUS


def _pin(  # noqa: PLR0913, PLR0917 -- test builder: one pin with every fact `_port` lacks
    draft: Draft,
    function: FunctionTemplate,
    name: str,
    side: PoleSide | None = None,
    mark: ConductorMark | None = None,
    role: PortRole = PortRole.GENERIC,
) -> PortTemplate:
    key = (*function.key, "port", name)
    port = PortTemplate(
        id=make_id(PortTemplate, key),
        key=key,
        function=function.id,
        name=name,
        role=role,
        pole_side=side,
        conductor_mark=mark,
    )
    draft.add(port, origin=_ORIGIN)
    return port


def _poles(  # noqa: PLR0913, PLR0917 -- test builder: one function and its pole pins
    draft: Draft,
    part: Part,
    name: str,
    kind: FunctionKind,
    link: LinkKind,
    pairs: list[tuple[str, str]],
    *,
    sides: bool = True,
    protection: ProtectionType | None = None,
) -> FunctionTemplate:
    """A function with one link per `(line, load)` pair, declared in the given order."""
    key = (*part.key, "function", name)
    function = FunctionTemplate(
        id=make_id(FunctionTemplate, key),
        key=key,
        part=part.id,
        name=name,
        kind=kind,
        protection_type=protection,
    )
    draft.add(function, origin=_ORIGIN)
    for a, b in pairs:
        pa = _pin(draft, function, a, LINE if sides else None)
        pb = _pin(draft, function, b, LOAD if sides else None)
        _link(draft, function, pa, pb, link)
    return function


_THREE = [("1", "2"), ("3", "4"), ("5", "6")]


def breaker(
    draft: Draft, lib, mpn: str = "TEST-MCB-3P", order=_THREE, *, sides: bool = True
) -> None:
    """Facts: main PROTECTIVE poles 1/2 3/4 5/6, odd pin LINE (none when `sides` is False)."""
    part = _part(
        draft, lib, manufacturer="TestCo", mpn=mpn, category=PartCategory.PROTECTION, letter="Q"
    )
    _poles(
        draft, part, "main", FunctionKind.PROTECTION, LinkKind.PROTECTIVE, order,
        sides=sides, protection=ProtectionType.MCB,
    )  # fmt: skip


def _contactor(draft: Draft, lib) -> None:
    """Facts: main 3 SWITCHED poles 1/2 3/4 5/6; aux NO 13/14; coil A1 LINE, A2 LOAD mark L-."""
    part = _part(
        draft, lib, manufacturer="TestCo", mpn="TEST-KM-3P",
        category=PartCategory.ELECTROMECHANICAL, letter="K",
    )  # fmt: skip
    _poles(draft, part, "main", FunctionKind.CONTACT_NO, LinkKind.SWITCHED, _THREE)
    _poles(draft, part, "aux", FunctionKind.CONTACT_NO, LinkKind.SWITCHED, [("13", "14")])
    coil = _function(draft, part, "coil", FunctionKind.COIL)
    _pin(draft, coil, "A1", LINE)
    _pin(draft, coil, "A2", LOAD, MINUS)


def _overload(draft: Draft, lib) -> None:
    """Facts: main 3 PROTECTIVE poles 1/2 3/4 5/6; aux NC 95/96 LINE/LOAD; pass pin A2 mark L-."""
    part = _part(
        draft, lib, manufacturer="TestCo", mpn="TEST-OL-3P",
        category=PartCategory.PROTECTION, letter="F",
    )  # fmt: skip
    _poles(
        draft, part, "main", FunctionKind.PROTECTION, LinkKind.PROTECTIVE, _THREE,
        protection=ProtectionType.OVERLOAD,
    )  # fmt: skip
    _poles(draft, part, "aux", FunctionKind.CONTACT_NC, LinkKind.SWITCHED, [("95", "96")])
    _pin(draft, _function(draft, part, "pass", FunctionKind.GENERIC), "A2", None, MINUS)


def _buttons(draft: Draft, lib) -> None:
    """Facts: NC 21/22 and NO 13/14, one SWITCHED pole each, odd pin LINE."""
    for mpn, kind, pair in (
        ("TEST-BTN-NC", FunctionKind.CONTACT_NC, ("21", "22")),
        ("TEST-BTN-NO", FunctionKind.CONTACT_NO, ("13", "14")),
    ):
        part = _part(
            draft, lib, manufacturer="TestCo", mpn=mpn,
            category=PartCategory.ELECTROMECHANICAL, letter="S",
        )  # fmt: skip
        _poles(draft, part, "contact", kind, LinkKind.SWITCHED, [pair])


def _loads(draft: Draft, lib) -> None:
    """Facts: motor U V W marks L1 L2 L3, no links, PE pin role PE; coil A1/A2 no facts."""
    motor = _part(
        draft, lib, manufacturer="TestCo", mpn="TEST-MOTOR-3P",
        category=PartCategory.ELECTROMECHANICAL, letter="M",
    )  # fmt: skip
    load = _function(draft, motor, "load", FunctionKind.LOAD)
    for name, mark in (("U", L1), ("V", L2), ("W", L3)):
        _pin(draft, load, name, None, mark)
    _pin(draft, load, "PE", None, None, PortRole.PE)
    coil = _part(
        draft, lib, manufacturer="TestCo", mpn="TEST-COIL",
        category=PartCategory.ELECTROMECHANICAL, letter="K",
    )  # fmt: skip
    cfn = _function(draft, coil, "coil", FunctionKind.COIL)
    _pin(draft, cfn, "A1")
    _pin(draft, cfn, "A2")


def _supply_and_plc(draft: Draft, lib) -> None:
    """Facts: PSU + mark L+, - mark L-, Operating 24 V; PLC channel one pin, no facts."""
    psu = _part(
        draft, lib, manufacturer="TestCo", mpn="TEST-PSU-24V",
        category=PartCategory.GENERIC, letter="G",
    )  # fmt: skip
    out = _function(draft, psu, "out", FunctionKind.SUPPLY)
    _pin(draft, out, "+", None, PLUS)
    _pin(draft, out, "-", None, MINUS)
    key = (*out.key, "operating")
    draft.add(
        OperatingFacet(
            id=make_id(OperatingFacet, key),
            key=key,
            subject=out.id,
            operating=Operating(nominal_voltage_v=Decimal(24)),
        ),
        origin=_ORIGIN,
    )
    plc = _part(
        draft, lib, manufacturer="TestCo", mpn="TEST-PLC-CH",
        category=PartCategory.PLC_MODULE, letter="A",
    )  # fmt: skip
    _pin(draft, _function(draft, plc, "channel", FunctionKind.PLC_CHANNEL), "CH")


def _terminals_and_cables(draft: Draft, lib) -> None:
    """Facts: terminals internal/external CONDUCTIVE, no sides; PE terminal roles the same."""
    for mpn in ("TEST-TERM", "TEST-TERM-PE"):
        part = _part(
            draft, lib, manufacturer="TestCo", mpn=mpn,
            category=PartCategory.TERMINAL, letter="X",
        )  # fmt: skip
        fn = _function(draft, part, "terminal", FunctionKind.TERMINAL)
        inner = _pin(draft, fn, "internal", role=PortRole.INTERNAL)
        outer = _pin(draft, fn, "external", role=PortRole.EXTERNAL)
        _link(draft, fn, inner, outer, LinkKind.CONDUCTIVE)
    for mpn, colours in (
        ("TEST-CBL-4", ("BN", "BU", "BK", "GNYE")),
        ("TEST-CBL-3", ("BN", "BU", "BK")),
    ):
        cable = _part(
            draft, lib, manufacturer="TestCo", mpn=mpn,
            category=PartCategory.CABLE, letter="W",
        )  # fmt: skip
        key = (*cable.key, "cable_product")
        draft.add(
            CableProductFacet(
                id=make_id(CableProductFacet, key),
                key=key,
                subject=cable.id,
                core_colours=colours,
                gauge_mm2=Decimal("1.5"),
                shielded=False,
            ),
            origin=_ORIGIN,
        )


def series_library() -> Draft:
    """`build_test_catalogue()` plus every series stub part (mpns `TEST-MCB-3P` and the like)."""
    draft = build_test_catalogue()
    lib = _library(draft, "test-series")
    breaker(draft, lib)
    _contactor(draft, lib)
    _overload(draft, lib)
    _buttons(draft, lib)
    _loads(draft, lib)
    _supply_and_plc(draft, lib)
    _terminals_and_cables(draft, lib)
    return draft


def pair_library() -> Draft:
    """`series_library()` plus the demo parts: the pairs' PE terminal is `DEMO-TB-PE-2.5`."""
    return merge(series_library(), fransys_parts.load("demo_parts"))
