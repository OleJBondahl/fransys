"""Field case: terminals of one strip stand in rows: three at the symbols' pitch, others alone or a gap apart in one row.
The bug: the far terminals printed only their point (`4`) under a strip tag, so an engineer could not tell which strip they belong to.
Fixed by el-0125 (STRIP-TAG-ONCE, designer R2063, R2068): a terminal alone in its run, or a gap from its neighbour, prints the full form (`-XA:4`)."""

from typing import NamedTuple

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import RD


class _Io(NamedTuple):
    pass


@fr.unit("fc-terminal-tag", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _alone(d: fr.Design) -> _Io:
    xa = d.terminal_strip("XA", "DEMO-TB-2.5", 5)
    supply = d.ac_supply("A", "230", xa[1], xa[2], xa[3])
    qa, m1 = d.device("QA", "DEMO-MCB-3P"), d.device("M1", "DEMO-MOTOR-4KW")
    d.series(supply, qa.element, m1, wire=2.5)
    d.series(xa[4], d.device("H1", "DEMO-LAMP-24"), xa[5], wire=(RD, 0.5))
    return _Io()


@fr.unit("fc-terminal-gap", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _gapped(d: fr.Design) -> _Io:
    xa = d.terminal_strip("XA", "DEMO-TB-2.5", 8)
    for k in (1, 2, 3, 4):
        d.series(xa[k], d.device(f"H{k}", "DEMO-LAMP-24"), xa[k + 4], wire=(RD, 0.5))
    return _Io()


def _tags(unit: fr.UnitDef[_Io], name: str) -> set[str]:
    d = fr.design("demo_parts")
    d.add(unit, "U1")
    result = fr.build(d, cabinet_document(name))
    return {t.text for drawing in drawn_pages(result.model).values() for t in drawing.texts if t.kind == "TAG"}


@pytest.mark.rule("STRIP-TAG-ONCE")
def test_a_terminal_alone_in_its_column_prints_its_full_designation() -> None:
    tags = _tags(_alone, "fc-terminal-tag")
    assert {"1", "2", "3", "-XA"} <= tags  # the run at the symbols' own pitch keeps one strip tag over its points
    assert {"-XA:4", "-XA:5"} <= tags
    assert not {"4", "5"} & tags


@pytest.mark.rule("STRIP-TAG-ONCE")
def test_terminals_a_gap_apart_in_one_row_print_their_full_designations() -> None:
    tags = _tags(_gapped, "fc-terminal-gap")
    assert {"-XA:1", "-XA:2", "-XA:3", "-XA:4"} <= tags
    assert not {"1", "2", "3", "4"} & tags
