"""The one first-free allocation: the lowest whole number a taken set does not hold."""

lazy from collections.abc import Container


def first_free(taken: Container[int], start: int = 1) -> int:
    """The lowest integer from `start` upward that `taken` does not contain.

    A gap is filled before the number after the highest. `taken` is only asked `in`, so a set,
    a range or any container works; the caller adds the result to its own set. It never ends
    for a `taken` that holds every integer from `start`.
    """
    number = start
    while number in taken:
        number += 1
    return number
