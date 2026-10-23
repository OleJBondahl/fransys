"""The head of a fan and rule P3, each in one place (layout-0286).

Spec section 2: a fan's head is its driver and its legs are its sinks. The builder
(`topology_nets`) gives a fan with exactly one driver that driver as `Fan.head`; a fan with
several (a return bus) has none, and P3 does not apply to it: its spread is priced by its arrow
pairs. Stage 4's HEAD_OFF_LEGS and the scorer's P3 both read `fan_head` and `head_short`.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Set as AbstractSet

    from .values import Attach, Fan


def fan_head(fan: Fan) -> Attach | None:
    """The fan's head: the one driver its builder chose, or None (no driver, or several)."""
    return fan.head


def head_short(
    head_pages: AbstractSet[int], leg_pages: Iterable[int]
) -> tuple[int, int, int] | None:
    """P3: (legs on the head's page, the page holding most of the others, its legs), or None.

    None when no other page holds more legs than the head's page. A tie keeps the lower page.
    """
    legs = Counter(leg_pages)
    mine = max((legs[p] for p in head_pages), default=0)
    others = [p for p in legs if p not in head_pages]
    if not others:
        return None
    most = max(others, key=lambda p: (legs[p], -p))
    return (mine, most, legs[most]) if mine < legs[most] else None
