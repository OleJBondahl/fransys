"""Field case: the overview and the release listing print a bar end as the bar alone.

The engineering shape: a cabinet unit with a protective-earth bar and three motors, each PE pin
wired to the bar.

The bug: the wire list printed `-U1-PE1` (PE-BAR B4), but the overview's signal tracing and the
release listing's conductor ends still named the screw (`-PE1:1`), a fact the wiring never records.
The rule: one derive fact, `printed_port_name`, says what follows an item's designation; a bar's
port gives nothing (model-0227). A release baseline cut with a bar on 0.18.3 shows
`BASELINE_DIFFERS` once.
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import GNYE

from fransys_model.derive import overview_graph
from fransys_model.derive.baseline import listing
from fransys_model.vocab.bars import is_bar_port
from fransys_model.vocab.tables import units


class _Unit(NamedTuple):
    """A unit with no interface to hand back."""


@fr.unit("pe-text", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _cab(c: Any) -> _Unit:
    pe1 = c.device("PE1", "DEMO-PEBAR-20").pe
    for name in ("M1", "M2", "M3"):
        c.detail.wire(c.device(name, "DEMO-MOTOR-4KW").motor["PE"], pe1, wire=(GNYE, 2.5))
    return _Unit()


@pytest.fixture(scope="module")
def model(tmp_path_factory: pytest.TempPathFactory) -> Any:
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    cover = tmp_path_factory.mktemp("cover") / "c.md"
    cover.write_text("# C\n", encoding="utf-8")
    return fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "pe-text", cover=cover)
    ).model


def test_overview_signals_mark_a_bar_end_with_no_screw(model: Any) -> None:
    """The overview's signal ports on the bar carry no marking; the motor pins keep theirs."""
    ports = [p for s in overview_graph(model).signals for p in s.ports]
    assert [p.marking for p in ports if is_bar_port(model, p.port)]
    assert {p.marking for p in ports if is_bar_port(model, p.port)} == {""}
    assert {p.marking for p in ports if not is_bar_port(model, p.port)} == {"PE"}


def test_release_listing_conductor_ends_print_the_bar_alone(model: Any) -> None:
    """The listing's conductor ends on the bar read `-PE1`, no `:1`."""
    (unit,) = units(model)
    ends = [end for row in listing(model, unit).conductors for end in (row.a, row.b)]
    assert [e for e in ends if "PE1" in e] == ["-PE1"] * 3
