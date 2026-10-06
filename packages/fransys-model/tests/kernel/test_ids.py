"""WP2 tests: `kernel.ids` (ROADMAP WP2, design/kernel-records.md 5.2)."""

from itertools import permutations
from typing import Any

import pytest

from fransys_model.kernel import Id, ModelError, SchemaError, make_id
from fransys_model.kernel.ids import parse_id, render_id


def test_make_id_is_deterministic(thing_cls: type) -> None:
    """The same `record_type` and key always produce the same id, run twice."""
    key = ("aux", "pumps", "pump1")
    assert make_id(thing_cls, key) == make_id(thing_cls, key)


def test_make_id_differs_by_kind(thing_cls: type, link_cls: type) -> None:
    """Two different record types with the same key get different ids."""
    key = ("aux", "pumps", "pump1")
    assert make_id(thing_cls, key) != make_id(link_cls, key)


def test_make_id_differs_by_key(thing_cls: type) -> None:
    """Two different keys on the same record type get different ids."""
    assert make_id(thing_cls, ("a", "b")) != make_id(thing_cls, ("a", "c"))


def test_make_id_rejects_separator_in_key_segment(thing_cls: type) -> None:
    r"""A segment holding `\x1f` is rejected, so `("a","b")` never collides with `("a\x1fb",)`."""
    with pytest.raises(ModelError):
        make_id(thing_cls, ("a\x1fb",))


@pytest.mark.parametrize("key", [(), ("a", "")])
def test_make_id_rejects_empty_key_or_segment(thing_cls: type, key: tuple[str, ...]) -> None:
    """An empty key, or a key with an empty segment, is rejected."""
    with pytest.raises(ModelError):
        make_id(thing_cls, key)


def test_id_is_hashable_and_not_a_str() -> None:
    """`Id` can key a `dict`/`frozendict` and is not interchangeable with a plain `str`."""
    an_id = Id(kind="thing", value="0" * 32)
    assert hash(an_id) == hash(Id(kind="thing", value="0" * 32))
    assert not isinstance(an_id, str)


def test_id_orders_by_kind_then_value() -> None:
    """`Id` instances order by `(kind, value)`."""
    lower = Id(kind="a", value="1")
    higher = Id(kind="b", value="0")
    assert lower < higher


def test_make_id_value_is_pinned_across_machines(thing_cls: type) -> None:
    """A golden value: the namespace, separator or hashing changing would change every id."""
    assert make_id(thing_cls, ("aux", "pumps", "pump1")) == Id(
        kind="thing", value="53c14214f97b5f25a561c34375da3ba0"
    )


def test_make_id_key_segments_are_not_concatenated(thing_cls: type) -> None:
    """The separator keeps `("a","bc")`, `("ab","c")` and `("abc",)` apart, and order counts."""
    ids = {make_id(thing_cls, key) for key in [("a", "bc"), ("ab", "c"), ("abc",), ("bc", "a")]}
    assert len(ids) == 4


@pytest.mark.parametrize(
    "key",
    [("a\x1fb",), ("ok", "a\x1fb"), ("ok", "", "ok"), ("",), ("ok", ""), ()],
    ids=[
        "separator-first",
        "separator-later",
        "empty-middle",
        "only-empty",
        "empty-last",
        "no-segments",
    ],
)
def test_make_id_rejects_bad_keys_with_schema_error(thing_cls: type, key: tuple[str, ...]) -> None:
    """A bad segment anywhere in the key is a `SchemaError` naming the kind."""
    with pytest.raises(SchemaError) as excinfo:
        make_id(thing_cls, key)
    assert excinfo.value.kind == "thing"


def test_make_id_rejects_a_class_that_is_not_a_record_kind() -> None:
    """A `@value` class has no kind, so it cannot have ids."""
    with pytest.raises(SchemaError, match="not a @record kind") as excinfo:
        make_id(Id, ("a",))
    assert excinfo.value.kind == "Id"


def test_make_id_does_not_inherit_a_parent_kind(thing_cls: type) -> None:
    """A subclass is not itself a kind: reusing the parent's kind would alias ids."""
    sub = type("Sub", (thing_cls,), {})

    with pytest.raises(SchemaError, match="not a @record kind") as excinfo:
        make_id(sub, ("a",))
    assert excinfo.value.kind == "Sub"


def test_id_can_key_a_frozendict() -> None:
    """`Id` is usable as the key type of the model's tables."""
    an_id = Id(kind="thing", value="0" * 32)
    assert frozendict({an_id: "row"})[Id(kind="thing", value="0" * 32)] == "row"


def test_id_orders_by_value_within_a_kind_and_supports_every_comparison() -> None:
    """Equal kinds fall back to `value`; `<=`, `>`, `>=` follow, and `==` still holds."""
    low = Id(kind="a", value="1")
    high = Id(kind="a", value="2")
    assert low < high
    assert low <= high
    assert high > low
    assert high >= low
    assert low <= Id(kind="a", value="1")
    assert not low < Id(kind="a", value="1")


