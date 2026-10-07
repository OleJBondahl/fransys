"""`check_ratings` reads rails only for a function that has a rating to check.

A model with one rated and one rating-less function: `port_rails` and `rail_pairs` run for the
rated one alone. Invented data.

Can-fail probe: `ratings.py` `check_ratings`, drop the `if not sources: continue` and the
rating-less function is read too.
"""

from plant import Plant
from rating_plant import AC_400, load, rated, supply
lazy import pytest

from fransys_model.vocab import rail_reach
from fransys_model.vocab.validators import ratings


def test_rail_readers_run_only_for_the_function_with_a_rating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    load(plant, "bare", [["L1"]], None)
    marked = load(plant, "marked", [["L1"]], rated(ac="230"))
    seen: dict[str, list[object]] = {"port_rails": [], "rail_pairs": []}
    for name, calls in seen.items():
        real = getattr(rail_reach, name)

        def counted(model, subject, real=real, calls=calls):
            calls.append(subject)
            return real(model, subject)

        monkeypatch.setattr(rail_reach, name, counted)

    ratings.check_ratings(plant.model())

    assert seen["rail_pairs"] == [marked]
    assert len(seen["port_rails"]) == 1  # the one port of `marked`; `bare`'s is never read
