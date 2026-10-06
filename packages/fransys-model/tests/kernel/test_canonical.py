"""WP6 tests: `kernel.canonical`, `dumps`/`loads` and the digests (ROADMAP WP6,
design/kernel-model.md 5.6)."""

from decimal import Decimal
from typing import Any

import pytest
from canon_probes import (
    CanonDerived,
    CanonDetail,
    CanonFacet,
    CanonLayout,
    Shade,
    derived_id,
    draft_of,
    item_id,
    make_item,
    make_owner,
    model_of,
    owner_id,
)

from fransys_model.kernel import (
    Draft,
    FreezeError,
    Id,
    Origin,
    SchemaVersionError,
    ValueTypeError,
    dumps,
    freeze,
    from_data,
    loads,
    register_namespaces,
)


def test_loads_dumps_roundtrip(thing_cls: type, origin: Origin) -> None:
    """`loads(dumps(m)) == m` for a model with at least one record."""
    draft = Draft()
    thing = thing_cls(id=Id(kind="thing", value="1" * 32), key=("a",), name="pump")
    draft.add(thing, origin=origin)
    model = freeze(draft)
    assert loads(dumps(model)) == model


def test_dumps_byte_stable_across_insertion_order(thing_cls: type, origin: Origin) -> None:
    """The same records, added in two different orders, dump to the same bytes."""
    first_draft, second_draft = Draft(), Draft()
    thing_a = thing_cls(id=Id(kind="thing", value="a" * 32), key=("a",), name="pump-a")
    thing_b = thing_cls(id=Id(kind="thing", value="b" * 32), key=("b",), name="pump-b")
    first_draft.add(thing_a, origin=origin)
    first_draft.add(thing_b, origin=origin)
    second_draft.add(thing_b, origin=origin)
    second_draft.add(thing_a, origin=origin)
    assert dumps(freeze(first_draft)) == dumps(freeze(second_draft))


def test_digest_changes_when_field_changes(thing_cls: type, origin: Origin) -> None:
    """Changing a record field changes the model digest."""
    an_id = Id(kind="thing", value="1" * 32)
    draft = Draft()
    draft.add(thing_cls(id=an_id, key=("a",), name="pump"), origin=origin)
    before = freeze(draft).digest
    changed = Draft()
    changed.add(thing_cls(id=an_id, key=("a",), name="valve"), origin=origin)
    after = freeze(changed).digest
    assert before != after


def test_digest_unchanged_when_only_origins_change(thing_cls: type) -> None:
    """Two models differing only in `Origin` (file/line) have the same digest."""
    thing = thing_cls(id=Id(kind="thing", value="1" * 32), key=("a",), name="pump")
    first = Draft()
    first.add(thing, origin=Origin(file="a.py", line=1, note=""))
    second = Draft()
    second.add(thing, origin=Origin(file="b.py", line=99, note="moved"))
    assert freeze(first).digest == freeze(second).digest


def test_from_data_raises_on_schema_version_mismatch() -> None:
    """A `schema_version` this build does not know is a hard error, not a migration."""
    with pytest.raises(SchemaVersionError):
        from_data(frozendict({"schema_version": -1}))


def _rich(origin: Origin) -> Any:
    """A model holding every annotation shape, an alias, and every kind of `ext` value."""
    detail = CanonDetail(amount=Decimal("2.50"), owner=owner_id("1"), shade=Shade.BLUE)
    ext = frozendict(
        {
            "id": owner_id("1"),
            "map": frozendict({"a.b": (1, frozendict({"$id": "not a tag"}))}),
            "tuple": ("x", None, True, 7),
            "text": "1.5",
        }
    )
    bare = CanonDetail(amount=Decimal(0), owner=owner_id("1"))  # shade is None: an optional enum
    item = make_item("2", maybe=owner_id("1"), details=(detail, bare), note="Ærlig vær å", ext=ext)
    draft = draft_of(origin, make_owner("1"), item, make_item("3", owner=owner_id("9")))
    draft.alias(owner_id("9"), owner_id("1"))
    return freeze(draft)


def test_a_rich_model_survives_the_round_trip(origin: Origin) -> None:
    """Decimals, both enum kinds, nested values, tags, aliases and Norwegian text all come back."""
    model = _rich(origin)
    reloaded = loads(dumps(model))
    assert reloaded == model
    assert reloaded.hashes == model.hashes
    assert reloaded.digests == model.digests
    assert reloaded.digest == model.digest
    assert dumps(reloaded) == dumps(model)


def test_a_decimal_comes_back_equal_though_written_in_its_canonical_form(origin: Origin) -> None:
    """`Decimal("1.50")` is written `1.5`, and `Decimal("1.5")` equals it."""
    model = model_of(origin, make_owner("1"), make_item("2", amount=Decimal("1.50")))
    reloaded = loads(dumps(model))
    reloaded_item: Any = reloaded.tables["canon_item_probe"][item_id("2")]
    assert reloaded_item.amount == Decimal("1.5")
    assert reloaded == model


def test_two_spellings_of_one_decimal_give_one_dump_and_one_digest(origin: Origin) -> None:
    """The ROADMAP's own case: they compare and hash equal, so they must dump equal."""
    spelt_long = model_of(origin, make_owner("1"), make_item("2", amount=Decimal("1.50")))
    spelt_short = model_of(origin, make_owner("1"), make_item("2", amount=Decimal("1.5")))
    assert dumps(spelt_long) == dumps(spelt_short)
    assert spelt_long.digest == spelt_short.digest
    assert spelt_long.hashes == spelt_short.hashes


