"""Field case: two adjacent poles of a 4-pole changeover relay inside a `Unit`, each wired to a field strip.
The bug: a make throw had no path, though the same wiring outside a Unit routed clean.
Fixed by layout-0088, a route end's first outward cell is reserved for its own net; no other net runs, turns or crosses there."""

from typing import NamedTuple

import fransys as fr
from _model_build_cover import cabinet_document, unit_document
from fransys.colours import BK


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


_TERMINAL = "DEMO-TB-2.5"
_CHANGEOVER = "DEMO-RLY-4CO-24"
_BAD_CODES = {"CONNECTION_NOT_DRAWN", "DOCUMENT_NO_DRAWINGS"}


def bad_codes(result: fr.BuildResult, bad: set[str]) -> set[str]:
    """The codes of `bad` that `fr.check` finds on `result`."""
    return {f.code for f in fr.check(result) if f.code in bad}


def _circuit(d: fr.Design) -> _Open:
    """Poles 3 and 4 of one changeover: each pole's make throw and break throw wired to its
    own terminal of a field strip (one strip for make throws, a second for break throws); no
    other wiring than the coil's feed from a cabinet strip.
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
        d.series(brk.inner, fn[f"{pole}2"], wire=(BK, 1.5))  # break throw
        d.series(make.inner, fn[f"{pole}4"], wire=(BK, 1.5))  # make throw
    # layout-0218: an unwired coil is drawn nowhere; its feed from a cabinet strip keeps K1's
    # coil, and so its contact table and the contacts' cross-references, on the page
    feed = d.terminal_strip("X03", _TERMINAL, place="CAB")
    d.series(feed[1].inner, relay.coil["A1"], wire=(BK, 0.75))
    d.series(feed[2].inner, relay.coil["A2"], wire=(BK, 0.75))
    return _Open()


_circuit_unit = fr.unit("unit", revision=1, interface_version=1, date="2026-09-26", text="First issue", by="XX")(_circuit)


def _build(*, in_unit: bool) -> fr.BuildResult:
    """The circuit inside a unit or bare, in one `CABINET_SCHEMATIC` document.

    A `CABINET_SCHEMATIC` document is a third draft (decision 0037): with no
    document, decision 0037's own gate skips layout entirely, and this field case's
    """
    d = fr.design("demo_parts")
    if in_unit:
        d.add(_circuit_unit, "UNIT")
    else:
        _circuit(d)
    subject = "unit" if in_unit else d.location("CAB", "Cabinet")
    document_draft = unit_document(subject)
    return fr.build(d, document_draft, *(() if in_unit else (cabinet_document(d.location("FIELD", "Field strips")),)))


def test_changeover_make_throws_route_inside_a_unit() -> None:
    assert bad_codes(_build(in_unit=True), _BAD_CODES) == set()


def test_changeover_make_throws_route_with_no_unit() -> None:
    """The passing neighbour: the same wiring with no `Unit` around it routes clean."""
    assert bad_codes(_build(in_unit=False), _BAD_CODES) == set()
