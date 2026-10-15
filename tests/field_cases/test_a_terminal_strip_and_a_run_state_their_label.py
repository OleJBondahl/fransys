"""Field case: `TerminalStrip.label` and `Run.label` give the name a design printed.

The engineering shape: a jumper bar over terminals 1 to 4 of a strip, described in the bill of
materials with the strip's name, "X5 bar 1-3", built from the strip handle rather than a second
copy of the string.

The bug: the handle held its name privately, so the text was typed again and drifted from the
strip's tag.

Decision author-0055 (API-FRICTION-2 C14): `TerminalStrip.label` is the strip's label, as the design
printed it; `Run.label` is the run's own label. Both are read-only.
"""

import fransys as fr
import pytest


def test_a_strip_states_its_label() -> None:
    d = fr.design("demo_parts")
    x5 = d.terminal_strip("X5", "DEMO-TB-2.5", 4)
    assert x5.label == "X5"
    d.device(f"{x5.label} bar 1-3", "DEMO-JUMPER-BAR-3P")


def test_a_run_states_its_own_label() -> None:
    d = fr.design("demo_parts")
    x5 = d.terminal_strip("X5", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
    assert x5.run("L1", 2).label == "L1"
    assert x5.run("PE", 1).label == "PE"


def test_the_label_is_read_only() -> None:
    d = fr.design("demo_parts")
    x5 = d.terminal_strip("X5", "DEMO-TB-2.5", 4)
    with pytest.raises(AttributeError):
        x5.label = "X6"  # ty: ignore[invalid-assignment] -- the property has no setter
