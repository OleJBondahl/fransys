"""`s.rating(...)` and `s.operating(...)`: a scope reads a part's values from the catalogue (Q6)."""

from decimal import Decimal

import fransys_parts
import pytest
from fransys_author import AuthorError, Design

from fransys_model.derive import function_rating
from fransys_model.kernel import freeze, merge
from fransys_model.vocab import Operating, Rating

_LIBRARY = 'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'


def _part(mpn: str, manufacturer: str, body: str = "", functions: str = "") -> str:
    head = (
        f'schema = 1\n\n[part]\nmpn = "{mpn}"\nmanufacturer = "{manufacturer}"\n'
        'description = "d"\ncategory = "generic"\nclass_code = "X"\n'
    )
    return head + body + functions


def _function(name: str, tables: str = "") -> str:
    return (
        f'\n[[function]]\nname = "{name}"\nkind = "generic"\n'
        f'ports = [{{ name = "{name}", role = "generic" }}]\n{tables}'
    )


# RT-1: a part rating (AC and DC) and four functions: `sw` has a template rating with AC only,
# `plain` and `coil` have none, `bare` has no facet at all. `coil` has an operating envelope.
_RT1 = _part(
    "RT-1",
    "Demo",
    '\n[rating]\nvoltage_ac_v = "500"\nvoltage_dc_v = "48"\ncurrent_dc_a = "10"\n',
    _function("sw", '\n[function.rating]\nvoltage_ac_v = "250"\ncurrent_ac_a = "0.5"\n')
    + _function("plain")
    + _function(
        "coil",
        '\n[function.operating]\nnominal_voltage_v = "24"\nmin_voltage_v = "18"\n'
        'max_voltage_v = "30"\ncapacity_ah = "7.2"\n',
    )
    + _function("bare"),
)
# RT-2 has no rating and no operating facet. RT-3 has a template rating and no part rating.
_RT2 = _part("RT-2", "Demo", functions=_function("f"))
_RT3 = _part(
    "RT-3",
    "Demo",
    functions=_function("f", '\n[function.rating]\nvoltage_dc_v = "24"\n'),
)
# One MPN from two manufacturers: ambiguous when bare.
_AMB_A = _part("AMB-1", "Alpha", functions=_function("f"))
_AMB_B = _part("AMB-1", "Beta", functions=_function("f"))


@pytest.fixture
def library(tmp_path):
    root = tmp_path / "lib"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    for name, text in (
        ("rt1", _RT1),
        ("rt2", _RT2),
        ("rt3", _RT3),
        ("amb_a", _AMB_A),
        ("amb_b", _AMB_B),
    ):
        (root / "parts" / f"{name}.toml").write_text(text)
    return fransys_parts.load_path(root)


_PART_RATING = Rating(voltage_ac_v=Decimal(500), voltage_dc_v=Decimal(48), current_dc_a=Decimal(10))
_SW_RATING = Rating(voltage_ac_v=Decimal(250), current_ac_a=Decimal("0.5"))


def test_rating_without_a_function_is_the_parts_own(library):
    s = Design(library)
    assert s.rating("RT-1") == _PART_RATING
    assert s.rating("RT-2") is None


def test_rating_with_a_function_is_the_templates_else_the_parts_else_none(library):
    s = Design(library)
    assert s.rating("RT-1", "sw") == _SW_RATING
    assert s.rating("RT-1", "plain") == _PART_RATING
    assert s.rating("RT-2", "f") is None
    assert s.rating("RT-3", "f") == Rating(voltage_dc_v=Decimal(24))
    assert s.rating("RT-3") is None


def test_a_template_rating_with_only_ac_hides_the_parts_dc(library):
    s = Design(library)
    rating = s.rating("RT-1", "sw")
    assert rating is not None
    assert rating.voltage_dc_v is None
    assert rating.current_dc_a is None
    assert s.rating("RT-1") == _PART_RATING


