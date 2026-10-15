"""`score(scene)`: the terms of the placement objective that a scene states (design section 3).

One counter per term. The same function scores today's output, a mock-up and the engine.
This is the one home of the crossing rule: once per point and per pair of nets. Cable lines and
fan legs of the harness family are outside its scope (design fact 18).
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .score_facts import attached_off_pin, head_off_legs, row_broken
from .score_placement import junction_off_line, loose, pair_cut
from .score_wiring import wiring

if TYPE_CHECKING:
    from .scene import Scene


@dataclass(frozen=True, slots=True)
class Score:
    """The counted terms. `placement` maps a P rule name to the boxes or nets it flags."""

    pages: int
    symbols: int
    references: dict[str, int]
    wiring: dict[str, int]
    placement: dict[str, list[str]] = field(default_factory=dict)


def score(scene: Scene) -> Score:
    """Count every term of `scene`; the crossing counter counts points."""
    refs: dict[str, int] = {}
    for marker in scene.markers:
        refs[marker.cls] = refs.get(marker.cls, 0) + 1
    placement = {
        "attached_off_pin": attached_off_pin(scene),
        "pair_cut": pair_cut(scene),
        "head_off_legs": head_off_legs(scene),
        "loose": loose(scene),
        "junction_off_line": junction_off_line(scene),
        "row_broken": row_broken(scene),
    }
    return Score(
        pages=len({b.page for b in scene.boxes}),
        symbols=len({b.id for b in scene.boxes}),
        references=refs,
        wiring=wiring(scene.wires),
        placement=placement,
    )
