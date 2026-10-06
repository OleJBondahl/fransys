"""EA colours and signals: static names whose values come from the model."""

import pytest
from fransys_author.surface import AI, AO, DI, DO, colours

from fransys_model.vocab import BASE_COLOURS, RESERVED_COLOURS, SignalType, split_colour


def _codes() -> dict[str, str]:
    return {k: v for k, v in vars(colours).items() if isinstance(v, str) and k.isupper()}


def test_the_colour_names_are_the_model_codes_and_gnye() -> None:
    assert set(_codes()) == set(BASE_COLOURS) | set(RESERVED_COLOURS) | {"GNYE"}


def test_every_colour_value_is_its_name_and_a_legal_colour() -> None:
    for name, value in _codes().items():
        assert value == name
        assert split_colour(value) is not None


def test_a_name_the_model_lacks_cannot_be_imported() -> None:
    with pytest.raises(ImportError):
        exec("from fransys_author.surface.colours import XX")  # noqa: S102 -- the import is the test


def test_the_four_signal_names() -> None:
    assert (DI, DO, AI, AO) == (
        SignalType.DI,
        SignalType.DO,
        SignalType.AI_CURRENT,
        SignalType.AO_CURRENT,
    )
