"""D5 step 6: the power symbols and their texts of the invented plant, against a golden.

One line per symbol (page, symbol, turn, origin, text) and one per power label (page, box), over
`power_fixture`'s plant on its narrow sheet. `--regenerate-golden` rewrites it; read the diff.
"""

from pathlib import Path

import pytest
from power_fixture import power_run

from fransys_layout.stages.texts.power import power_places
from fransys_model.layout import POWER_SLOT

_GOLDEN = Path(__file__).parent.parent / "golden" / "power_symbols.txt"


@pytest.fixture
def regenerate(request: pytest.FixtureRequest) -> bool:
    """True under `--regenerate-golden`: the golden is rewritten instead of compared."""
    return bool(request.config.getoption("--regenerate-golden"))


def _dump() -> str:
    layout = power_run()[2].layout
    lines = [
        f"S p{one.page} {one.symbol} {one.orientation.name} {one.at.x},{one.at.y} {one.text!r}"
        for one in sorted(power_places(layout.markers), key=lambda p: (p.page, p.at.x, p.at.y))
    ]
    labels = sorted(
        (one for one in layout.labels if one.slot == POWER_SLOT),
        key=lambda one: (one.page, one.box.x, one.box.y),
    )
    lines += [
        f"L p{one.page} {one.box.x},{one.box.y} {one.box.width}x{one.box.height}" for one in labels
    ]
    return "\n".join(lines) + "\n"


def test_power_symbols_match_golden(*, regenerate: bool) -> None:
    """The plant's power symbols and texts are the ones in `golden/power_symbols.txt`."""
    actual = _dump()
    if regenerate:
        _GOLDEN.write_text(actual, encoding="utf-8", newline="\n")
    assert actual == _GOLDEN.read_text(encoding="utf-8")
    assert actual.count("\nL ") + actual.startswith("L ") > 0
