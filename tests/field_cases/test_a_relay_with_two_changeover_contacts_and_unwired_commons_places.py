"""Field case: a control relay K1 with two changeover contacts, each break throw through a coil and each make throw to another coil.
The bug: with two contacts the drawing set cannot be laid out (PLACEMENT_PROBLEM, YCycleError), so no page is made and fr.write raises.
Closed by R868: the core hub turn places both contacts."""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from fransys.colours import WH

if TYPE_CHECKING:
    from pathlib import Path

_WIRE = (WH, 0.5)


class _Io(NamedTuple):
    pass


def _contacts(count: int, *, reverse: bool = False) -> fr.UnitDef[_Io]:
    @fr.unit("fc-co", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def build(d: fr.Design) -> _Io:
        strip = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 8, external=True)
        with d.function("CTRL", "Control"):
            order = range(count, 0, -1) if reverse else range(1, count + 1)
            loads = {i: d.device(f"Y{i}", "DEMO-RLY-2CO-24") for i in order}
            buttons = {i: d.device(f"S{i}", "DEMO-PB-NO") for i in order}
            holds = {i: d.device(f"Q{i}", "DEMO-RLY-2CO-24") for i in order}
            relay = d.device("K1", "DEMO-RLY-2CO-24")
            d.series(strip[1].outer, relay.coil, strip[2].outer, wire=_WIRE)
            for i in range(count):
                contact = getattr(relay, f"co_{i + 1}")
                d.series(holds[i + 1].coil, contact.nc, buttons[i + 1].sw, wire=_WIRE)
                d.series(strip[5].outer, holds[i + 1].coil, wire=_WIRE)
                d.series(buttons[i + 1].sw, strip[3].outer, wire=_WIRE)
                d.series(contact.no, loads[i + 1].coil, wire=_WIRE)
                d.series(loads[i + 1].coil, strip[4].outer, wire=_WIRE)
        return _Io()

    return build


def _codes(count: int, root: Path, *, reverse: bool = False) -> set[str]:
    d = fr.design("demo_parts")
    d.add(_contacts(count, reverse=reverse), "U1")
    (root / "cover.md").write_text("# cover\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "fc-co", cover=root / "cover.md")
    return {f.code for f in fr.build(d, document).findings}


def test_one_contact_with_its_common_unwired_is_placed(tmp_path: Path) -> None:
    """Control: one contact reaches no PLACEMENT_PROBLEM (it has a conductor with no path today)."""
    assert "PLACEMENT_PROBLEM" not in _codes(1, tmp_path)


def test_two_contacts_with_their_commons_unwired_are_placed(tmp_path: Path) -> None:
    assert "PLACEMENT_PROBLEM" not in _codes(2, tmp_path)


def test_two_contacts_declared_in_reverse_are_placed(tmp_path: Path) -> None:
    """The same circuit, its symbols declared in reverse: a variant for the rank landing."""
    assert "PLACEMENT_PROBLEM" not in _codes(2, tmp_path, reverse=True)


def test_two_contacts_with_their_commons_unwired_draw_no_wire_along_a_net_they_do_not_join(tmp_path: Path) -> None:
    """KI-405: WIRE_MEETS_NET shows along Y1 today."""
    assert "WIRE_MEETS_NET" not in _codes(2, tmp_path)