def test_id_sorts_the_same_whatever_the_input_order() -> None:
    """Sorting ids is a total order: every arrangement of the same ids sorts identically."""
    ids = [Id(kind="b", value="0"), Id(kind="a", value="9"), Id(kind="a", value="1")]
    expected = [Id(kind="a", value="1"), Id(kind="a", value="9"), Id(kind="b", value="0")]
    for order in permutations(ids):
        assert sorted(order) == expected


def test_id_does_not_order_against_other_types() -> None:
    """Comparing an `Id` with a `str` is a `TypeError`, not a silent answer."""
    with pytest.raises(TypeError):
        _ = Id(kind="a", value="1") < "a"


@pytest.mark.parametrize(
    "key",
    ["ab", ["a", "b"], ("a", 1), ("a", 0), ("a", None), ("a", b"b"), ("a", ("b",))],
    ids=["str", "list", "int", "zero", "none", "bytes", "nested-tuple"],
)
def test_make_id_rejects_a_key_that_is_not_a_tuple_of_str(thing_cls: type, key: Any) -> None:
    """A `str` or `list` key would share the id of the equal tuple; the rest were misdiagnosed."""
    with pytest.raises(SchemaError, match="not a tuple of str") as excinfo:
        make_id(thing_cls, key)
    assert excinfo.value.kind == "thing"


def test_make_id_rejects_a_lone_surrogate_as_a_schema_error(thing_cls: type) -> None:
    """A lone surrogate (JSON can carry one) cannot be encoded, so it is a `SchemaError`."""
    with pytest.raises(SchemaError, match="UTF-8") as excinfo:
        make_id(thing_cls, ("a", "\ud800"))
    assert excinfo.value.kind == "thing"


@pytest.mark.parametrize("not_a_class", ["thing", None, 42], ids=["kind-name", "none", "int"])
def test_make_id_rejects_something_that_is_not_a_class(not_a_class: Any) -> None:
    """A kind name given where the class belongs is a `SchemaError`, not a `vars()` `TypeError`."""
    with pytest.raises(SchemaError, match="not a @record kind") as excinfo:
        make_id(not_a_class, ("a",))
    assert excinfo.value.kind == repr(not_a_class)


def test_make_id_rejects_a_record_instance(thing_cls: Any) -> None:
    """An instance of a record is not the record type."""
    instance = thing_cls(id=Id(kind="thing", value="0" * 32), key=("a",), name="x")
    with pytest.raises(SchemaError, match="not a @record kind") as excinfo:
        make_id(instance, ("a",))
    assert excinfo.value.kind == getattr(instance, "__qualname__", repr(instance))


def test_render_id_is_kind_colon_value() -> None:
    """The one place an `Id` becomes text: `kind:value`."""
    assert render_id(Id(kind="layout.page", value="ab" * 16)) == "layout.page:" + "ab" * 16


def test_parse_id_reads_what_render_id_wrote() -> None:
    """The round trip, for a plain kind and a dotted one."""
    for kind in ("thing", "facet.terminal"):
        an_id = Id(kind=kind, value="0f" * 16)
        assert parse_id(render_id(an_id)) == an_id


def test_parse_id_splits_on_the_first_colon_only() -> None:
    """The kind grammar forbids `:`, so anything after the first one is the value."""
    assert parse_id("thing:a:b") == Id(kind="thing", value="a:b")


def test_parse_id_does_not_insist_on_hex() -> None:
    """Fixtures build readable ids by hand, so the value is not validated."""
    assert parse_id("thing:not-hex") == Id(kind="thing", value="not-hex")


@pytest.mark.parametrize(
    "text", ["", "thing", ":abc", "thing:"], ids=["empty", "no-colon", "no-kind", "no-value"]
)
def test_parse_id_refuses_text_that_is_not_kind_colon_value(text: str) -> None:
    """A missing kind, value or separator is a `SchemaError`, not a stray `ValueError`."""
    with pytest.raises(SchemaError, match="not `kind:value`") as excinfo:
        parse_id(text)
    assert excinfo.value.kind == "id"


@pytest.mark.parametrize(
    ("kind", "value"),
    [("", "abc"), ("thing", ""), ("a:b", "abc")],
    ids=["no-kind", "no-value", "colon-in-kind"],
)
def test_an_id_that_render_id_could_not_write_back_is_refused(kind: str, value: str) -> None:
    """Both halves are needed, and a colon in the kind would move the separator."""
    with pytest.raises(SchemaError, match="an Id needs") as excinfo:
        Id(kind=kind, value=value)
    assert excinfo.value.kind == "id"


def test_a_colon_in_the_value_is_fine() -> None:
    """The first colon is the separator, so the value may hold more."""
    made = Id(kind="thing", value="a:b")
    assert parse_id(render_id(made)) == made