def test_a_reloaded_model_is_attributed_to_the_canonical_text(origin: Origin) -> None:
    """Origins are not carried, so every record answers with the one stand-in origin."""
    reloaded = loads(dumps(model_of(origin, make_owner("1"))))
    assert reloaded.origin_of(owner_id("1")) == Origin(file="<canonical>", line=0, note="")


def test_models_that_differ_only_in_origins_are_equal(origin: Origin) -> None:
    """`origins` is not compared: a moved line is not a change to the plant."""
    moved = Origin(file="elsewhere.py", line=40, note="moved")
    assert model_of(origin, make_owner("1")) == model_of(moved, make_owner("1"))


def test_the_canonical_text_is_pinned_byte_for_byte() -> None:
    """A golden: a change to keys, order, indent or the id text changes every golden file."""
    origin = Origin(file="golden.py", line=1, note="")
    text = dumps(model_of(origin, make_owner("1")))
    assert text == (
        "{\n"
        '  "aliases": [],\n'
        '  "schema_version": 8,\n'
        '  "tables": {\n'
        '    "canon_owner_probe": [\n'
        "      {\n"
        '        "ext": {},\n'
        '        "id": "canon_owner_probe:' + "1" * 32 + '",\n'
        '        "key": [\n'
        '          "1"\n'
        "        ]\n"
        "      }\n"
        "    ]\n"
        "  }\n"
        "}\n"
    )


def _three_namespaces(origin: Origin, *, x: int = 5, subject_note: str = "a") -> Any:
    register_namespaces("facet", "layout")
    owner = make_owner("1")
    facet = CanonFacet(
        id=Id(kind="facet.canon_facet_probe", value="2" * 32),
        key=("f",),
        subject=owner_id("1"),
        ext=frozendict({"note": subject_note}),
    )
    layout = CanonLayout(
        id=Id(kind="layout.canon_layout_probe", value="3" * 32),
        key=("l",),
        owner=owner_id("1"),
        x=x,
    )
    return model_of(origin, owner, facet, layout)


def test_moving_a_layout_record_changes_only_the_layout_and_overall_digests(origin: Origin) -> None:
    """One namespace's change moves its digest and the model's, and no other namespace's."""
    before, after = _three_namespaces(origin, x=5), _three_namespaces(origin, x=64)
    assert before.digests["layout"] != after.digests["layout"]
    assert before.digests["core"] == after.digests["core"]
    assert before.digests["facet"] == after.digests["facet"]
    assert before.digest != after.digest


def test_changing_a_facet_record_changes_only_the_facet_and_overall_digests(origin: Origin) -> None:
    """The plant digests (`core`, `facet`) answer "did the plant change?" without layout."""
    before, after = _three_namespaces(origin), _three_namespaces(origin, subject_note="b")
    assert before.digests["facet"] != after.digests["facet"]
    assert before.digests["core"] == after.digests["core"]
    assert before.digests["layout"] == after.digests["layout"]
    assert before.digest != after.digest


def test_a_three_namespace_model_round_trips_with_every_digest(origin: Origin) -> None:
    """`digests` is recomputed on load: the reloaded model has all three and equals the original."""
    model = _three_namespaces(origin)
    assert set(model.digests) == {"core", "facet", "layout"}
    reloaded = loads(dumps(model))
    assert reloaded == model
    assert reloaded.digests == model.digests


def test_the_largest_int_and_the_extreme_decimals_survive_the_round_trip(origin: Origin) -> None:
    """The limits `check_value` sets are exactly what the text form can carry."""
    biggest = 2**2048 - 1
    model = model_of(
        origin,
        make_owner("1"),
        make_item("2", count=biggest, amount=Decimal("1E+1000")),
        make_item("3", count=-biggest, amount=Decimal("-1.5E-1000")),
    )
    reloaded = loads(dumps(model))
    assert reloaded == model
    assert reloaded.digest == model.digest


def test_a_field_derived_in_post_init_is_written_and_comes_back(origin: Origin) -> None:
    """`init=False` fields are in the text (every field is) and are derived again on load."""
    model = model_of(origin, CanonDerived(id=derived_id("5"), key=("5",), name="pump"))
    text = dumps(model)
    assert '"shout": "PUMP"' in text
    assert loads(text) == model


@pytest.mark.parametrize(
    "record",
    [
        make_owner("3", ext=frozendict({"m": frozendict({10**5000: 1})})),
        make_owner("3", ext=frozendict({"m": (frozendict({10**5000: 1}),)})),
        make_item("2", scores=frozendict({10**5000: 1})),
    ],
    ids=["ext-mapping", "ext-tuple-of-mapping", "declared-mapping"],
)
def test_freeze_refuses_a_huge_int_key_as_a_model_error(origin: Origin, record: Any) -> None:
    """The refusal of a key must not print it: `str(10**5000)` raises a stdlib `ValueError`."""
    with pytest.raises(FreezeError) as excinfo:
        model_of(origin, make_owner("1"), record)
    assert all(isinstance(error, ValueTypeError) for error in excinfo.value.errors)


def test_freeze_refuses_a_record_nested_too_deeply_to_check(origin: Origin) -> None:
    """`from_data` turns `RecursionError` into a `SchemaError`; `freeze` must do the same."""
    nested: Any = 1
    for _ in range(5000):
        nested = frozendict({"k": nested})
    with pytest.raises(FreezeError, match="1 error") as excinfo:
        model_of(origin, make_owner("1", ext=frozendict({"deep": nested})))
    (error,) = excinfo.value.errors
    assert isinstance(error, ValueTypeError)
    assert "nested too deeply" in str(error)
