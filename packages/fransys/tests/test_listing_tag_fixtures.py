"""A baseline cut by a real older release verifies as one INFO under today's build (LS3).

`data/listing_tags/v0.18.3/` holds the release folder `fr.release` wrote with the code of tag
v0.18.3 (the bar prints its screw there). Cut with `claude-tools/ls_tag_fixture_v0.18.3.py`, run
from a worktree at the tag: `uv run python ls_tag_fixture_v0.18.3.py <into>`; the design is
the one below, spelled with that tag's `u.wire`. Demo parts only.
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
    pe1 = u.device("PE1", "DEMO-PEBAR-20").pe
    motors = {n: u.device(n, "DEMO-MOTOR-4KW") for n in ("M1", "M2", "M3")}
    for name in ("M1", "M2"):
        u.detail.wire(motors[name].motor["PE"], pe1, wire=(GNYE, 2.5))
    return _Open()


@pytest.fixture(scope="module")
def result() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_bar, "U1")
    return fr.build(d)


@pytest.mark.parametrize("tag", ["v0.18.3"])
def test_a_real_older_release_gives_one_info_and_no_error(result: fr.BuildResult, tag: str) -> None:
    findings = fr.verify(result, _DATA / tag)
    assert [(f.code, f.severity.name) for f in findings] == [("BASELINE_RULES_MOVED", "INFO")]
    assert "0.18.4" in findings[0].message
