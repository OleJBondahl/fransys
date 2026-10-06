"""EA2 and EA3: bare tags, the default place, one function block, unique tags."""

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.kernel import Draft
from fransys_model.vocab import Aspect, AspectNode


def _nodes(d) -> dict[str, AspectNode]:
    return {r.label: r for r in d.draft().records() if isinstance(r, AspectNode)}


def test_location_and_function_write_one_aspect_node_each(parts: Draft) -> None:
    d = design(parts, place="C1")
    d.location("C1", "Motor cabinet")
    with d.function("M1", "Pump motor starter"):
        pass
    nodes = _nodes(d)
    assert nodes["C1"].aspect is Aspect.LOCATION
    assert nodes["C1"].description == "Motor cabinet"
    assert nodes["M1"].aspect is Aspect.FUNCTION


def test_a_location_declared_twice_with_one_text_is_one_node(parts: Draft) -> None:
    d = design(parts)
    assert d.location("C1", "Cabinet") == d.location("C1", "Cabinet")
    assert len(_nodes(d)) == 1


def test_a_location_with_a_second_text_raises(parts: Draft) -> None:
    d = design(parts)
    d.location("C1", "Cabinet")
    with pytest.raises(AuthorError, match="'C1' has the text 'Cabinet' and was given 'Other'"):
        d.location("C1", "Other")


def test_the_default_place_is_made_on_first_use_with_no_text(parts: Draft) -> None:
    d = design(parts, place="C1")
    assert d._place_node("C1") is d._place_node("C1")
    assert _nodes(d)["C1"].description == ""


def test_place_none_means_no_place(parts: Draft) -> None:
    assert design(parts)._place_node(None) is None


@pytest.mark.parametrize(
    ("make", "message"),
    [
        (lambda d: d.location("+C1", "x"), "write C1; location() adds the +"),
        (lambda d: d.location("-C1", "x"), "write C1; location() adds the +"),
        (lambda d: d.function("=M1", "x").__enter__(), "write M1; function() adds the ="),
        (lambda d: d.location("", "x"), "write <tag>; location() adds the +"),
        (lambda d: design(d.library, place="+C1"), "write C1; location() adds the +"),
    ],
)
def test_a_prefixed_tag_raises_naming_the_call(parts: Draft, make, message: str) -> None:
    with pytest.raises(AuthorError, match=message.replace("(", r"\(").replace(")", r"\)")):
        make(design(parts))


def test_function_blocks_do_not_nest(parts: Draft) -> None:
    d = design(parts)
    with (
        d.function("M1", "a"),
        pytest.raises(AuthorError, match="do not nest"),
        d.function("M2", "b"),
    ):
        pass
    with d.function("M2", "b"):  # the failed nesting left the design usable
        assert d._function == "M2"
    assert d._function is None


def test_a_block_ends_on_an_exception(parts: Draft) -> None:
    d = design(parts)
    with pytest.raises(RuntimeError), d.function("M1", "a"):
        raise RuntimeError
    assert d._function is None


def test_a_tag_is_unique_per_function_and_the_key_names_both(parts: Draft) -> None:
    d = design(parts)
    with d.function("P1", "a"):
        first = d._claim("Q1", per_function=True)
        with pytest.raises(AuthorError, match="tag 'Q1' is already used in function 'P1'"):
            d._claim("Q1", per_function=True)
    with d.function("P2", "b"):
        second = d._claim("Q1", per_function=True)
    assert (first, second) == ("P1/Q1", "P2/Q1")


def test_a_design_wide_tag_ignores_the_function(parts: Draft) -> None:
    d = design(parts)
    assert d._claim("X1", per_function=False) == "X1"
    with d.function("P1", "a"), pytest.raises(AuthorError, match="tag 'X1' is already used;"):
        d._claim("X1", per_function=False)


def test_draft_is_the_engines_and_library_is_kept(parts: Draft) -> None:
    d = design(parts)
    assert d.library is parts
    assert isinstance(d.draft(), Draft)


def test_a_location_called_after_a_device_used_the_place_sets_its_text(parts: Draft) -> None:
    d = design(parts, place="C1")
    d._place_node("C1")
    d.location("C1", "Late text")
    assert _nodes(d)["C1"].description == "Late text"
    assert d.location("C1", "Late text") == d._place_node("C1")


def test_a_location_called_before_the_devices_keeps_its_text(parts: Draft) -> None:
    d = design(parts, place="C1")
    d.location("C1", "Early text")
    d._place_node("C1")
    assert _nodes(d)["C1"].description == "Early text"


def test_a_late_location_with_a_different_text_names_both_texts(parts: Draft) -> None:
    d = design(parts, place="C1")
    d._place_node("C1")
    d.location("C1", "First")
    with pytest.raises(AuthorError, match=r"'First'.*'Second'"):
        d.location("C1", "Second")
