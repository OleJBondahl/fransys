"""CONTACT-STATES CS4 fallback (Acceptance 8): the voltage to earth stands only with no pair.

An IT 400 V supply with N: L1, L2, L3 at 230 V max and 0/120/240 degrees, N at 0 V. An IT phase
stands 398.4 V to earth. A function with a rail pair in some state checks at its pairs, even
when a contact leaves one side open in another state: that open side floats at the other side's
potential and 0 V stands across the device. A function that never stands across two rails (a pole
in one conductor) checks at the voltage to earth of the rail it reaches. Every plant is
hand-built and invented.

Can-fail probe, one Edit in `vocab/validators/ratings.py`, run and undone: `_stands` judging the
fallback per state, returning `[*pair_stands, *earth_stands]` even when pairs exist, fails the
load test with a false 398.4 V finding and leaves the single-pole tests passing.
"""

from plant import Plant
from rating_plant import AC_400, rated, supply
from test_rail_pairs import _GENERIC, _NO, _load, _Relay

from fransys_model.kernel import make_id
from fransys_model.vocab import PartRatingFacet, rail_pairs
from fransys_model.vocab.enums import Earthing, FunctionKind
from fransys_model.vocab.templates import Part
from fransys_model.vocab.validators.ratings import check_ratings

_PROTECTION = (
    "prot",
    FunctionKind.PROTECTION,
    (("1", _GENERIC), ("2", _GENERIC)),
    (("1", "2"),),
)


def _it_plant() -> Plant:
    """A plant with the IT 400 V supply `400V`."""
    plant = Plant()
    supply(plant, "ac", AC_400, name="400V", earthing=Earthing.IT)
    return plant


def test_a_load_between_a_no_contact_l1_and_n_is_checked_at_its_pair_not_to_earth() -> None:
    """(a) L1 behind a relay's NO contact, N declared on the other port, rated 230 V AC."""
    plant = _it_plant()
    relay = _Relay(plant, "k1", (_NO,))
    load = _load(plant, ac="230")
    plant.net("L1", (relay.pins["no.13"],), potential="L1")
    plant.wire(relay.pins["no.14"], load.p0, key="w-p0")
    plant.net("N", (load.p1,), potential="N")
    model = plant.model()
    assert rail_pairs(model, load.function) == frozenset({("L1", "N")})
    assert check_ratings(model) == ()


def _pole(rating: str) -> Plant:
    """A protection function `prot` of item `f1` rated `rating` V AC, L1 on pin 1 only.

    Its switched link is conductive, so L1 reaches both ports: one rail, no pair.
    """
    plant = _it_plant()
    guard = _Relay(plant, "f1", (_PROTECTION,))
    plant.add(
        PartRatingFacet(
            id=make_id(PartRatingFacet, ("f1",)),
            key=("f1",),
            subject=make_id(Part, ("part-f1",)),
            rating=rated(ac=rating),
        )
    )
    plant.net("L1", (guard.pins["prot.1"],), potential="L1")
    assert rail_pairs(plant.model(), guard.functions["prot"]) == frozenset()
    return plant


def test_a_single_pole_in_one_conductor_rated_below_its_rail_to_earth_gives_the_finding() -> None:
    """(b) IT phase L1 stands 398.4 V to earth: 300 V fires, and says so."""
    (finding,) = check_ratings(_pole("300").model())
    assert finding.subjects == (Plant.function_id("f1", "prot"),)
    assert finding.message == (
        "function 'prot' of item f1 is rated 300 V AC (part or template rating), "
        "but rail 'L1' is at 398.4 V to earth (IT supply '400V')"
    )


def test_the_same_single_pole_rated_above_its_rail_to_earth_gives_none() -> None:
    assert check_ratings(_pole("399").model()) == ()
