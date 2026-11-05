"""Field case: `TerminalStrip.label` and `Run.label` give the name a design printed.
The bug: the handle held its name privately, so a bill of materials typed the strip's text again and it drifted from the tag.
Fixed by author-0055, both labels are read-only: the strip's label as printed, and the run's own (API-FRICTION-2 C14)."""

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
