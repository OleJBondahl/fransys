"""HL14, author-0030: a side hint on an interface with no harness line warns and draws nothing.

Built through `import fransys as fr` from `examples/demo-parts` only. The interface is a boundary
connector left open on purpose, so no harness line stands at it.
"""

from typing import NamedTuple

import fransys as fr

_CODE = "SIDE_HINT_NO_HARNESS_LINE"


class _Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-side", revision=1, interface_version=1, date="2026-10-07", text="t", by="XX")
def _board(d: fr.Design) -> _Io:
    return _Io(d.device("X1", "DEMO-CONN-2P", interface=True))


def _build(*, hint: bool):
    d = fr.design("demo_parts", place="C1")
    io = d.add(_board, "U1", unused=("X1",))
    if hint:
        d.layout.side(io.X1, fr.ABOVE)
    return fr.build(d)


def test_a_hint_on_an_interface_with_no_harness_line_gives_the_warning() -> None:
    result = _build(hint=True)
    (finding,) = [f for f in result.findings if f.code == _CODE]
    assert finding.severity is fr.Severity.WARNING
    assert "X1" in finding.message


def test_no_hint_no_warning() -> None:
    assert not [f for f in _build(hint=False).findings if f.code == _CODE]
