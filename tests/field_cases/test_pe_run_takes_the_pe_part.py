"""Field case: a run labelled "PE" takes the strip's PE part.

The engineering shape: a strip with feed-through terminals and a PE run beside them, the
protective conductors landing on PE terminal blocks (IEC 60947-7-2, label "PE" per IEC 60445).

The bug: a run took the strip's one feed-through part, so the PE terminals counted and printed
as feed-through ones; there was no part-per-run keyword (owner: "all terminals except PE are of
the same part").

The rule (EA15, G23): a run labelled exactly "PE" takes the strip's `pe=` part; on a strip
without `pe=` it raises `_take_pe`'s message. An explicit `X1[n]` is unchecked.
"""

import fransys as fr
import pytest
from fransys_author import AuthorError

_FEED = "DEMO-TB-2.5"
_PE = "DEMO-TB-PE-2.5"


def _strip(pe: str | None = None) -> fr.Design:
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", _FEED, pe=pe)
    strip.run("PE", 2)
    strip.run("L", 3)
    return d


def test_pe_run_takes_the_pe_part() -> None:
    """Two PE terminals of the `pe=` part, three feed-through ones in the other run."""
    d = _strip(_PE)
    counts = {line.mpn: line.count for line in fr.derive.bom_lines(fr.build(d).model)}
    assert counts == {_PE: 2, _FEED: 3}


def test_pe_run_without_pe_part_raises() -> None:
    """No `pe=`: the same message `_take_pe` gives, naming the strip and the fix."""
    with pytest.raises(
        AuthorError, match=r"X1 has no PE terminal part: terminal_strip\(\.\.\., pe="
    ):
        _strip()
