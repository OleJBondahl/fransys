"""EA9 next-free: `take`, `take_pe` and the strip as a series element."""

import pytest
from fransys_author import AuthorError
from fransys_author.surface import TypedDevice, design
from fransys_author.surface._pairing import End

from fransys_model.vocab import TerminalFacet

from ..equivalence.series_parts import series_library  # noqa: TID252 -- same suite's stub parts


@pytest.fixture(scope="module")
def lib():
    return series_library()


def _numbers(d):
    return sorted(f.index for f in d.draft().records() if isinstance(f, TerminalFacet))


def test_take_counts_on_in_script_order(lib) -> None:
    x1 = design(lib).terminal_strip("X1", "TEST-TERM")
    first, second = x1._take(2), x1._take(2)
    assert [t.key[-1] for t in first + second] == ["1", "2", "3", "4"]


def test_an_explicit_terminal_is_skipped(lib) -> None:
    x1 = design(lib).terminal_strip("X1", "TEST-TERM")
    x1[2]
    assert [t.key[-1] for t in x1._take(2)] == ["1", "3"]


def test_the_constructor_pre_make_does_not_use_numbers(lib) -> None:
    x1 = design(lib).terminal_strip("X1", "TEST-TERM", 3)
    assert [t.key[-1] for t in x1._take(3)] == ["1", "2", "3"]


def test_an_insertion_above_renumbers(lib) -> None:
    """A release reports DESIGNATION_MOVED for the terminals an insertion pushes down."""

    def numbers(*, insert: bool) -> list[str]:
        x1 = design(lib).terminal_strip("X1", "TEST-TERM")
        if insert:
            x1._take(1)
        return [t.key[-1] for t in x1._take(2)]

    assert numbers(insert=False) == ["1", "2"]
    assert numbers(insert=True) == ["2", "3"]


def test_take_past_count_raises(lib) -> None:
    x1 = design(lib).terminal_strip("X1", "TEST-TERM", 3)
    with pytest.raises(AuthorError, match="X1 has 3 terminals; the series needs 4"):
        x1._take(4)
    x1._take(3)
    with pytest.raises(AuthorError, match="X1 has 3 terminals; the series needs 4"):
        x1._take(1)


def test_take_pe_shares_the_number_space(lib) -> None:
    d = design(lib)
    x1 = d.terminal_strip("X1", "TEST-TERM", pe="TEST-TERM-PE")
    (a,) = x1._take(1)
    pe = x1._take_pe()
    (b,) = x1._take(1)
    assert [t.key[-1] for t in (a, pe, b)] == ["1", "2", "3"]
    assert _numbers(d) == [1, 2, 3]


def test_no_pe_part_raises(lib) -> None:
    x1 = design(lib).terminal_strip("X1", "TEST-TERM")
    with pytest.raises(
        AuthorError, match=r"X1 has no PE terminal part: terminal_strip\(\.\.\., pe=P\.X\)"
    ):
        x1._take_pe()


def test_pe_takes_a_string_or_a_part_class(lib) -> None:
    class Pe(TypedDevice):
        mpn = "TEST-TERM-PE"

    d = design(lib)
    assert d.terminal_strip("X1", "TEST-TERM", pe=Pe)._take_pe() is not None
    assert d.terminal_strip("X2", "TEST-TERM", pe="TEST-TERM-PE")._take_pe() is not None


def test_series_ends_are_inner_line_and_outer_load(lib) -> None:
    x1 = design(lib).terminal_strip("X1", "TEST-TERM")
    ends = x1._series_ends(None, 2)  # ty: ignore[invalid-argument-type] -- design is unused
    ts = (x1[1], x1[2])
    assert x1._series_width() is None
    assert ends.line == tuple(End(t.inner, None) for t in ts)
    assert ends.load == tuple(End(t.outer, None) for t in ts)
    assert [t.key[-1] for t in x1._take(1)] == ["3"]


def test_terminal_strip_refuses_a_part_two_makers_make(lib) -> None:
    d = design(lib)
    with pytest.raises(AuthorError, match="MPN 'TEST-SHARED' is ambiguous across manufacturers"):
        d.terminal_strip("X1", "TEST-SHARED")
    with pytest.raises(AuthorError, match="MPN 'TEST-SHARED' is ambiguous"):
        d.terminal_strip("X2", "TEST-TERM", pe="TEST-SHARED")
