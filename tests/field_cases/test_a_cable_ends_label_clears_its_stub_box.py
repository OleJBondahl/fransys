"""Field case: a multi-core cable leaves a row of relays for one arrow box, with a label per branch.
The bug: a branch label could stand under the arrow box's text (seen at a 2.6 mm smallest text height, no longer a setting).
Fixed by layout-0206, a line label keeps clear of the boxes of the stubs its own line ends in, as of every other box."""

from functools import cache
from typing import NamedTuple

import fransys as fr
from _expected_codes import expect_codes
from _model_build_cover import cabinet_document, unit_document
from fransys.colours import BK, BU


@cache
def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cab = d.location("C1", "Cabinet")
    fld = d.location("FLD", "Field")
    cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    for n in range(1, 5):
        relay = d.device(f"K{n}", "DEMO-RLY-2CO-24")
        lamp = d.device(f"M{n}", "DEMO-LAMP-24", place="FLD")
        cable.core(n, relay.coil["A1"], lamp["1"])
        d.series(relay.coil["A2"], lamp["2"], wire=(BU, 0.5))
    return fr.build(d, unit_document(cab), unit_document(fld))


def test_no_text_overlaps_the_cables_label_or_its_arrow_box() -> None:
    bad = [(f.code, f.message) for f in _built().findings if f.code == "WIRE_OVER_LABEL" and "-W1" in f.message]
    assert bad == []


class _MotorIo(NamedTuple):
    M1: fr.Device


class _StripIo(NamedTuple):
    L1: fr.Run
    L2: fr.Run
    L3: fr.Run


@fr.unit("demo-motor-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _motor_box(d: fr.Design) -> _MotorIo:
    with d.function("FAN", "Fan"):
        return _MotorIo(d.device("M1", "DEMO-MOTOR-4KW", interface=True))


@fr.unit("demo-feed-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _feed_box(d: fr.Design) -> _StripIo:
    strip = d.terminal_strip("X4", "DEMO-TB-2.5", description="Motor supply out")
    runs = [strip.run(n, 1, interface=True) for n in ("L1", "L2", "L3")]
    with d.function("FEED", "Motor feed"):
        d.series(d.device("F7", "DEMO-OVERLOAD-3P").main, (runs[0][1], runs[1][1], runs[2][1]), wire=(BK, 2.5))
    return _StripIo(*runs)


def test_a_motor_cabled_from_a_three_pole_overloads_strips_draws_its_bundle_stub() -> None:
    d = fr.design("demo_parts")
    d.project(title="Demo plant", number="P-1", customer="Demo Co", revision=1, author="OJB")
    d.revision(1, date="2026-01-01", text="first", created="AB")
    d.location("DECK", "Upper deck")
    d.location("ROOM", "Pump room")
    motor = d.add(_motor_box, "BP", place="DECK")
    feed = d.add(_feed_box, "CS", place="ROOM")
    cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=60, external=True)
    with d.function("CFN", "Fan feed"):
        d.series((feed.L1[1], feed.L2[1], feed.L3[1]), cable, motor.M1.motor)
    built = fr.build(d, cabinet_document(d.location("DECK", "Upper deck")))
    expect_codes(built, "UNPRINTED_SET")  # the document prints only the motor unit's location
    assert [f.message for f in built.findings if f.code == "PLACEMENT_PROBLEM"] == []
    assert "DRAWN_READ_INCOMPLETE" not in {f.code for f in built.findings}
