"""A chain of states, each the step of the one before, cut at a repeat (cleanup step 2, F6)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def _same[S](state: S) -> S:
    return state


def follow[S](
    start: S, step: Callable[[S], S | None], *, key: Callable[[S], object] = _same
) -> list[S]:
    """`start`, then `step` of each, until `None` or a repeated `key` (the repeat is left out)."""
    seen = {key(start)}
    states = [start]
    while (state := step(states[-1])) is not None and key(state) not in seen:
        seen.add(key(state))
        states.append(state)
    return states
