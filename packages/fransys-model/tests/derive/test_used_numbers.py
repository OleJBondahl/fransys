"""The numbering passes allocate by `lowest_free` over a used-number set: same numbers as before.

The old rule is `first_free` over a text set, asking `code + str(n)` in the set (kept here as a
local copy). Only an exact `code + str(n)` text uses a number (DESIGNATION-SCHEME).
"""

import pytest

from fransys_model.derive.passes.numbering_units import next_number, used_numbers
from fransys_model.refdef import lowest_free

ONE, TWO = chr(0x661), chr(0x662)  # Arabic-indic digits: str.isdigit but not ASCII


def _old(code: str, taken: set[str]) -> int:
    n = 1
    while f"{code}{n}" in taken:
        n += 1
    return n


def _run(*numbers: int, code: str = "A") -> set[str]:
    return {f"{code}{n}" for n in numbers}


CORPUS = {
    "empty": ("A", set()),
    "gaps": ("A", _run(1, 2, 4, 7)),
    "leading zero": ("A", {"A01", "A1B", "AB1", "A2"}),
    "lower case and zero": ("A", {"a1", "A0", "A-1", f"A{ONE}"}),
    "non ascii digit only": ("A", {f"A{ONE}", f"A{TWO}"}),
    "code prefixes code": ("A", _run(1, 2) | _run(1, 2, 3, code="AB")),
    "other code": ("AB", _run(1, 2) | _run(1, 2, 3, code="AB")),
    "digit code": ("A1", {"A12", "A11", "A1"}),
    "a thousand": ("A", _run(*range(1, 1001))),
    "a thousand with a hole": ("A", _run(*range(1, 1001)) - {"A500"}),
}


@pytest.mark.rule("DESIGNATION-SCHEME")
@pytest.mark.parametrize("name", CORPUS)
def test_lowest_free_over_used_numbers_equals_first_free_over_texts(name: str) -> None:
    code, taken = CORPUS[name]
    assert lowest_free(used_numbers(code, taken)) == _old(code, taken)


@pytest.mark.rule("DESIGNATION-SCHEME")
def test_only_an_exact_text_uses_a_number() -> None:
    assert used_numbers("A", {"A01", "A1B", "AB1", "a1", "A-1", f"A{ONE}", "A", "A2"}) == {2}


@pytest.mark.rule("DESIGNATION-SCHEME")
@pytest.mark.parametrize("name", CORPUS)
@pytest.mark.parametrize("codes", [("A",), ("A", "AB", "A"), ("A1", "A", "A1", "A")])
def test_fifty_allocations_equal_the_old_ones(name: str, codes: tuple[str, ...]) -> None:
    _, start = CORPUS[name]
    old_taken, new_taken = set(start), set(start)
    numbers: dict[str, set[int]] = {}
    for step in range(50):
        code = codes[step % len(codes)]
        expected = _old(code, old_taken)
        old_taken.add(f"{code}{expected}")
        assert next_number(new_taken, numbers, code) == expected
    assert new_taken == old_taken


@pytest.mark.parametrize(("taken", "expected"), [(set(), 1), ({1, 2, 4}, 3), ({1, 2, 3}, 4)])
def test_lowest_free_fills_the_lowest_gap(taken: set[int], expected: int) -> None:
    assert lowest_free(taken) == expected
