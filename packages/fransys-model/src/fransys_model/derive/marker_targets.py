"""A link marker with many targets prints the first and a count (owner 2026-10-05, model-0139).

A marker names the other ends of its net. Up to `FULL_TARGETS` it prints each, one line each.
Past that it prints one line, the first target and `+n` more distinct ones, so its box stays
one line wide; layout sizes the box with `marker_lines`, derive prints with `target_lines`.
"""

lazy from collections.abc import Sequence

FULL_TARGETS = 2


def marker_lines(targets: int) -> int:
    """The lines a marker with `targets` other ends prints: one each up to the limit, else one."""
    return targets if targets <= FULL_TARGETS else 1


def target_lines(number: int, positions: Sequence[str]) -> list[str]:
    """`#n-<position>` per distinct target, or the first (reading order) and `+<k>`."""
    distinct = list(dict.fromkeys(positions))
    if len(positions) <= FULL_TARGETS:
        return [f"#{number}-{position}" for position in distinct]
    more = f" +{len(distinct) - 1}" if len(distinct) > 1 else ""
    return [f"#{number}-{distinct[0]}{more}"]
