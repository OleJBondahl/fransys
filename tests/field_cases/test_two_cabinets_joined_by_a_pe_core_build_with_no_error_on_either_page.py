"""Field case: two cabinets, each with an earthed PE terminal and one other earthed device, joined by a GNYE core.
The bug: the PE net spans both cabinets but took the bond class of whichever port was read last, so one cabinet's
page drew two earth pieces as one: DRAWING_SHORTS_NETS and RAIL_IDENTITY_SHARED, whichever order the ports came in (KI-1501)."""

from typing import NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import GNYE

_UNITS = {"A": "cab-a", "B": "cab-b"}


class _Side(NamedTuple):
    pe: fr.Terminal


def _cabinet(tag: str) -> fr.UnitDef[_Side]:
    @fr.unit(_UNITS[tag], revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title=tag, number=f"{tag}-1")
    def body(u: fr.Design) -> _Side:
        u.earth(u.device(f"M{tag}", "DEMO-MOTOR-4KW").motor["PE"])
        pe = u.terminal_strip(f"X{tag}", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True).run("PE", 1)[1]
        u.earth(pe)
        return _Side(pe)

    return body


def _build(first: str, *, swap_core: bool) -> fr.BuildResult:
    d = fr.design("demo_parts")
    sides = {tag: d.add(_cabinet(tag), f"{tag}1") for tag in (first, "B" if first == "A" else "A")}
    ends = (sides["B"].pe, sides["A"].pe) if swap_core else (sides["A"].pe, sides["B"].pe)
    d.cable("W1", "DEMO-CBL-4G1.5", length_m=3).core(GNYE, *ends)
    return fr.build(d, *(unit_document(name) for name in _UNITS.values()))


@pytest.mark.parametrize("swap_core", [False, True])
@pytest.mark.parametrize("first", ["A", "B"])
def test_two_cabinets_joined_by_a_pe_core_build_with_no_error_on_either_page(first: str, *, swap_core: bool) -> None:
    """The PE net of both cabinets is one bond class: no error in either order of the units or of the core's ends."""
    built = _build(first, swap_core=swap_core)
    assert [f.code for f in built.findings if f.severity.name == "ERROR"] == []
