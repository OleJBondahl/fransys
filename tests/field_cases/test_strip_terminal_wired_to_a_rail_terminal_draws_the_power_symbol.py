"""Field case: a plain strip terminal whose only wire goes to a bridged 24 V rail terminal.

The engineering shape: a PSU on a declared 24 V DC supply feeds a bridged `24V` run of strip X1;
one terminal of a plain strip X2 is wired to that run, the PSU's 0 V to X2's other terminal.

The bug: X2's terminal drew as a bare dot, with no wire and no power symbol (finding
`CONNECTION_TO_UNDRAWN`), because the rail-wire reader counted only non-terminal pins as ends.

The rule (owner 2026-10-02): a pin on a rail strip draws the power symbol. The decision that fixed
it: layout-0137.
"""

from typing import TYPE_CHECKING

import fransys as fr

from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    from pathlib import Path


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    psu = d.device("T1", "DEMO-PSU-24")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("24V", psu)
    rail = d.terminal_strip("X1", "DEMO-TB-2.5").run("24V", 2, bridged=True)
    plain = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
    d.wire(psu.output["+"], rail[1], wire=("RD", 0.75))
    d.wire(rail[2], plain[1], wire=("RD", 0.75))
    d.wire(psu.output["-"], plain[2], wire=("BK", 0.75))
    (tmp_path / "c.md").write_text("# C\n", encoding="utf-8")
    return fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=tmp_path / "c.md")
    )


def test_a_terminal_wired_only_to_a_rail_terminal_draws_a_power_symbol(tmp_path: Path) -> None:
    model = _build(tmp_path).model
    (item,) = (i for i in items(model) if fr.derive.printed_designation(model, i) == "-X2:1")
    funcs = {f.id for f in functions(model).values() if f.item == item}
    mine = {p.id for p in ports(model).values() if p.function in funcs}
    drawn = [s for s in layout_of(model, PowerSymbol).values() if s.port in mine]
    assert [s.symbol for s in drawn] == ["power-supply"]
    assert "CONNECTION_TO_UNDRAWN" not in {f.code for f in fr.check(_build(tmp_path))}


def test_a_device_pe_pin_wired_to_a_pe_bar_terminal_draws_protective_earth(tmp_path: Path) -> None:
    """The earth shape of the same cause (layout-0137): a PE pin wired to a bridged PE bar draws the
    PE symbol. A pin joined only by `d.earth` draws bare by design and warns `NET_UNREALISED`."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    bar = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5").run("PE", 2, bridged=True)
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    d.wire(motor.motor["PE"], bar[1], wire=("GNYE", 2.5))
    d.earth(motor.motor["PE"], bar[1])
    (tmp_path / "c.md").write_text("# C\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=tmp_path / "c.md")
    model = fr.build(d, doc).model
    assert [s.symbol for s in layout_of(model, PowerSymbol).values()] == ["protective-earth"]
