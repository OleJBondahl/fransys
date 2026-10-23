"""`ac_supply` and `dc_supply` take their default rails from `RAIL_DEFAULTS` (EL-7 part F)."""

from typing import TYPE_CHECKING

from fransys_author.surface import design

from fransys_model.vocab import RAIL_DEFAULTS

from .test_supplies import lib  # noqa: F401 -- the module fixture of the supply tests

if TYPE_CHECKING:
    from fransys_model.kernel import Draft


def test_ac_supply_rails_follow_the_table(lib: Draft) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    pins = [d.device(f"A{i}", "TEST-PSU-24V").out["+"] for i in range(4)]
    ac = d.ac_supply("mains", "400", *pins[:3], n=pins[3])
    rails = (ac.L1, ac.L2, ac.L3)
    assert [(r.mark, r.phase) for r in rails] == list(RAIL_DEFAULTS["ac"])
    assert [r.potential for r in rails] == [mark.value for mark, _ in RAIL_DEFAULTS["ac"]]
    assert (ac.N.mark, ac.N.potential) == (RAIL_DEFAULTS["ac_neutral"], "N")


def test_dc_supply_rails_follow_the_table(lib: Draft) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    dc = d.dc_supply("psu", d.device("G1", "PSU-MID"))
    assert (dc.plus.mark, dc.minus.mark, dc.mid.mark) == tuple(RAIL_DEFAULTS["dc"])
    assert dc.mid.potential == RAIL_DEFAULTS["dc_zero"]
    e = design(lib, place="C1")
    two = e.dc_supply("two", e.device("G2", "TEST-PSU-24V"))
    assert two.minus.potential == RAIL_DEFAULTS["dc_zero"]
