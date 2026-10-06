"""Field case: a fixed assembly `Unit` of N short two-ended harnesses (a cable with a plug at
each end), each harness at its own location, every plug port a boundary port of the unit, and
no other internal wiring at all: the unit is nothing but a bundle of pass-through cables.

The bug: 19 harnesses in the unit gives `CONNECTION_NOT_DRAWN` ERRORs (a cable core between the
unit's own two boundary plugs is never routed); 18 harnesses routes clean, and the same 19
harnesses built with no `Unit` around them route clean too (both measured 2026-09-26). So this
is a scale threshold inside a `Unit`'s own layout, not a shape the engine never handles. The
unit carries its own `fr.document(...)` (units spec U3, the pattern
`tests/test_write_unit_worked_example.py` uses) so the case still lays out once `fr.build` only
lays out a model that holds a `Document` (decision PS1).

Found by a consumer, reproduced 2026-09-26. The cause (2026-09-27): the unit's overview pages its
plugs in tag order, which stands two harnesses' plugs on two pages there, while each core is wired
between the plugs' boundary replicas on its location's sheet; so no cut was decided and neither
overview page drew the core. Fixing decision: the layout redesign's S21 (`references` decides
every connection; ends on different pages of one drawing set are a `#n` reference, D4).
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr

if TYPE_CHECKING:
    from pathlib import Path


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


_PLUG = "DEMO-CONN-2P"
_CABLE = "DEMO-CBL-4G1.5"
_BAD_CODES = {"ROUTE_FAILED", "CONNECTION_NOT_DRAWN"}


def _harness_assembly(n: int, tmp_path: Path) -> fr.BuildResult:
    """A unit of `n` two-ended harnesses, each its own location, both plugs of each a boundary
    port of the unit; no other wiring; the unit's own cabinet-schematic document.
    """

    @fr.unit(
        "unit",
        revision=1,
        interface_version=1,
        date="2026-09-26",
        text="First issue",
        by="XX",
    )
    def assembly(u: fr.Design) -> _Open:
        with u.function("HAR", "Harness"):
            for i in range(n):
                u.location(f"L{i}", f"Harness {i}")
                harness = u.harness(f"WH{i}", name=f"w{i}", place=f"L{i}")
                near = u.device(f"P{i}A", _PLUG, parent=harness, place=f"L{i}", interface=True)
                far = u.device(f"P{i}B", _PLUG, parent=harness, place=f"L{i}", interface=True)
                cable = u.cable(f"W{i}", _CABLE, parent=harness, name=f"w{i}c", place=f"L{i}")
                cable.core(1, near[1], far[1])
        return _Open()

    d = fr.design("demo_parts")
    d.add(assembly, "UNIT")
    cover = tmp_path / "unit.md"
    cover.write_text("# Harness assembly\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "unit", cover=cover)
    return fr.build(d, doc)


def _bad_codes(result: fr.BuildResult) -> set[str]:
    return {f.code for f in fr.check(result) if f.code in _BAD_CODES}


def test_nineteen_harnesses_route_clean(tmp_path: Path) -> None:
    """Takes several seconds: 19 is the smallest reproducing count, and it is one build."""
    assert _bad_codes(_harness_assembly(19, tmp_path)) == set()
