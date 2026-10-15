"""Field case: one source feeds several targets, each by its own wire.

The engineering shape: one terminal (a feed) goes to five terminals of another strip, one wire
from the feed to each. `d.detail.wire(src, *targets)` chains instead (src to t1, t1 to t2, and so
on), so the targets end up wired to each other.

The need: a star, `d.detail.star(src, targets)`, one wire from the source to each target and none
between targets. A strip as the source gives ONE terminal for all targets.

The decision: author-0059; the API rewrite keeps the star as a verb of its own.
"""

import fransys as fr
from fransys.colours import BK

from fransys_model.vocab import Conductor, ConductorKind
from fransys_model.vocab.tables import conductors

_TERMINAL = "DEMO-TB-2.5"
_TARGETS = (1, 4, 7, 10, 13)


def _wires(model: fr.Model) -> list[frozenset]:
    """The two port ids of each wire."""
    found: list[Conductor] = [c for c in conductors(model).values() if c.kind is ConductorKind.WIRE]
    return [frozenset((c.a, c.b)) for c in found]


def test_a_star_wires_the_source_to_each_target() -> None:
    """A chain would end five wires too, but with the targets wired to each other."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    x2 = d.terminal_strip("X2", _TERMINAL)
    x7 = d.terminal_strip("X7", _TERMINAL)
    targets = tuple(x7[n] for n in _TARGETS)
    d.detail.star(x2[17].outer, targets, wire=(BK, 1.5))
    wires = _wires(fr.build(d).model)
    source = x2[17].outer.id
    assert sorted(wires, key=sorted) == sorted(
        (frozenset((source, t.inner.id)) for t in targets), key=sorted
    )


def test_a_strip_as_the_source_gives_one_terminal_for_all_targets() -> None:
    """A strip resolved per target would take a new free terminal each time."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    feed = d.terminal_strip("X2", _TERMINAL)
    x7 = d.terminal_strip("X7", _TERMINAL)
    targets = tuple(x7[n] for n in _TARGETS)
    d.detail.star(feed, targets, wire=(BK, 1.5))
    wires = _wires(fr.build(d).model)
    ends = [{p for p in w if p not in {t.inner.id for t in targets}} for w in wires]
    assert len(wires) == len(_TARGETS)
    assert len({next(iter(e)) for e in ends}) == 1
