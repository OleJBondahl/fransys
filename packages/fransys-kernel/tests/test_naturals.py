"""Tests: `kernel.naturals`, the one text key and the one Id order (NUMBER-SORT K7, K8).

Can-fail probe: dropping the whole-text tie from `natural_key` fails
`test_key_is_total_x1_against_x01` and `test_key_equal_only_for_equal_text`.
"""

from itertools import permutations

from hypothesis import given
from hypothesis import strategies as st

from fransys_kernel import Id, canonical, natural_join, natural_key, natural_sorted

_TEXT = st.text(alphabet="Xx01129-+ab٣", max_size=8)


def test_key_is_total_x1_against_x01() -> None:
    """`X01` and `X1` have one value but two keys: the whole text breaks the tie."""
    assert natural_key("X01") != natural_key("X1")
    assert natural_key("X01") < natural_key("X1")
    assert natural_sorted(["X1", "X01"]) == ["X01", "X1"]
    assert natural_sorted(["X01", "X1"]) == ["X01", "X1"]


@given(_TEXT, _TEXT)
def test_key_equal_only_for_equal_text(a: str, b: str) -> None:
    """Totality: equal keys mean equal texts."""
    assert (natural_key(a) == natural_key(b)) == (a == b)


@given(_TEXT, _TEXT)
def test_key_is_antisymmetric(a: str, b: str) -> None:
    """Two keys never each stand before the other."""
    assert not (natural_key(a) < natural_key(b) and natural_key(b) < natural_key(a))


@given(_TEXT, _TEXT, _TEXT)
def test_key_is_transitive(a: str, b: str, c: str) -> None:
    """`a <= b` and `b <= c` give `a <= c`."""
    if natural_key(a) <= natural_key(b) <= natural_key(c):
        assert natural_key(a) <= natural_key(c)


def test_digit_runs_sort_by_value() -> None:
    """`A2` stands before `A10`; numbers stand before text runs."""
    assert natural_sorted(["A10", "A2", "A1"]) == ["A1", "A2", "A10"]
    assert natural_sorted(["A", "2", "10"]) == ["2", "10", "A"]


def test_key_is_case_sensitive() -> None:
    """Upper case stands before lower case: `B1` before `a1`."""
    assert natural_key("B1") < natural_key("a1")


def test_non_ascii_digits_compare_as_text() -> None:
    """Renamed from `..._decimal_run_compares_as_a_number` (LIB-ADOPT N1): ASCII digits only.

    An Arabic-Indic `٣` and a superscript `²` are text runs, which stand after every number.
    """
    assert natural_sorted(["A٣", "A10"]) == ["A10", "A٣"]
    assert natural_key("A²")[0] == ((1, "A²"),)


def test_natural_join_orders_and_joins() -> None:
    """The one printed list: `-X2, -X10`."""
    assert natural_join(["-X10", "-X2"]) == "-X2, -X10"
    assert natural_join([]) == ""


def _ids() -> list[Id[object]]:
    return [
        Id(kind="port", value="p10"),
        Id(kind="port", value="p2"),
        Id(kind="item", value="p2"),
        Id(kind="port", value="p2"),
    ]


def test_canonical_orders_ids_by_their_text() -> None:
    """Ids order by `kind:value` text, digit runs by value; duplicates stay."""
    assert canonical(_ids()) == (
        Id(kind="item", value="p2"),
        Id(kind="port", value="p2"),
        Id(kind="port", value="p2"),
        Id(kind="port", value="p10"),
    )


def test_canonical_is_the_same_for_any_input_order() -> None:
    """The output does not depend on the order the ids arrive in, and is idempotent."""
    first = canonical(_ids())
    assert all(canonical(order) == first for order in permutations(_ids()))
    assert canonical(first) == first
