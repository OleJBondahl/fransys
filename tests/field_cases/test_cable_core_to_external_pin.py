"""Field case: one pin shown in two function groups (a header pin joined to a coil pin), each view wired to a PE strip pin.
The bug: 0.23.2 (CP-S1) joined PE symbols by cabinet rail only, so each view was a piece: CONNECTION_NOT_DRAWN, drawing unchanged.
Fixed in join_power: inked power symbols of one model group (conductor, link, header join) are one piece."""

import contextvars
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import GNYE

from fransys_model.kernel import id_namespace


class _Io(NamedTuple):
    pe: Any


@fr.unit("pin-views", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Pin views", number="PV-1")
def _pin_views(u: Any) -> _Io:
    m = u.device("M1", "DEMO-RELAY-MOD-2")
    pe = u.terminal_strip("PE", "DEMO-TB-PE-2.5", 4)
    u.series(m.j1[1], pe[1], wire=(GNYE, 1.5))
    u.series(m.k1["A1"], pe[2], wire=(GNYE, 1.5))
    u.earth(pe[1])
    return _Io(pe)


@pytest.mark.parametrize("salt", ["-", "a", "b"])
def test_two_views_of_one_pin_each_grounded_by_a_pe_symbol_are_one_piece(salt: str) -> None:
    """The header pin and its coil pin are one pin: no CONNECTION_NOT_DRAWN, and the build holds no ERROR."""

    def built() -> list[str]:
        if salt != "-":
            id_namespace(salt)  # a context of its own: the salt never leaks into another test
        d = fr.design("demo_parts")
        d.add(_pin_views, "U1", place=None)
        return [f.message for f in fr.check(fr.build(d, unit_document("pin-views"))) if f.severity.name == "ERROR"]

    assert contextvars.copy_context().run(built) == []
