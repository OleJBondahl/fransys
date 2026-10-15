"""What a strip's call marks: boundary terminals by index and bridges with no run (author-0038)."""

from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.surface._runs import is_range

if TYPE_CHECKING:
    from fransys_author.surface._strip import TerminalStrip

_PAIR = 2  # a bridge joins at least two terminals
Marks = bool | tuple[int, ...]
Bridged = bool | tuple[int, int] | tuple[tuple[int, int], ...]


def marked(spec: Marks, number: int) -> bool:
    """Whether terminal `number` is named by `spec`: `True` names every one."""
    return spec is True or (isinstance(spec, tuple) and number in spec)


def check_marks(tag: str, count: int | None, **specs: Marks) -> None:
    """Raise `AuthorError` for a tuple on a strip with no count or a number outside `1..count`."""
    for keyword, spec in specs.items():
        if isinstance(spec, bool):
            continue
        if count is None:
            msg = f"{tag}: {keyword}={spec} names terminals by number, so give the strip a count"
            raise AuthorError(msg)
        for number in spec:
            if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= count:
                msg = (
                    f"{tag}: {keyword}={spec} names terminal {number!r}, outside 1..{count}: "
                    f"name numbers from 1 to {count}"
                )
                raise AuthorError(msg)


def check_run_marks(
    tag: str, strip_spec: tuple[Marks, Marks], *, interface: Marks, unused: Marks
) -> None:
    """Raise when a run marks (`interface=True`, `unused=True`) a strip that already marks all."""
    if (interface or unused) and any(spec is True for spec in strip_spec):
        msg = (
            f"{tag}: the strip already marks every terminal as boundary, so the run's "
            "interface=/unused= repeats it: set it on the strip or on the run, not both"
        )
        raise AuthorError(msg)


def _ranges(tag: str, count: int | None, bridged: Bridged) -> tuple[tuple[int, int], ...]:
    """The `(first, last)` ranges `bridged` names, each checked; `()` for `False`."""
    if bridged is False:
        return ()
    if count is None:
        msg = f"{tag}: bridged= names terminals by number, so give the strip a count"
        raise AuthorError(msg)
    if bridged is True:
        if count < _PAIR:
            msg = (
                f"{tag}: bridged=True needs a strip of at least 2 terminals, got a count of {count}"
            )
            raise AuthorError(msg)
        return ((1, count),)
    pairs = (bridged,) if isinstance(bridged[0], int) else bridged
    return tuple(_one_range(tag, count, pair) for pair in pairs)


def _one_range(tag: str, count: int, pair: tuple[int, int]) -> tuple[int, int]:
    first, last = pair
    if not is_range(first, last, count):
        msg = f"{tag}: bridged={pair} needs 1 <= first < last <= {count}"
        raise AuthorError(msg)
    return first, last


def bridge_ranges(strip: TerminalStrip, bridged: Bridged) -> None:
    """Jumper each range of terminals of `strip`, each to the next; a refusal names the fix."""
    ranges = _ranges(strip._tag, strip._count, bridged)
    ordered = sorted(ranges)
    for (_, last), (first, _) in pairwise(ordered):
        if first <= last:
            tag = strip._tag
            msg = f"{tag}: bridged ranges overlap at terminal {first}: give each terminal one range"
            raise AuthorError(msg)
    if strip._bridge is None:
        return
    for first, last in ranges:
        numbers = range(first, last + 1)
        strip._bridge(*(strip._terminal(number) for number in numbers))
        if strip._now() is not None:  # outside every block each terminal joins its first block
            strip._claim(*numbers)
