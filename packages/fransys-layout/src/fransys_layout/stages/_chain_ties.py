"""Chain direction ties (T4): the facts of one direction of a chain, and the order that picks."""

from typing import TYPE_CHECKING, NamedTuple

from fransys_layout.conventions import FACTS, fact, rank_key, validate
from fransys_layout.conventions.order import CHAIN_TIES

from ._chain_state import _Synthetic

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ._chain_state import _Pole, _PoleId, _Reading
    from .types import FunctionSpec, Handle


class _Direction(NamedTuple):
    """One direction of a chain: its walked sequence, what the pass reads, and whether turned."""

    seq: Sequence[tuple[_PoleId, Handle, Handle]]
    rd: _Reading
    turned: bool

    def ends(self) -> tuple[Handle, Handle]:
        """The end ports in this direction: where it starts and where it stops."""
        first, last = self.seq[0][1], self.seq[-1][2]
        return (last, first) if self.turned else (first, last)


def _strip_of(pole: _Pole, specs: Mapping[Handle, FunctionSpec]) -> str:
    """The strip text of a terminal pole, empty for any other."""
    if not pole.terminal or pole.kind is _Synthetic.MATE:
        return ""
    return specs[pole.function].strip_text


@fact("strip_entry_outvoted", kind="physical", source="IEC 60947-7 terminal block strip entry")
def _strip_entry_outvoted(way: _Direction) -> bool:
    """The strip entries outvote this direction; a tie keeps the walked one (B9)."""
    rd = way.rd
    votes = [
        rd.port_side.get(e) == rd.strip_entry[_strip_of(rd.poles[p], rd.specs)]
        for p, e, _ in way.seq
        if _strip_of(rd.poles[p], rd.specs) in rd.strip_entry
    ]
    entered, against = votes.count(True), votes.count(False)
    return bool(votes) and (entered >= against if way.turned else against > entered)


@fact("potential_below_top", kind="electrical", source="across quantity: Rail.max_v and phase")
def _potential_below_top(way: _Direction) -> bool:
    """This direction starts at the lower potential, when the two ends differ (C20, A10)."""
    first, last = (way.rd.rank_of.get(end) for end in way.ends())
    return first is not None and last is not None and last < first


@fact("designation_after", kind="physical", source="IEC 81346 reference designation")
def _designation_after(way: _Direction) -> bool:
    """This direction starts at the later designation, then the terminal sort key (A6, D1)."""
    rd = way.rd
    first, last = (rd.port_function[end] for end in way.ends())
    return (rd.specs[first].designation, rd.tie_key.get(first, ())) > (
        rd.specs[last].designation,
        rd.tie_key.get(last, ()),
    )


validate(CHAIN_TIES, FACTS)


def needs_reverse(seq: Sequence[tuple[_PoleId, Handle, Handle]], rd: _Reading) -> bool:
    """Whether a direction-free chain runs bottom to top: the first tie rule that separates."""
    return rank_key(CHAIN_TIES, _Direction(seq, rd, turned=True), FACTS) < rank_key(
        CHAIN_TIES, _Direction(seq, rd, turned=False), FACTS
    )
