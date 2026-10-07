"""Field case: two three-phase supplies in one design, the second with its own rail names.

The engineering shape: a 400 V earthed L1/L2/L3/N supply and a second, floating three-phase
supply (no N, 230 V line to line) whose rails are named EL1, EL2 and EL3. A contactor on each
supply feeds its own output strip, as the two throws of a changeover would.

The bug: `ac_supply` had no `names=`, so the second supply's rails were also called L1, L2 and
L3, and the duplicate-rail refusal rejected it: it could not be declared.

Fixed by decision author-0024: `names=` takes one name per phase pin, then one for N. It renames
the printed rail and its potential; phases and conductor marks stay L1/L2/L3/N, so wire colours
and phase checks are unchanged.
"""

import fransys as fr
import pytest
from _model_build_cover import cabinet_document
from fransys.colours import BK
from fransys_author import AuthorError

from fransys_model.vocab.tables import nets, supply_systems

_STAR_VOLTS = "132.79"  # 230 V line to line is 230 / sqrt(3) from each phase to the star point


def _design(names: tuple[str, ...]) -> fr.Design:
    d = fr.design("demo_parts")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 4)
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
    out_a, out_b = (d.terminal_strip(tag, "DEMO-TB-2.5", 3) for tag in ("X8", "X9"))
    mains = d.ac_supply("400V", 230, x0[1], x0[2], x0[3], n=x0[4])
    it = d.ac_supply(
        "IT230V", _STAR_VOLTS, *(x1[n] for n in (1, 2, 3)), names=names, earthing=fr.IT
    )
    q2 = d.device("Q2", "DEMO-CTR-3P-24")
    for pole, rail in enumerate((mains.L1, mains.L2, mains.L3)):
        d.series(rail, d.device(f"F{pole + 1}", "DEMO-MCB-C6").element, out_a, wire=(BK, 2.5))
    d.series(it, q2.main, out_b, wire=(BK, 2.5))
    return d


def test_second_supply_prints_its_own_rail_names() -> None:
    """The model carries EL1, EL2 and EL3 as the second supply's rails and power nets, no ERROR."""
    d = _design(("EL1", "EL2", "EL3"))
    result = fr.build(d, cabinet_document(d.location("C1", "Cabinet")))
    assert not [f for f in result.findings if f.severity is fr.Severity.ERROR]
    rails = {s.name: set(s.rails) for s in supply_systems(result.model).values()}
    assert rails["IT230V"] == {"EL1", "EL2", "EL3"}
    assert rails["400V"] == {"L1", "L2", "L3", "N"}
    assert {"EL1", "EL2", "EL3"} <= {n.potential for n in nets(result.model).values()}


def test_names_of_the_wrong_length_raise_with_the_expected_count() -> None:
    """Two names for three phases and no N raise, and the message gives the expected count."""
    with pytest.raises(AuthorError, match="expected 3"):
        _design(("EL1", "EL2"))
