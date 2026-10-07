"""A consumer reads what each part declares from a parts-only build (decision model-0165).

Built through the facade from `examples/demo-parts`, no design: a coil, a supply and a
function-less part each have rows, and `profile_of` is the same function layout reads.
"""

import fransys as fr
import pytest

import fransys_model.layout


@pytest.fixture(scope="module")
def rows() -> dict[tuple[str, str], fr.derive.PartFunctionRow]:
    """Every row of the demo library, by (mpn, function name)."""
    model = fr.build(fr.parts("demo_parts")).model
    return {(row.mpn, row.name): row for row in fr.derive.part_function_rows(model)}


def test_a_coil_has_a_row_with_its_kind(rows) -> None:
    """The relay's coil row names the kind and states no rating."""
    row = rows[("DEMO-CTR-3P-24", "coil")]
    assert row.kind is fr.derive.FunctionKind.COIL
    assert row.rating is None


def test_a_supply_has_a_row_with_its_rating(rows) -> None:
    """The controller's field supply carries its stated DC current."""
    row = rows[("DEMO-CTRL-8", "supply_field")]
    assert row.kind is fr.derive.FunctionKind.SUPPLY
    assert row.rating is not None
    assert row.rating.current_dc_a == 10


def test_a_function_less_part_has_one_row_with_the_parts_rating(rows) -> None:
    """A fuse link has no function: template and kind are `None`, the rating is the part's."""
    row = rows[("DEMO-FUSE-LINK-4A-T", "")]
    assert (row.template, row.kind) == (None, None)
    assert row.rating is not None
    assert row.rating.current_dc_a == 4


def test_profile_of_is_the_layout_reader() -> None:
    """`fr.derive.profile_of` is `fransys_model.layout.profile_of`, the house profile here."""
    model = fr.build(fr.parts("demo_parts")).model
    assert fr.derive.profile_of is fransys_model.layout.profile_of
    assert fr.derive.profile_of(model).key == ("house", "profile")
