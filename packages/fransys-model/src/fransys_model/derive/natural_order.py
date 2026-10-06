"""The one order of printed designations: digit runs compare as numbers (decision model-0149)."""

from fransys_model.vocab import marking_key

type NaturalKey = tuple[tuple[tuple[int, int, str], ...], str]


def natural_key(text: str) -> NaturalKey:
    """Sort key of a printed text: digit runs by value, so `-W2` sorts before `-W10`.

    Text runs compare as strings and sort after numbers; the whole text breaks a tie.
    """
    return marking_key(text), text
