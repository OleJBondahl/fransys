"""A `GROUP_SPLIT` avoids severing a D1 pole link (deep-dive D4, EF-A2 part 6), on the cabinet.

At a narrow content width `=P1` is wider than a page and splits between columns. Wire 17 joins
the through paths of `-K1` `aux` and `-S0` `nc_2`, two columns of `=P1`, on a net of two ports:
a D1 pole link. The split lands between two other columns, so no marker pair cuts it. The
pair `-K2` `aux` to `-K1` `aux` (wire 18) runs between two groups: packing between groups is
unchanged, and it stays a `CHAIN_BROKEN` where it is cut.
"""

import pytest
from narrow_cabinet import narrow_results

from fransys_layout.lint.codes import CHAIN_BROKEN
from fransys_layout.stages.partition import GROUP_SPLIT
from fransys_model.kernel import Finding, make_id
from fransys_model.vocab import AspectNode, Function

_K1_AUX = make_id(Function, ("cabinet", "k1", "fn", "aux"))
_K2_AUX = make_id(Function, ("cabinet", "k2", "fn", "aux"))
_S0_NC_2 = make_id(Function, ("cabinet", "s0", "fn", "nc_2"))
_P1 = make_id(AspectNode, ("p1",))


def _broken(findings: tuple[Finding, ...], pair: set) -> list[Finding]:
    """The `CHAIN_BROKEN` findings whose subjects name both functions of `pair`."""
    return [f for f in findings if f.code == CHAIN_BROKEN and pair <= set(f.subjects)]


@pytest.mark.parametrize("width_mm", [180, 170, 160, 150, 120, 100])
def test_the_pole_link_of_wire_17_is_not_cut_by_the_group_split(width_mm: int) -> None:
    """`=P1` still splits at these widths; the split does not cut `-K1` `aux` from `-S0` `nc_2`."""
    findings = narrow_results(width_mm)[1]
    assert any(f.code == GROUP_SPLIT and _P1 in f.subjects for f in findings)
    assert _broken(findings, {_K1_AUX, _S0_NC_2}) == []


@pytest.mark.parametrize("width_mm", [300, 210])
def test_a_link_between_two_groups_is_still_cut(width_mm: int) -> None:
    """Packing between groups is unchanged: `-K2` `aux` to `-K1` `aux` stays a `CHAIN_BROKEN`."""
    assert len(_broken(narrow_results(width_mm)[1], {_K2_AUX, _K1_AUX})) == 1
