"""WP8 tests: type-level vocab kinds (ROADMAP WP8, design/vocabulary.md 6 "Type level")."""

import pytest

from fransys_model.kernel import (
    Draft,
    Id,
    Model,
    Origin,
    SchemaError,
    freeze,
    from_data,
    make_id,
    to_data,
)
from fransys_model.vocab.enums import (
    ConductorMark,
    FunctionKind,
    LinkKind,
    LinkRest,
    PartCategory,
    PoleSide,
    PortRole,
    ProtectionType,
)
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, Part, PortTemplate


def test_part_has_the_designed_fields() -> None:
    """`Part` carries `mpn`, `manufacturer`, `description`, `category`, `class_code`."""
    part_id = Id(kind="part", value="0" * 32)
    part = Part(
        id=part_id,
        key=("examples", "relay"),
        mpn="EXAMPLE-RELAY-1",
        manufacturer="Example Co",
        description="Invented example relay",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    assert part.mpn == "EXAMPLE-RELAY-1"
    assert part.class_code == "K"
    assert part.category is PartCategory.ELECTROMECHANICAL


def test_function_template_has_the_designed_fields() -> None:
    """`FunctionTemplate` carries `part`, `name`, `kind`."""
    part_id = Id(kind="part", value="0" * 32)
    coil = FunctionTemplate(
        id=Id(kind="function_template", value="1" * 32),
        key=("examples", "relay", "fn", "coil"),
        part=part_id,
        name="coil",
        kind=FunctionKind.COIL,
    )
    assert coil.part == part_id
    assert coil.kind is FunctionKind.COIL


def test_port_template_has_the_designed_fields() -> None:
    """`PortTemplate` carries `function`, `name`, `role`."""
    function_id = Id(kind="function_template", value="1" * 32)
    a1 = PortTemplate(
        id=Id(kind="port_template", value="2" * 32),
        key=("examples", "relay", "fn", "coil", "port", "A1"),
        function=function_id,
        name="A1",
        role=PortRole.GENERIC,
    )
    assert a1.function == function_id
    assert a1.name == "A1"


def test_internal_link_has_the_designed_fields() -> None:
    """`InternalLink` carries `a`, `b`, `kind`; a CO contact's two legs are `SWITCHED`."""
    port_11 = Id(kind="port_template", value="3" * 32)
    port_14 = Id(kind="port_template", value="4" * 32)
    link = InternalLink(
        id=Id(kind="internal_link", value="5" * 32),
        key=("examples", "relay", "fn", "co_1", "link", "11-14"),
        a=port_11,
        b=port_14,
        kind=LinkKind.SWITCHED,
    )
    assert link.kind is LinkKind.SWITCHED
    assert {link.a, link.b} == {port_11, port_14}


def test_internal_link_ends_normalise_order_at_construction() -> None:
    """`InternalLink.a`/`b` are stored in id order, whichever end is called `a`
    (design/vocabulary.md 6 and design/connectivity.md)."""
    port_11 = Id(kind="port_template", value="3" * 32)
    port_14 = Id(kind="port_template", value="4" * 32)
    link_forward = InternalLink(
        id=Id(kind="internal_link", value="5" * 32),
        key=("examples", "relay", "fn", "co_1", "link", "11-14"),
        a=port_11,
        b=port_14,
        kind=LinkKind.SWITCHED,
    )
    link_backward = InternalLink(
        id=Id(kind="internal_link", value="5" * 32),
        key=("examples", "relay", "fn", "co_1", "link", "11-14"),
        a=port_14,
        b=port_11,
        kind=LinkKind.SWITCHED,
    )
    assert link_forward.a == link_backward.a == port_11
    assert link_forward.b == link_backward.b == port_14


def test_internal_link_refuses_the_same_port_template_at_both_ends() -> None:
    """Exactly two ends means two different port templates."""
    port_11 = Id(kind="port_template", value="3" * 32)
    link_id = Id(kind="internal_link", value="5" * 32)
    with pytest.raises(SchemaError) as excinfo:
        InternalLink(
            id=link_id,
            key=("examples", "relay", "fn", "co_1", "link", "11-11"),
            a=port_11,
            b=port_11,
            kind=LinkKind.SWITCHED,
        )
    assert excinfo.value.record_id == link_id
    assert excinfo.value.kind == "internal_link"
    assert "an internal link joins two different port templates" in str(excinfo.value)


def test_order_ends_leaves_both_ends_alone_when_only_one_is_not_an_id() -> None:
    """One end that is not an `Id` already skips the swap (`freeze()` reports the bad value
    later); a second, valid `Id` end must not turn the skip off (mutmut id 2 of `_order_ends`:
    `or` in the type guard, mutated to `and`)."""
    port_14 = Id(kind="port_template", value="4" * 32)
    link = InternalLink(
        id=Id(kind="internal_link", value="5" * 32),
        key=("examples", "relay", "fn", "co_1", "link", "11-14"),
        a=port_14,
        b="not-a-port-template",  # ty: ignore[invalid-argument-type] -- deliberately not an `Id`, the one end this test needs to skip the swap
        kind=LinkKind.SWITCHED,
    )
    assert link.a == port_14
    assert link.b == "not-a-port-template"


def test_internal_link_refusal_message_is_exact() -> None:
    """The refusal text is exactly the spec's wording, not merely a substring of it (mutmut id 9
    of `InternalLink.__post_init__`: the message argument passed to `_order_ends`)."""
    port_11 = Id(kind="port_template", value="3" * 32)
    with pytest.raises(SchemaError) as excinfo:
        InternalLink(
            id=Id(kind="internal_link", value="5" * 32),
            key=("examples", "relay", "fn", "co_1", "link", "11-11"),
            a=port_11,
            b=port_11,
            kind=LinkKind.SWITCHED,
        )
    assert str(excinfo.value) == "an internal link joins two different port templates"


def test_internal_link_permutation_leaves_the_authoring_key_alone() -> None:
    """Swapping which end is called `a` canonicalises the fields, not the authoring key (SC7)."""
    port_11 = Id(kind="port_template", value="3" * 32)
    port_14 = Id(kind="port_template", value="4" * 32)
    key = ("examples", "relay", "fn", "co_1", "link", "11-14")
    link_forward = InternalLink(
        id=Id(kind="internal_link", value="5" * 32),
        key=key,
        a=port_11,
        b=port_14,
        kind=LinkKind.SWITCHED,
    )
    link_backward = InternalLink(
        id=Id(kind="internal_link", value="5" * 32),
        key=key,
        a=port_14,
        b=port_11,
        kind=LinkKind.SWITCHED,
    )
    assert link_forward.key == link_backward.key == key
    assert link_forward.a == link_backward.a
    assert link_forward.b == link_backward.b


@pytest.mark.parametrize("kind", [LinkKind.CONDUCTIVE, LinkKind.PROTECTIVE])
def test_internal_link_refuses_a_rest_state_unless_it_is_switched(kind: LinkKind) -> None:
    """A rest state belongs to a switched link; the same `rest` on a switched one is accepted."""
    link_id = Id(kind="internal_link", value="5" * 32)
    a, b = Id(kind="port_template", value="3" * 32), Id(kind="port_template", value="4" * 32)
    with pytest.raises(SchemaError) as excinfo:
        InternalLink(id=link_id, key=("k",), kind=kind, rest=LinkRest.OPEN, a=a, b=b)
    assert excinfo.value.record_id == link_id
    assert "only a switched internal link has a rest state" in str(excinfo.value)
    kept = InternalLink(
        id=link_id, key=("k",), kind=LinkKind.SWITCHED, rest=LinkRest.OPEN, a=a, b=b
    )
    assert kept.rest is LinkRest.OPEN


def test_port_template_pole_side_and_conductor_mark_default_to_none() -> None:
    """F9: a port that states neither fact has `None` for both."""
    port = PortTemplate(
        id=Id(kind="port_template", value="2" * 32),
        key=("examples", "motor", "fn", "motor", "port", "U"),
        function=Id(kind="function_template", value="1" * 32),
        name="U",
        role=PortRole.GENERIC,
    )
    assert port.pole_side is None
    assert port.conductor_mark is None


def test_port_template_pole_side_and_conductor_mark_round_trip() -> None:
    """F9: both facts survive an encode/decode round trip through a frozen model."""
    draft = Draft()
    part_key = ("examples", "psu")
    fn_key = (*part_key, "fn", "out")
    function_id = make_id(FunctionTemplate, fn_key)
    port_key = (*fn_key, "port", "+")
    port_id = make_id(PortTemplate, port_key)
    origin = Origin(file="t.toml", line=1, note="")
    part = Part(
        id=make_id(Part, part_key),
        key=part_key,
        mpn="X",
        manufacturer="M",
        description="d",
        category=PartCategory.GENERIC,
        class_code="T",
    )
    draft.add(part, origin=origin)
    draft.add(
        FunctionTemplate(
            id=function_id, key=fn_key, part=part.id, name="out", kind=FunctionKind.SUPPLY
        ),
        origin=origin,
    )
    draft.add(
        PortTemplate(
            id=port_id,
            key=port_key,
            function=function_id,
            name="+",
            role=PortRole.GENERIC,
            pole_side=PoleSide.LOAD,
            conductor_mark=ConductorMark.L_PLUS,
        ),
        origin=origin,
    )
    model = freeze(draft)
    again = from_data(to_data(model))
    port = again.tables["port_template"][port_id]
    assert isinstance(port, PortTemplate)
    assert port.pole_side is PoleSide.LOAD
    assert port.conductor_mark is ConductorMark.L_PLUS


def _function(kind: FunctionKind, protection_type: ProtectionType | None) -> FunctionTemplate:
    part_key = ("examples", "breaker")
    fn_key = (*part_key, "fn", "f")
    return FunctionTemplate(
        id=make_id(FunctionTemplate, fn_key),
        key=fn_key,
        part=make_id(Part, part_key),
        name="f",
        kind=kind,
        protection_type=protection_type,
    )


def _model_with(function: FunctionTemplate) -> Model:
    part_key = ("examples", "breaker")
    origin = Origin(file="t.toml", line=1, note="")
    draft = Draft()
    draft.add(
        Part(
            id=make_id(Part, part_key),
            key=part_key,
            mpn="X",
            manufacturer="M",
            description="d",
            category=PartCategory.GENERIC,
            class_code="F",
        ),
        origin=origin,
    )
    draft.add(function, origin=origin)
    return freeze(draft)


def test_function_template_protection_type_defaults_to_none_and_is_written_null() -> None:
    """Not declared is `None` and the canonical form writes the key as null (model-0127)."""
    bare = _function(FunctionKind.PROTECTION, None)
    assert bare.protection_type is None
    written = to_data(_model_with(bare))["tables"]["function_template"]
    assert [row["protection_type"] for row in written] == [None]


def test_function_template_protection_type_round_trips() -> None:
    """A protection function keeps its `ProtectionType` through `to_data` and `from_data`."""
    typed = _function(FunctionKind.PROTECTION, ProtectionType.MCB)
    data = to_data(_model_with(typed))
    assert data["tables"]["function_template"][0]["protection_type"] == "mcb"
    assert from_data(data).tables["function_template"][typed.id] == typed


@pytest.mark.parametrize("kind", [k for k in FunctionKind if k is not FunctionKind.PROTECTION])
def test_function_template_refuses_a_protection_type_unless_it_is_protection(
    kind: FunctionKind,
) -> None:
    """Only `kind = protection` takes a type; the same type on a protection one is accepted."""
    with pytest.raises(SchemaError) as excinfo:
        _function(kind, ProtectionType.FUSE)
    assert "only a protection function has a protection type" in str(excinfo.value)
