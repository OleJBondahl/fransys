"""Field case: two adjacent poles of a 4-pole changeover relay, inside a `Unit`, each pole's
make throw and break throw wired to its own terminal on a field strip (a different location
than the relay's own).

The bug: with the relay inside a `Unit`, the higher-numbered of the two poles' make-throw wire
cannot be routed (`ROUTE_FAILED`, `CONNECTION_NOT_DRAWN`); the lower-numbered pole's make throw,
and both poles' break throws, route clean. The same wiring with no `Unit` around it routes
clean. Reordering the wiring calls does not move the failure to the other pole: it is the
relay's third and fourth poles specifically, whichever one is authored first.

Found by a consumer, reproduced 2026-09-26. Fixing decision: layout-0088 -- a route end's first
outward cell is reserved for its own net; no other net runs, turns or crosses there. The layout
redesign's step 5 (D1, "terminal under its throw") is expected to remove the detour these two
poles need at all, drawing the higher-numbered pole's make throw on a straight second row
instead, which would make this reservation moot for this case (still the general router rule).
"""

from typing import NamedTuple

import fransys as fr
from fransys.colours import BK


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


_TERMINAL = "DEMO-TB-2.5"
_CHANGEOVER = "DEMO-CO-4P-24"
_BAD_CODES = {"ROUTE_FAILED", "CONNECTION_NOT_DRAWN", "DOCUMENT_NO_DRAWINGS"}


def _circuit(d: fr.Design) -> _Open:
    """Poles 3 and 4 of one changeover: each pole's make throw and break throw wired to its
    own terminal of a field strip (one strip for make throws, a second for break throws); no
    other wiring.
    """
    d.location("CAB", "Cabinet")
    d.location("FIELD", "Field strips")
    field_a = d.terminal_strip("X01", _TERMINAL, place="FIELD")
    field_b = d.terminal_strip("X02", _TERMINAL, place="FIELD")
    relay = d.device("K1", _CHANGEOVER, place="CAB")
    for pole in (3, 4):
        make = field_a.run(f"RUN{pole}", 1)[1]
        brk = field_b.run(f"RUN{pole}", 1)[1]
        fn = getattr(relay, f"co_{pole}")
        d.wire(brk, fn[f"{pole}2"], wire=(BK, 1.5))  # break throw
        d.wire(make, fn[f"{pole}4"], wire=(BK, 1.5))  # make throw
    return _Open()


_circuit_unit = fr.unit(
    "unit", revision=1, interface_version=1, date="2026-09-26", text="First issue", by="XX"
)(_circuit)


def _build(tmp_path, *, in_unit: bool) -> fr.BuildResult:
    """The circuit inside a unit or bare, in one `CABINET_SCHEMATIC` document.

    A `CABINET_SCHEMATIC` document is a third draft (MODEL-BUILD PS4, decision 0037): with no
    document, decision 0037's own gate (PS1) skips layout entirely, and this field case's
    `ROUTE_FAILED`/`CONNECTION_NOT_DRAWN` codes -- both layout findings -- would never fire
    either way, passing vacuously with no proof layout-0088's fix still holds. A unit is one
    drawing set: a unit's drawings take the unit as subject, not a location inside it (a
    location inside a unit has no drawing of its own -- `DOCUMENT_NO_DRAWINGS` otherwise, the
    pattern `tests/field_cases/test_boundary_only_harness_assembly.py` uses); the no-unit path
    has no unit to be the subject, so it keeps `cab`.
    """
    d = fr.design("demo_parts")
    if in_unit:
        d.add(_circuit_unit, "UNIT")
    else:
        _circuit(d)
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    subject = "unit" if in_unit else d.location("CAB", "Cabinet")
    document_draft = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover)
    return fr.build(d, document_draft)


def _bad_codes(result: fr.BuildResult) -> set[str]:
    return {f.code for f in fr.check(result) if f.code in _BAD_CODES}


def test_changeover_make_throws_route_inside_a_unit(tmp_path) -> None:
    assert _bad_codes(_build(tmp_path, in_unit=True)) == set()


def test_changeover_make_throws_route_with_no_unit(tmp_path) -> None:
    """The passing neighbour: the same wiring with no `Unit` around it routes clean."""
    assert _bad_codes(_build(tmp_path, in_unit=False)) == set()