def test_operating_is_the_templates_or_none(library):
    s = Design(library)
    operating = s.operating("RT-1", "coil")
    assert operating == Operating(
        nominal_voltage_v=Decimal(24),
        min_voltage_v=Decimal(18),
        max_voltage_v=Decimal(30),
        capacity_ah=Decimal("7.2"),
    )
    assert operating is not None
    assert isinstance(operating.nominal_voltage_v, Decimal)
    assert isinstance(operating.capacity_ah, Decimal)
    assert s.operating("RT-1", "bare") is None
    assert s.operating("RT-2", "f") is None


def test_a_manufacturer_mpn_pair_resolves(library):
    s = Design(library)
    assert s.rating(("Demo", "RT-1")) == _PART_RATING
    assert s.rating(("Demo", "RT-1"), "sw") == _SW_RATING
    assert s.operating(("Demo", "RT-1"), "coil") == s.operating("RT-1", "coil")
    assert s.rating(("Alpha", "AMB-1")) is None


def _message(call) -> str:
    with pytest.raises(AuthorError) as raised:
        call()
    return str(raised.value)


@pytest.mark.parametrize("mpn", ["NOPE-9", "RT-11", ("Demo", "RT-9"), ("Nobody", "RT-1"), "AMB-1"])
def test_unknown_and_ambiguous_mpns_read_like_item(library, mpn):
    s = Design(library)
    expected = _message(lambda: s.item(mpn, tag="X1"))
    assert _message(lambda: s.rating(mpn)) == expected
    assert _message(lambda: s.rating(mpn, "f")) == expected
    assert _message(lambda: s.operating(mpn, "f")) == expected


def test_the_ambiguous_mpn_message_asks_for_the_pair(library):
    s = Design(library)
    assert "ambiguous across manufacturers (Alpha, Beta)" in _message(lambda: s.rating("AMB-1"))


def test_a_function_no_template_has_is_refused_naming_the_part(library):
    s = Design(library)
    for call in (lambda: s.rating("RT-1", "nope"), lambda: s.operating("RT-1", "nope")):
        message = _message(call)
        assert "'RT-1'" in message
        assert "'nope'" in message
        assert "it has: bare, coil, plain, sw" in message


@pytest.mark.parametrize("function", [1, b"sw", ("sw",), True])
def test_a_function_that_is_not_a_str_is_refused(library, function):
    s = Design(library)
    with pytest.raises(AuthorError, match=r"part 'RT-1' has no function named .*str"):
        s.rating("RT-1", function)
    with pytest.raises(AuthorError, match=r"part 'RT-1' has no function named .*str"):
        s.operating("RT-1", function)
    assert s.rating("RT-1", "sw") == _SW_RATING


def test_the_refusal_lists_the_functions_the_part_has(library):
    s = Design(library)
    assert "it has: f" in _message(lambda: s.rating("RT-2", "g"))


def test_a_read_adds_nothing_to_the_draft(library):
    d = Design(library)
    panel = d.scope("panel")
    before = d.draft().records()
    panel.rating("RT-1")
    panel.rating("RT-1", "sw")
    panel.operating("RT-1", "coil")
    d.rating("RT-3", "f")
    with pytest.raises(AuthorError):
        d.rating("RT-1", "nope")
    assert d.draft().records() == before


def test_the_scope_read_equals_the_models_function_rating(library):
    d = Design(library)
    k1 = d.item("RT-1", tag="K1")
    k3 = d.item("RT-3", tag="K3")
    k2 = d.item("RT-2", tag="K2")
    model = freeze(merge(library, d.draft()))
    for item, mpn, names in (
        (k1, "RT-1", ("sw", "plain", "coil", "bare")),
        (k3, "RT-3", ("f",)),
        (k2, "RT-2", ("f",)),
    ):
        for name in names:
            assert d.rating(mpn, name) == function_rating(model, item.fn(name).id), (mpn, name)
