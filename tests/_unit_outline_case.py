"""The unit-with-outline case of P7.4: a unit's interface strip wired inside and out (SW8).

Invented demo data only (invariant 6): `examples/demo-parts`.
"""

import atexit
import shutil
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BU

__all__ = ["TERMINALS", "unit_outline_case_drafts"]

TERMINALS = 4


class _Io(NamedTuple):
    X: Any


@fr.unit("demo-switch-cab", revision=1, interface_version=1, date="2026-01-01", text="1", by="AB")
def _cab(u: Any) -> _Io:
    x = u.terminal_strip("X", "DEMO-TB-2.5", TERMINALS, interface=True)
    for n in range(1, TERMINALS + 1):
        button = u.device(f"S{n}", "DEMO-PB-NO")
        u.detail.wire(x[n], button.sw["A"], wire=(BU, 0.5))
    return _Io(x)


def unit_outline_case_drafts() -> tuple[fr.Design, Any]:
    """The design and cabinet document: unit U1 (strip X, four push buttons) and a field strip X9.

    Each terminal of X is wired to its push button inside the unit and, on its outer side, to the
    same-numbered terminal of the container's field strip X9, so every net crosses the unit.
    """
    d = fr.design("demo_parts")
    room = d.location("R", "Room")
    cab = d.add(_cab, "U1", place="R")
    field = d.terminal_strip("X9", "DEMO-TB-2.5", TERMINALS, external=True, place="R")
    for n in range(1, TERMINALS + 1):
        d.detail.wire(cab.X[n], field[n], wire=(BU, 0.5))
    scratch = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, scratch, ignore_errors=True)
    cover = Path(scratch) / "cover.md"
    cover.write_text("# Room\n", encoding="utf-8")
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, room, cover=cover)
