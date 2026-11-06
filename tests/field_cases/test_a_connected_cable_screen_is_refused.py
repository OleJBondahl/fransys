"""Field case: a cable screen core wired to a pin is refused with SCREEN_DISABLED (R1799) and `fr.write` raises.
Screen connections return later (KI row SCREEN-RETURN); an open screen still prints as shielded."""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _expected_codes import expect_codes

if TYPE_CHECKING:
    from pathlib import Path


def _screened(*, connect: bool) -> fr.BuildResult:
    """A 2x2x0.75 instrument cable (cores 1-4 conductors, 5 and 6 pair screens) with every conductor wired."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8, pe="DEMO-TB-PE-2.5")
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 8)
    w1 = d.cable("W1", "DEMO-CBL-2X2X0.75-SP", length_m=5)
    for n in range(1, 5):
        w1.core(n, x1[n], x2[n])
    if connect:
        w1.core(5, x1.run("PE", 1)[1])
    return fr.build(d)


def test_a_connected_screen_is_refused_and_write_raises(tmp_path: Path) -> None:
    result = _screened(connect=True)
    expect_codes(result, "SCREEN_DISABLED")
    with pytest.raises(fr.BuildFailedError):
        fr.write(result, tmp_path / "out")


def test_an_open_screen_is_not_refused() -> None:
    assert "SCREEN_DISABLED" not in {f.code for f in _screened(connect=False).findings}
