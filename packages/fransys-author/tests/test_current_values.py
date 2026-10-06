"""The three current fields through the author API (decision model-0088).

`Operating(max_current_dc_a=...)` and `Rating(min_breaking_current_a=...)` are the model classes,
so `boundary(...)` and the catalogue readers carry the fields with no author code of their own.
"""

from decimal import Decimal

import fransys_parts
import pytest
from fransys_author import Design

from fransys_model.kernel import Draft, Origin, freeze, make_id, merge
from fransys_model.vocab import (
    Boundary,
    BoundaryValuesFacet,
    FunctionTemplate,
    InternalLink,
    LinkKind,
    Operating,
    PortRole,
    PortTemplate,
    Rating,
    boundary_operating,
    boundary_rating,
)

_ORIGIN = Origin(file="<catalogue-guards fixture>", line=1, note="test catalogue")


@pytest.fixture(scope="module")
def demo():
    return fransys_parts.load("demo_parts")


def _unit_boundary(demo, **values):
    d = Design(demo)
    u = d.scope("u1").unit("demo-unit", revision=1, interface="1")
    u.boundary(u.item("DEMO-TB-2.5", tag="X1"), **values)
    (boundary,) = [r for r in d.draft().records() if isinstance(r, Boundary)]
    (facet,) = [r for r in d.draft().records() if isinstance(r, BoundaryValuesFacet)]
    return d, boundary, facet


def test_boundary_operating_with_a_max_current_is_stored_and_read_back(demo):
    operating = Operating(max_current_dc_a=Decimal(186))
    d, boundary, facet = _unit_boundary(demo, operating=operating)
    assert facet.operating == operating
    assert facet.operating is not None
    assert facet.operating.max_current_dc_a == Decimal(186)
    assert facet.rating is None
    model = freeze(merge(demo, d.draft()))
    read = boundary_operating(model, boundary.id)
    assert read == operating
    assert read is not None
    assert isinstance(read.max_current_dc_a, Decimal)
    assert boundary_rating(model, boundary.id) is None


def test_boundary_rating_with_a_min_breaking_current_is_stored_and_read_back(demo):
    rating = Rating(current_dc_a=Decimal(400), min_breaking_current_a=Decimal(4000))
    d, boundary, facet = _unit_boundary(demo, rating=rating)
    assert facet.rating == rating
    model = freeze(merge(demo, d.draft()))
    read = boundary_rating(model, boundary.id)
    assert read == rating
    assert read is not None
    assert read.min_breaking_current_a == Decimal(4000)


def test_a_boundary_operating_stating_only_a_max_current_is_not_empty(demo):
    """The empty-value refusal reads every field, so a value with only the new field passes it."""
    operating = Operating(max_current_ac_a=Decimal(63))
    d, boundary, facet = _unit_boundary(demo, operating=operating)
    assert facet.operating == operating
    assert facet.rating is None
    model = freeze(merge(demo, d.draft()))
    assert boundary_operating(model, boundary.id) == operating

    rating = Rating(min_breaking_current_a=Decimal(1))
    d, boundary, facet = _unit_boundary(demo, rating=rating)
    assert facet.rating == rating
    assert facet.operating is None
    model = freeze(merge(demo, d.draft()))
    assert boundary_rating(model, boundary.id) == rating


def test_the_template_reader_returns_the_source_limit_of_the_demo_string(demo):
    d = Design(demo)
    operating = d.operating("DEMO-STRING-864V", "string")
    assert operating == Operating(
        nominal_voltage_v=Decimal(864),
        max_voltage_v=Decimal("985.5"),
        max_current_dc_a=Decimal(186),
    )
    assert operating is not None
    assert isinstance(operating.max_current_dc_a, Decimal)
    assert operating.max_current_ac_a is None


def test_the_rating_reader_returns_the_min_breaking_current_of_the_demo_fuse(demo):
    d = Design(demo)
    rating = d.rating("DEMO-FUSE-ABAT", "element")
    assert rating == Rating(
        voltage_dc_v=Decimal(1500),
        current_dc_a=Decimal(400),
        min_breaking_current_a=Decimal(4000),
    )
    assert rating is not None
    assert isinstance(rating.min_breaking_current_a, Decimal)
    assert d.rating("DEMO-FUSE-ABAT") is None


def test_the_part_level_reader_returns_a_min_breaking_current_from_a_part_rating(tmp_path):
    root = tmp_path / "lib"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(
        'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
    )
    (root / "parts" / "p.toml").write_text(
        'schema = 1\n\n[part]\nmpn = "F-1"\nmanufacturer = "Demo"\ndescription = "d"\n'
        'category = "protection"\nclass_code = "F"\n\n[rating]\nmin_breaking_current_a = "250"\n\n'
        '[[function]]\nname = "element"\nkind = "protection"\n'
        'ports = [{ name = "1", role = "generic" }]\n'
    )
    d = Design(fransys_parts.load_path(root))
    expected = Rating(min_breaking_current_a=Decimal(250))
    assert d.rating("F-1") == expected
    assert d.rating("F-1", "element") == expected


def test_the_feedthrough_terminal_s_internal_link_is_indexed_in_the_catalogue(demo):
    """`_catalogue.build_catalogue`'s InternalLink-indexing loop (`_catalogue.py:169-176`)
    attributes `terminal-feedthrough-2_5.toml`'s one link to its own part, keyed by the owning
    function template's part, not by the link's own id or table order."""
    catalogue = Design(demo)._catalogue
    part = catalogue.find("DEMO-TB-2.5")
    (template,) = catalogue.function_templates[part.id]
    ports = {port.name: port for port in catalogue.port_templates[template.id]}
    (link,) = catalogue.internal_links[part.id]
    assert {link.a, link.b} == {ports["internal"].id, ports["external"].id}


def test_an_internal_link_whose_port_owns_no_function_template_raises_loudly():
    """Designer ruling 2026-09-27, S-A: `_catalogue.build_catalogue`'s InternalLink-indexing
    loop indexes `port_template_function` and `function_template_part` directly, with no
    guard. A part file can never produce this state (parts lint's `LINK_PORT_UNKNOWN` rejects
    a link naming a port its own function does not own), so it is hand-built here: two port
    templates whose `function` names a `FunctionTemplate` that was never added to the draft.
    The old guards would have silently dropped the link; the direct index must raise."""
    draft = Draft()
    phantom_function = make_id(FunctionTemplate, ("phantom", "function"))
    port_a = PortTemplate(
        id=make_id(PortTemplate, ("phantom", "a")),
        key=("phantom", "a"),
        function=phantom_function,
        name="a",
        role=PortRole.GENERIC,
    )
    port_b = PortTemplate(
        id=make_id(PortTemplate, ("phantom", "b")),
        key=("phantom", "b"),
        function=phantom_function,
        name="b",
        role=PortRole.GENERIC,
    )
    draft.add(port_a, origin=_ORIGIN)
    draft.add(port_b, origin=_ORIGIN)
    draft.add(
        InternalLink(
            id=make_id(InternalLink, ("phantom", "link")),
            key=("phantom", "link"),
            a=port_a.id,
            b=port_b.id,
            kind=LinkKind.CONDUCTIVE,
        ),
        origin=_ORIGIN,
    )
    with pytest.raises(KeyError):
        Design(draft)
