"""Stage 5, y: a mate's subject names its halves in natural order, whichever half came first."""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core import Facts, PinRef
from fransys_layout.core.place_align import mate_aligns

from . import align_fixtures as fx
from .test_place_x import env_of


def test_a_mate_subject_does_not_depend_on_the_order_of_its_halves() -> None:
    """Mate(p.s, q.n) and Mate(q.n, p.s) give one subject, the natural-order one."""
    prob = fx.mate_columns()
    swapped = replace(prob, facts=Facts(mates=((PinRef("q", "n"), PinRef("p", "s")),)))
    (kept,) = mate_aligns(env_of(prob))
    (flipped,) = mate_aligns(env_of(swapped))
    assert flipped.subject == kept.subject
    assert kept.subject == "p.s/q.n"
