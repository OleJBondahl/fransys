"""Field case: a control relay K1 with four changeover contacts, three used, each feeding a coil and a starter relay in a function block.
The bug: the consumer's drawing reported DRAWING_SHORTS_NETS; on this branch the shape gives LANE_WIRE_DROPPED.
Open: unmarked repro, both assertions stay in this module (the write must build, and no net may be reported shorted)."""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from fransys.colours import BK, WH

if TYPE_CHECKING:
    from pathlib import Path

_CTRL = (WH, 0.5)
_ZERO = (BK, 0.5)


class _Io(NamedTuple):
    pass


def _contacts(count: int) -> fr.UnitDef[_Io]:
    @fr.unit("fc-sh", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def build(d: fr.Design) -> _Io:
        strip = d.terminal_strip("X1", None, 12, external=True)
        bridge = d.terminal_strip("X2", "DEMO-TB-2.5", 9, external=True, bridged=((1, 3), (4, 6), (7, 9)))
        with d.function("CTRL", "Control"):
            relay = d.device("K1", "DEMO-RLY-4CO-24")
            holds = [d.device(f"Q{i}", "DEMO-RLY-2CO-24") for i in range(1, count + 1)]
            buttons = [d.device(f"S{i}", "DEMO-PB-NO") for i in range(1, count + 1)]
            loads = [d.device(f"Y{i}", "DEMO-RLY-2CO-24") for i in range(1, count + 1)]
            d.series(strip[1].outer, relay.coil, strip[2].outer, wire=_CTRL)
            for i, hold in enumerate(holds):
                d.series(bridge[1 + i].outer, hold.coil, wire=_CTRL)
            for i in range(count):
                contact = getattr(relay, f"co_{i + 1}")
                d.series(holds[i].coil, contact.nc, buttons[i].sw, wire=_CTRL)
        for i in range(count):
            with d.function(f"P{i + 1}", f"Starter {i + 1}"):
                contact = getattr(relay, f"co_{i + 1}")
                d.series(buttons[i].sw, bridge[4 + i].outer, wire=_ZERO)
                d.series(contact.no, loads[i].coil, wire=_CTRL)
                d.series(loads[i].coil, bridge[7 + i].outer, wire=_ZERO)
        return _Io()

    return build


def _error_codes(count: int, root: Path) -> list[str]:
    d = fr.design("demo_parts")
    d.add(_contacts(count), "U1")
    (root / "cover.md").write_text("# cover\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "fc-sh", cover=root / "cover.md")
    try:
        fr.write(fr.build(d, document), root / "out", intermediates=root / "inter")
    except fr.BuildFailedError as raised:
        return [f.code for f in raised.findings]
    return []


def test_three_used_contacts_of_a_four_changeover_relay_draw_no_shorted_nets(
    tmp_path: Path,
) -> None:
    codes = _error_codes(3, tmp_path)
    assert "DRAWING_SHORTS_NETS" not in codes
    assert codes == []
