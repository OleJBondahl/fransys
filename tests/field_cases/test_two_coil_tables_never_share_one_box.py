"""Field case: two coils stacked in one column get their contact tables at one and the same box.

The engineering shape: two relays wired in series (K1's A2 to K2's A1, K2's A2 to the 0 V rail),
each with a changeover contact feeding its own lamp. The two coils stand one under the other in
one column, and each coil gets a contact table (NO | NC).

The bug: `contact_images` places each table at the column's foot when a cell stands below its
coil, and a coil below its anchor is the column's last cell too; both coils share the anchor x and
the foot y, so the two tables print over each other and K1's table is not under K1 at all. Nothing
separates one image from another.
The fix (decision layout-0170): tables sharing one foot stack in coil order, top coil first,
each headed by its coil's tag.
"""

import tempfile
from pathlib import Path

import fransys as fr
from _contact_tables import table_body_g, table_symbols
from fransys.colours import BU


def _built():
    """The model of the two-relay circuit."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G1", "Relay group"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 4).run("R", 4, bridged=True)
        d.dc_supply("S", plus=live[1], minus=rail[1], voltage=24)
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        k2 = d.device("K2", "DEMO-RLY-2CO-24")
        p1 = d.device("P1", "DEMO-LAMP-24")
        p2 = d.device("P2", "DEMO-LAMP-24")
        d.detail.wire(live[1], k1.coil["A1"], wire=(BU, 0.5))
        d.detail.wire(k1.coil["A2"], k2.coil["A1"], wire=(BU, 0.5))
        d.detail.wire(k2.coil["A2"], rail[2].outer, wire=(BU, 0.5))
        d.detail.wire(k1.co_1["14"], p1.lamp["1"], wire=(BU, 0.5))
        d.detail.wire(p1.lamp["2"], rail[3].outer, wire=(BU, 0.5))
        d.detail.wire(k2.co_1["14"], p2.lamp["1"], wire=(BU, 0.5))
        d.detail.wire(p2.lamp["2"], rail[4].outer, wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _overlap(a: tuple, b: tuple) -> bool:
    """True when the two boxes (x0, y0, x1, y1) share area."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_two_coil_tables_stack_in_coil_order_each_headed_by_its_coil() -> None:
    """Both coils have a table; no two overlap; K1's is above K2's; each prints its coil."""
    tables = table_symbols(_built())
    assert len(tables) == 2
    top, bottom = sorted(tables, key=lambda t: t.y)
    assert not _overlap(table_body_g(top), table_body_g(bottom))
    # the heading row of a table is its coil's tag
    assert [t.texts[0] for t in (top, bottom)] == [("-K1",), ("-K2",)]
