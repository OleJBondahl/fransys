"""Field case: a plain strip terminal whose only wire goes to a bridged 24 V rail terminal draws the power symbol.
The bug: the terminal drew as a bare dot (CONNECTION_TO_UNDRAWN), as the rail-wire reader counted only non-terminal pins as ends.
Fixed by layout-0137: a pin on a rail strip draws the power symbol (owner 2026-10-02)."""

from typing import TYPE_CHECKING

import fransys as fr
from _drawn_facts import symbol_subjects

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
    rail = d.terminal_strip("X1", "DEMO-TB-2.5").run("24V", 2, bridged=True, rail=True)
    plain = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
    d.series(psu.output["+"], rail[1].inner, wire=("RD", 0.75))
    d.series(rail[2].inner, plain[1].inner, wire=("RD", 0.75))
    d.series(psu.output["-"], plain[2].inner, wire=("BK", 0.75))
    (tmp_path / "c.md").write_text("# C\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=tmp_path / "c.md"))


def test_an_unflagged_terminal_wired_to_a_rail_terminal_draws_as_a_terminal(tmp_path: Path) -> None:
    """G08-POWER: the unflagged -X2:1 draws as a terminal, a rail symbol at each of its pins; the rail terminal draws nothing."""
    result = _build(tmp_path)
    model = result.model
    (item,) = (i for i in items(model) if fr.derive.printed_designation(model, i) == "-X2:1")
    funcs = {f.id for f in functions(model).values() if f.item == item}
    mine = {p.id for p in ports(model).values() if p.function in funcs}
    drawn = [s for s in layout_of(model, PowerSymbol).values() if s.port in mine]
    assert [s.symbol for s in drawn] == ["power-supply", "power-supply"]
    assert [p.symbol for p in symbol_subjects(model) if p.function in funcs] == ["terminal"]
    rail = {i for i in items(model) if fr.derive.printed_designation(model, i).startswith("-X1:")}
    rail_funcs = {f.id for f in functions(model).values() if f.item in rail}
    assert rail_funcs
    assert not [p for p in symbol_subjects(model) if p.function in rail_funcs]
    assert "CONNECTION_TO_UNDRAWN" not in {f.code for f in fr.check(result)}


def test_a_device_pe_pin_wired_to_a_pe_rail_terminal_draws_protective_earth(tmp_path: Path) -> None:
    """The earth shape of the same cause (layout-0137): a PE pin wired to a bridged PE rail terminal draws the
    PE symbol. A pin joined only by `d.earth` draws it too (model-0236)."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    bar = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5").run("PE", 2, bridged=True, rail=True)
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    d.series(motor.motor["PE"], bar[1].inner, wire=("GNYE", 2.5))
    d.earth(motor.motor["PE"], bar[1])
    (tmp_path / "c.md").write_text("# C\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=tmp_path / "c.md")
    model = fr.build(d, doc).model
    assert [s.symbol for s in layout_of(model, PowerSymbol).values()] == ["protective-earth"]


def _motor_earth(tmp_path: Path, *, wired: bool) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    bar = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5").run("PE", 2, bridged=True, rail=True)
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    if wired:
        d.series(motor.motor["PE"], bar[1].inner, wire=("GNYE", 2.5))
    d.earth(motor.motor["PE"], bar[1])
    (tmp_path / "c.md").write_text("# C\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=tmp_path / "c.md"))


def _motor_pe_symbols(result: fr.BuildResult) -> list[str]:
    model = result.model
    (item,) = (i for i in items(model) if fr.derive.printed_designation(model, i) == "-M1")
    funcs = {f.id for f in functions(model).values() if f.item == item}
    pe = {p.id for p in ports(model).values() if p.function in funcs and p.key[-1] == "PE"}
    return [s.symbol for s in layout_of(model, PowerSymbol).values() if s.port in pe]


def test_a_pe_pin_joined_only_by_earth_draws_protective_earth(tmp_path: Path) -> None:
    """B0 (model-0236): every pin joined by `d.earth` draws the PE symbol, wired or not."""
    result = _motor_earth(tmp_path, wired=False)
    assert _motor_pe_symbols(result) == ["protective-earth"]
    assert "NET_UNREALISED" not in {f.code for f in fr.check(result)}


def test_a_wire_to_a_pe_terminal_changes_nothing_on_the_pin_symbol(tmp_path: Path) -> None:
    bare = _motor_pe_symbols(_motor_earth(tmp_path, wired=False))
    wired = _motor_pe_symbols(_motor_earth(tmp_path, wired=True))
    assert bare == wired == ["protective-earth"]
