"""`RAIL_DEFAULTS` holds the rails `ac_supply` and `dc_supply` once typed in the author (EL-7 F)."""

from fransys_model.vocab import RAIL_DEFAULTS, ConductorMark


def test_rail_defaults_hold_the_values_the_author_once_typed() -> None:
    assert RAIL_DEFAULTS["ac"] == (
        (ConductorMark.L1, 0),
        (ConductorMark.L2, 120),
        (ConductorMark.L3, 240),
    )
    assert RAIL_DEFAULTS["ac_neutral"] is ConductorMark.N
    assert RAIL_DEFAULTS["dc"] == (ConductorMark.L_PLUS, ConductorMark.L_MINUS, ConductorMark.M)
    assert RAIL_DEFAULTS["dc_zero"] == "0V"
    assert set(RAIL_DEFAULTS) == {"ac", "ac_neutral", "dc", "dc_zero"}
