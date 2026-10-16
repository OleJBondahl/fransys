"""Field case: a 3-wire sensor function with no line or load side, at the end of a series.

Engineering shape: a three-wire sensor on a plug is wired through a terminal strip and a 3-core
cable to a block of the panel. Its part file states three plain pins and no side, so nothing says
which pin is the line and which the load. The series is written with the bare sensor function as
its last element.

The bug: the refusal says "has no pole pair" and then tells the part's author to add the port key
`side` in the part file. The sensor's author is not the engineer who wrote the series, and the
explicit spelling `<device>.<fn>.pins` (pin for pin, in order) is the call that would work. Pin
order is a guess that can miswire a three-wire sensor, so the bare function must keep refusing.
The explicit `.pins` spelling builds.

Fixing decision: author-0061 (item 4: the refusal names the `.pins` spelling, not the part file).
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from fransys.colours import BK

if TYPE_CHECKING:
    from pathlib import Path

_PART = (
    'schema = 1\n\n[part]\nmpn = "PLANT-SENS-3W"\nmanufacturer = "Plant"\n'
    'description = "Planted three-wire sensor, no side"\ncategory = "generic"\nclass_code = "B"\n\n'
    '[[function]]\nname = "sig"\nkind = "sensor"\n'
    "ports = [\n"
    '    { name = "1", role = "generic" },\n'
    '    { name = "2", role = "generic" },\n'
    '    { name = "3", role = "generic" },\n'
    "]\n"
)


def _series_parts(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[fr.Design, tuple]:
    """A design on demo parts plus one planted sensor with pins 1 to 3 and no side.

    Returns the design and the (terminal strip ends 1 to 3, cable, sensor device) handles.
    """
    package = root / "fieldcase_bare_fn_parts"
    (package / "parts").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "library.toml").write_text(
        'schema = 1\nname = "fieldcase_bare_fn_parts"\nversion = "0.1.0"\n'
        'description = "Planted"\n',
        encoding="utf-8",
    )
    (package / "parts" / "sensor3w.toml").write_text(_PART, encoding="utf-8")
    monkeypatch.syspath_prepend(str(root))
    d = fr.design("fieldcase_bare_fn_parts", "demo_parts", place="CAB")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    cable = d.cable("W1", "DEMO-CBL-3X0.34")
    sensor = d.device("B1", "PLANT-SENS-3W")
    return d, (strip[1:4], cable, sensor)


def test_a_bare_sensor_end_is_refused_and_names_the_pins_spelling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    d, (ends, cable, sensor) = _series_parts(tmp_path, monkeypatch)
    with pytest.raises(fr.AuthorError) as raised:
        d.series(ends, cable, sensor.sig, wire=(BK, 0.75))
    message = str(raised.value)
    assert "has no line/load pole pair" in message
    assert "sig.pins" in message
    assert "adds the port key" not in message
    assert "`side`" not in message


def test_the_explicit_pins_spelling_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d, (ends, cable, sensor) = _series_parts(tmp_path, monkeypatch)
    d.series(ends, cable, sensor.sig.pins, wire=(BK, 0.75))
    fr.build(d)
