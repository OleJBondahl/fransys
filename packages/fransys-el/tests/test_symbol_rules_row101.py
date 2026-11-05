"""Row 101: the symbol choice order and the default step, read through the public symbol kit.

The part-level choice and the two-choices refusal are not reachable from the public author surface.
"""

import fransys as fr
import pytest
from fransys_el import ProblemError, symbol_kit
from fransys_el.symbol_kit import _rest
from fransys_el.symbol_rules import Facts, default_row, symbol_for

from electrical_symbols import LIBRARY
from fransys_model.elecdef import Gender
from fransys_model.kernel import Origin, evolve, make_id
from fransys_model.layout import SymbolChoice
from fransys_model.vocab import functions


def test_part_file_choice_beats_kind_choice() -> None:
    d = fr.design("demo_parts")
    sw = d.device("Q1", "DEMO-SWITCH-2P")
    kit = symbol_kit(fr.build(d).model, LIBRARY)
    assert kit[sw.sw.id].key == "make-contact"


def test_rest_and_push_draw_push_button_break() -> None:
    d = fr.design("demo_parts")
    pb = d.device("S1", "DEMO-PB-NO")
    pc = d.device("S2", "DEMO-PB-NC")
    kit = symbol_kit(fr.build(d).model, LIBRARY)
    assert kit[pc.sw.id].key == "push-button-break"
    assert kit[pb.sw.id].key == "push-button"


def test_s4_every_connector_gender_has_a_live_row() -> None:
    """S4: each connector gender, and none, has a live row; the rows give the three contacts."""
    genders = [None, *(g.name.lower() for g in Gender)]
    assert {"male", "female"} <= set(genders)
    symbols = set()
    for gender in genders:
        row = default_row(Facts("connector", None, None, gender, None))
        assert row is not None
        symbols.add(row.symbol)
    assert symbols == {"contact", "contact-male", "contact-female"}


def test_s2_two_choices_at_one_specificity_refuse() -> None:
    """S2: two choices for one function refuse, reached at `symbol_for`."""
    d = fr.design("demo_parts")
    k = d.device("K1", "DEMO-RLY-2CO-24")
    model = fr.build(d).model
    function = functions(model)[k.coil.id]
    key = ("test", "s2")
    twice = [
        SymbolChoice(
            id=make_id(SymbolChoice, (*key, s)),
            key=(*key, s),
            function=function.id,
            template=None,
            part=None,
            kind=None,
            symbol=s,
        )
        for s in ("operating-device", "contact")
    ]
    both = evolve(model, put=twice, origin=Origin(file="test_s2", line=1, note="two function choices"))
    with pytest.raises(ProblemError, match="several symbol choices"):
        symbol_for(both, function, None, Facts("coil", None, None, None, None))


def test_rest_follows_the_first_pole_that_has_a_switched_link() -> None:
    """The kit's rest fact is the state of the first function pole whose ends are a switched link (VOCAB-CLOSE)."""
    d = fr.design("demo_parts")
    d.device("K1", "DEMO-RLY-4CO-24")
    model = fr.build(d).model
    rests = [_rest(model, f) for f in functions(model).values()]
    assert sorted(map(str, rests)) == ["None", "rest", "rest", "rest", "rest"]
