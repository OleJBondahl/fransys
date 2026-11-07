"""Field case: a supply function stands at the top level and again inside a nested unit, cabled between their strips.
The bug (v0.22): the system sheet carrying both groups prints the function twice, "Incoming supply, Incoming supply".
Fixed: KI-350, `page_titles._entries` names each text once."""

import re
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK

if TYPE_CHECKING:
    from pathlib import Path

_SHEET = re.compile(r'"[0-9]+: ([^"\\]*)')


class _Io(NamedTuple):
    U: fr.Run


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Cabinet")
def _cabinet(u: Any) -> _Io:
    with u.function("SUP", "Incoming supply"):
        run = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True).run("L1", 2)
        lamp = u.device("H1", "DEMO-LAMP-24")
        u.series(run[1].inner, lamp["1"], wire=(BK, 0.5))
        u.series(run[2].inner, lamp["2"], wire=(BK, 0.5))
    return _Io(U=run)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Path]:
    tmp_path = tmp_path_factory.mktemp("titles")
    d = fr.design("demo_parts", "intake_parts", place="EXT")
    d.location("EXT", "External")
    d.project(title="Titles", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-26", text="First issue", created="XX")
    cabinet = d.add(_cabinet, "C1", place=None)
    with d.function("SUP", "Incoming supply"):
        up = d.terminal_strip("X0", "DEMO-TB-2.5", external=True).run("L1", 2)
        cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
        cable.core(1, up[1], cabinet.U[1])
        cable.core(2, up[2], cabinet.U[2])
    cover = tmp_path / "cover.md"
    cover.write_text("# Titles\n", encoding="utf-8")
    result = fr.build(
        d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover), fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover)
    )
    fr.write(result, out_dir=tmp_path / "out", intermediates=tmp_path / "inter")
    return result, tmp_path / "inter"


def test_a_sheet_title_names_each_function_once(built: tuple[Any, Path]) -> None:
    titles = [t.split(", ") for typ in built[1].glob("*.typ") for t in _SHEET.findall(typ.read_text(encoding="utf-8"))]
    assert ["Incoming supply"] in titles
    assert all(len(set(entries)) == len(entries) for entries in titles)


def test_the_cable_between_two_same_named_strips_is_drawn(built: tuple[Any, Path]) -> None:
    """KI-358: placement_sets._scoped joins the two homes of a strip pair with cut=(), so neither set draws a stub."""
    undrawn = [f for f in built[0].findings if f.code == "CONNECTION_NOT_DRAWN"]
    assert not undrawn, [f.message for f in undrawn]
