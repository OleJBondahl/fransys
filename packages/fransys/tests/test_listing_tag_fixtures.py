"""A baseline cut by a real older release is refused as BASELINE_TOO_OLD under today's build: listing versions 1 and 2 are not read (model-0381).

`data/listing_tags/v0.18.3/` holds the release folder `fr.release` wrote with the code of tag
v0.18.3. Cut with `claude-tools/ls_tag_fixture_v0.18.3.py`, run
"""

from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import GNYE

_DATA = Path(__file__).parent / "data" / "listing_tags"


class _Open(NamedTuple):
    pass


@fr.unit("ls-bar", revision=1, interface_version=1, date="2026-10-14", text="r", by="AB")
def _bar(u: Any) -> _Open:
    pe = u.terminal_strip("X1", "DEMO-TB-PE-2.5")
    motors = {n: u.device(n, "DEMO-MOTOR-4KW") for n in ("M1", "M2", "M3")}
    for i, name in enumerate(("M1", "M2"), 1):
        u.series(motors[name].motor["PE"], pe[i], wire=(GNYE, 2.5))
    return _Open()


@pytest.fixture(scope="module")
def result() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_bar, "U1")
    return fr.build(d)


@pytest.mark.parametrize("tag", ["v0.18.3"])
def test_a_real_older_release_is_refused_as_too_old(result: fr.BuildResult, tag: str) -> None:
    findings = fr.verify(result, _DATA / tag)
    assert [(f.code, f.severity.name) for f in findings] == [("BASELINE_TOO_OLD", "ERROR")]
    assert "0.18.3" in findings[0].message
