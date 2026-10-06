"""WP7 tests: `kernel.evolve` (ROADMAP WP7, design/kernel-model.md 5.7)."""

import dataclasses
import importlib
import types
from typing import TYPE_CHECKING, Any

import pytest
from freeze_probes import (
    Holds,
    Owner,
    Single,
    draft_of,
    holder_id,
    make_facet,
    make_holder,
    make_owner,
    owner_id,
)

from fransys_model.kernel import (
    AuthoringKey,
    Draft,
    FreezeError,
    Id,
    MergeConflict,
    Model,
    Origin,
    RefError,
    SchemaError,
    Value,
    ValueTypeError,
    evolve,
    freeze,
    record,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_BASE = Origin(file="base.py", line=1, note="")
_CALL = Origin(file="pass.py", line=9, note="numbering")


def _model(*records: Any) -> Model:
    return freeze(draft_of(_BASE, *records))


def _base() -> Model:
    """Owners 1, 2 and 3, a holder of owner 1, and a facet of owner 1."""
    return _model(
        make_owner("1"), make_owner("2"), make_owner("3"), make_holder("5"), make_facet("7", "1")
    )


def test_evolve_revalidates_removing_referenced_record_fails(
    thing_cls: type, link_cls: type, origin: Origin
) -> None:
    """Removing a `Thing` a `Link` still references is caught, not silently left dangling."""
    thing_id = Id(kind="thing", value="1" * 32)
    link_id = Id(kind="link", value="1" * 32)
    draft = Draft()
    draft.add(thing_cls(id=thing_id, key=("a",), name="pump"), origin=origin)
    draft.add(link_cls(id=link_id, key=("l",), a=thing_id, b=thing_id), origin=origin)
    model = freeze(draft)
    with pytest.raises(RefError):
        evolve(model, remove=(thing_id,))


def test_evolve_leaves_untouched_tables_identical_by_is(
    thing_cls: type, link_cls: type, origin: Origin
) -> None:
    """A table `evolve` doesn't touch is the same object, by `is`, before and after."""
    thing_id = Id(kind="thing", value="1" * 32)
    draft = Draft()
    draft.add(thing_cls(id=thing_id, key=("a",), name="pump"), origin=origin)
    model = freeze(draft)
    extra = link_cls(id=Id(kind="link", value="1" * 32), key=("l",), a=thing_id, b=thing_id)
    updated = evolve(model, put=(extra,), origin=origin)
    assert updated.tables["thing"] is model.tables["thing"]


def _put_owner() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    return (make_owner("4"),), ()


def _put_facet_of_another_owner() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    return (make_facet("8", "2"),), ()


def _remove_holder() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    return (), (holder_id("5"),)


def _remove_unreferenced_owner() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    return (), (owner_id("3"),)


def _replace_an_owner() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    return (make_owner("2", ext=frozendict({"note": "changed"})),), (owner_id("2"),)


def _retarget_the_holder() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    return (make_holder("5", owner=owner_id("2")),), (holder_id("5"),)


def _empty_a_table() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    return (), (Id(kind="freeze_unique_probe", value="7" * 32),)


def _swap_a_holder() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    return (make_holder("6", owner=owner_id("3")),), (holder_id("5"),)


def _remove_a_record_and_what_holds_it() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    return (), (owner_id("1"), holder_id("5"), Id(kind="freeze_unique_probe", value="7" * 32))


@pytest.mark.parametrize(
    "scenario",
    [
        _put_owner,
        _put_facet_of_another_owner,
        _remove_holder,
        _remove_unreferenced_owner,
        _replace_an_owner,
        _retarget_the_holder,
        _empty_a_table,
        _swap_a_holder,
        _remove_a_record_and_what_holds_it,
    ],
)
def test_evolve_gives_the_model_that_freezing_the_whole_result_gives(
    scenario: Callable[[], tuple[tuple[Any, ...], tuple[Any, ...]]],
) -> None:
    """The incremental result equals a full `freeze` of the same records."""
    base = _base()
    put, remove = scenario()
    gone = set(remove)
    kept = [
        record
        for table in base.tables.values()
        for record in table.values()
        if record.id not in gone
    ]
    expected = _model(*kept, *put)
    evolved = evolve(base, put=put, remove=remove, origin=_CALL)
    assert evolved == expected
    assert dict(evolved.tables) == dict(expected.tables)
    assert evolved.digest == expected.digest
    assert dict(evolved.digests) == dict(expected.digests)


def test_evolve_attributes_put_records_to_the_origin_of_the_call() -> None:
    """Untouched records keep their origin, put ones take the call's, removed ones lose theirs."""
    base = _base()
    evolved = evolve(base, put=(make_owner("4"),), remove=(owner_id("3"),), origin=_CALL)
    assert evolved.origin_of(owner_id("4")) == _CALL
    assert evolved.origin_of(owner_id("1")) == _BASE
    assert evolved.origin_of(owner_id("3")) is None
    assert set(evolved.origins) == set(evolved.hashes)


def test_evolve_of_nothing_returns_the_model_itself() -> None:
    """No change is no new model."""
    base = _base()
    assert evolve(base) is base
    assert evolve(base, put=(), remove=(), origin=_CALL) is base


def test_evolve_of_an_identical_put_is_a_no_op_that_keeps_the_models_record_and_origin() -> None:
    """Saying what the model already says changes nothing, not even the origin."""
    base = _base()
    same = make_owner("1")
    assert same is not base.tables["freeze_owner_probe"][owner_id("1")]
    evolved = evolve(base, put=(same,), origin=_CALL)
    assert evolved is base
    assert evolved.origin_of(owner_id("1")) == _BASE


def test_evolve_refuses_a_put_over_a_record_with_different_content() -> None:
    """Nothing is overwritten silently: the conflict names the model's origin and the call's."""
    with pytest.raises(MergeConflict) as excinfo:
        evolve(_base(), put=(make_owner("1", ext=frozendict({"a": 1})),), origin=_CALL)
    assert excinfo.value.record_id == owner_id("1")
    assert (excinfo.value.origin_a, excinfo.value.origin_b) == (_BASE, _CALL)


def test_evolve_replaces_a_record_when_it_is_named_in_remove_as_well() -> None:
    """The explicit way to change a record: `remove` is applied first, then `put`."""
    changed = make_owner("2", ext=frozendict({"a": 1}))
    evolved = evolve(_base(), put=(changed,), remove=(owner_id("2"),), origin=_CALL)
    assert evolved.tables["freeze_owner_probe"][owner_id("2")] is changed
    assert evolved.origin_of(owner_id("2")) == _CALL


def test_evolve_needs_an_origin_when_it_is_given_records() -> None:
    """Origins are how an error finds its way back to the author, so none is invented."""
    with pytest.raises(SchemaError, match="origin") as excinfo:
        evolve(_base(), put=(make_owner("4"),))
    assert excinfo.value.kind == "freeze_owner_probe"


def test_evolve_asks_for_an_origin_even_when_every_put_is_a_no_op() -> None:
    """The rule is about the call, not about what the model happens to contain."""
    with pytest.raises(SchemaError, match="origin"):
        evolve(_base(), put=(make_owner("1"),))


def test_evolve_names_the_same_kind_whatever_order_the_puts_come_in() -> None:
    """The kind in the missing-origin error is the first in `Id` order, not the first given."""
    a, b = make_owner("4"), make_facet("8", "1")
    for put in ((a, b), (b, a)):
        with pytest.raises(SchemaError) as excinfo:
            evolve(_base(), put=put)
        assert excinfo.value.kind == "freeze_owner_probe"


def test_evolve_refuses_to_remove_what_the_model_does_not_hold() -> None:
    """A remove that removes nothing is a mistake to report, and there is no holder to blame."""
    ghost = owner_id("9")
    with pytest.raises(SchemaError) as excinfo:
        evolve(_base(), remove=(ghost,))
    assert excinfo.value.record_id == ghost
    assert excinfo.value.kind == "freeze_owner_probe"


def test_evolve_names_the_smallest_id_of_several_that_do_not_exist() -> None:
    """Whichever ghost a set would yield first, the smallest is the one named."""
    ghosts = [Id(kind="freeze_owner_probe", value=f"{n:032x}") for n in range(100, 160)]
    for remove in (ghosts, ghosts[::-1]):
        with pytest.raises(SchemaError) as excinfo:
            evolve(_base(), remove=remove)
        assert excinfo.value.record_id == min(ghosts)


def test_evolve_takes_a_repeated_id_in_remove_once() -> None:
    """Saying it twice is saying it once, as for `Draft.alias`."""
    evolved = evolve(_base(), remove=(owner_id("3"), owner_id("3")))
    assert owner_id("3") not in evolved.hashes


def test_evolve_reports_a_reference_to_a_record_that_is_removed() -> None:
    """The holder, the field and the missing target are named."""
    with pytest.raises(RefError) as excinfo:
        evolve(_base(), remove=(owner_id("1"),))
    error = excinfo.value
    assert error.target == owner_id("1")
    assert error.record_id in {holder_id("5"), Id(kind="freeze_unique_probe", value="7" * 32)}


def test_evolve_raises_the_first_problem_in_freezes_order() -> None:
    """A holder with several dangling fields: the one `freeze` lists first is the one raised."""
    with pytest.raises(RefError) as excinfo:
        evolve(_base(), remove=(owner_id("1"),))
    error = excinfo.value
    assert (error.record_id, error.field, error.target) == (holder_id("5"), "many.0", owner_id("1"))
    survivors = (make_owner("2"), make_owner("3"), make_holder("5"), make_facet("7", "1"))
    with pytest.raises(FreezeError) as frozen:
        freeze(draft_of(_BASE, *survivors))
    first = frozen.value.errors[0]
    assert isinstance(first, RefError)
    assert (first.record_id, first.field, first.target) == (
        error.record_id,
        error.field,
        error.target,
    )


def test_evolve_lets_a_holder_and_what_it_holds_go_together() -> None:
    """Removing both sides of a reference is not a dangling reference."""
    evolved = evolve(
        _base(),
        remove=(owner_id("1"), holder_id("5"), Id(kind="freeze_unique_probe", value="7" * 32)),
    )
    assert owner_id("1") not in evolved.hashes


def test_evolve_refuses_a_put_that_refers_to_a_record_removed_in_the_same_call() -> None:
    """References are checked against the ids the model has after the call."""
    with pytest.raises(RefError) as excinfo:
        evolve(
            _base(),
            put=(make_holder("6", owner=owner_id("3")),),
            remove=(owner_id("3"),),
            origin=_CALL,
        )
    assert excinfo.value.target == owner_id("3")
    assert excinfo.value.record_id == holder_id("6")


def test_evolve_accepts_a_put_that_refers_to_a_record_put_in_the_same_call() -> None:
    """The final set of ids is what counts, not the order the records are listed in."""
    holder = make_holder("6", owner=owner_id("4"), nested=Holds(owner=owner_id("4")), many=())
    evolved = evolve(_base(), put=(holder, make_owner("4")), origin=_CALL)
    assert holder_id("6") in evolved.hashes


def test_evolve_refuses_a_put_that_refers_to_nothing() -> None:
    """A dangling reference in a new record is reported with its holder."""
    with pytest.raises(RefError) as excinfo:
        evolve(_base(), put=(make_holder("6", owner=owner_id("9")),), origin=_CALL)
    assert (excinfo.value.record_id, excinfo.value.target) == (holder_id("6"), owner_id("9"))


def test_evolve_refuses_a_reference_to_a_record_of_the_wrong_kind() -> None:
    """The field declares an owner; a holder's id is not one."""
    with pytest.raises(RefError, match="another kind"):
        evolve(_base(), put=(make_holder("6", owner=holder_id("5")),), origin=_CALL)


def test_evolve_refuses_a_put_that_is_not_a_record() -> None:
    """The same guard `Draft.add` has, because `evolve` does not go through it."""
    not_a_record: Any = Holds(owner=owner_id("1"))
    with pytest.raises(SchemaError, match="@record instance"):
        evolve(_base(), put=(not_a_record,), origin=_CALL)


def test_evolve_refuses_a_record_whose_id_is_of_another_kind() -> None:
    """A record filed under the wrong kind would corrupt the tables."""
    liar = Owner(id=holder_id("6"), key=("6",))
    with pytest.raises(SchemaError, match="@record instance"):
        evolve(_base(), put=(liar,), origin=_CALL)


def test_evolve_refuses_two_different_records_under_one_id_in_one_put() -> None:
    """There is only one origin to name, so this is not a `MergeConflict`."""
    first, second = make_owner("4"), make_owner("4", ext=frozendict({"a": 1}))
    with pytest.raises(SchemaError, match="one id") as excinfo:
        evolve(_base(), put=(first, second), origin=_CALL)
    assert excinfo.value.kind == "freeze_owner_probe"
    assert excinfo.value.record_id == owner_id("4")


def test_evolve_takes_the_same_record_twice_in_one_put_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Identical repeats are a no-op, as in a `Draft`: the record is hashed once."""
    module = importlib.import_module("fransys_model.kernel.evolve")
    seen: list[Any] = []
    real = module.record_hash

    def counting(record: Any) -> str:
        seen.append(record.id)
        return real(record)

    monkeypatch.setattr(module, "record_hash", counting)
    evolved = evolve(_base(), put=(make_owner("4"), make_owner("4")), origin=_CALL)
    assert owner_id("4") in evolved.hashes
    assert seen == [owner_id("4")]


def test_evolve_checks_the_fields_of_a_put_record() -> None:
    """A wrong type is a `SchemaError` and a float is a `ValueTypeError`, as in `freeze`."""
    bad_key: Any = "not a tuple"
    with pytest.raises(SchemaError):
        evolve(_base(), put=(Owner(id=owner_id("4"), key=bad_key),), origin=_CALL)
    with pytest.raises(ValueTypeError):
        evolve(_base(), put=(make_owner("4", ext=frozendict({"x": 1.5})),), origin=_CALL)


def test_evolve_raises_the_earliest_stage_first_whatever_order_the_puts_come_in() -> None:
    """A field problem outranks a reference problem, so which one escapes is not luck."""
    bad_value = make_owner("4", ext=frozendict({"x": 1.5}))
    dangling = make_holder("6", owner=owner_id("9"))
    for put in ((bad_value, dangling), (dangling, bad_value)):
        with pytest.raises(ValueTypeError):
            evolve(_base(), put=put, origin=_CALL)


def test_evolve_enforces_unique_against_the_whole_table() -> None:
    """A second facet for a subject is a clash with a record `put` did not mention."""
    with pytest.raises(SchemaError, match="per subject") as excinfo:
        evolve(_base(), put=(make_facet("8", "1"),), origin=_CALL)
    assert excinfo.value.kind == "freeze_unique_probe"


def test_evolve_lets_a_facet_move_to_a_subject_that_has_none() -> None:
    """Replace the facet of owner 1 by one of owner 2: unique still holds."""
    evolved = evolve(
        _base(),
        put=(make_facet("7", "2"),),
        remove=(Id(kind="freeze_unique_probe", value="7" * 32),),
        origin=_CALL,
    )
    moved: Any = next(iter(evolved.tables["freeze_unique_probe"].values()))
    assert len(evolved.tables["freeze_unique_probe"]) == 1
    assert moved.subject == owner_id("2")


def test_evolve_enforces_singleton_over_the_table_and_the_puts() -> None:
    """One is fine, a second is not, and a second is not fine because of a record already there."""
    one = Single(id=Id(kind="freeze_single_probe", value="9" * 32), key=("9",))
    two = Single(id=Id(kind="freeze_single_probe", value="8" * 32), key=("8",))
    with pytest.raises(SchemaError, match="at most one record of this kind"):
        evolve(_base(), put=(one, two), origin=_CALL)
    held = evolve(_base(), put=(one,), origin=_CALL)
    with pytest.raises(SchemaError, match="at most one record of this kind"):
        evolve(held, put=(two,), origin=_CALL)


def test_evolve_shares_every_table_it_does_not_touch() -> None:
    """Untouched tables are the model's own objects; the touched one is a new object."""
    base = _base()
    evolved = evolve(base, put=(make_owner("4"),), origin=_CALL)
    assert evolved.tables["freeze_holder_probe"] is base.tables["freeze_holder_probe"]
    assert evolved.tables["freeze_unique_probe"] is base.tables["freeze_unique_probe"]
    assert evolved.tables["freeze_owner_probe"] is not base.tables["freeze_owner_probe"]
    assert set(base.tables["freeze_owner_probe"]) == {owner_id("1"), owner_id("2"), owner_id("3")}


def test_evolve_leaves_the_model_it_was_given_alone() -> None:
    """A pure function: the argument is unchanged afterwards."""
    base = _base()
    before = (base.digest, dict(base.hashes), dict(base.origins), set(base.tables))
    evolve(base, put=(make_owner("4"),), remove=(owner_id("3"),), origin=_CALL)
    assert (base.digest, dict(base.hashes), dict(base.origins), set(base.tables)) == before


def test_evolve_hashes_only_the_records_it_puts(monkeypatch: pytest.MonkeyPatch) -> None:
    """The point of an incremental edit: untouched hashes are copied, not computed again."""
    module = importlib.import_module("fransys_model.kernel.evolve")
    seen: list[Any] = []
    real = module.record_hash

    def counting(record: Any) -> str:
        seen.append(record.id)
        return real(record)

    monkeypatch.setattr(module, "record_hash", counting)
    evolve(_base(), put=(make_owner("4"), make_owner("6")), remove=(owner_id("3"),), origin=_CALL)
    assert sorted(seen) == [owner_id("4"), owner_id("6")]


def test_evolve_takes_any_iterable() -> None:
    """A pass may hand over a generator."""
    evolved = evolve(
        _base(),
        put=(make_owner(digit) for digit in "45"),
        remove=iter([owner_id("3")]),
        origin=_CALL,
    )
    assert {owner_id("4"), owner_id("5")} <= set(evolved.hashes)
    assert owner_id("3") not in evolved.hashes


def _aliased() -> Model:
    """Owners 1 and 2 and holder 5, with owner 8 retired in favour of owner 1."""
    draft = draft_of(_BASE, make_owner("1"), make_owner("2"), make_holder("5"))
    draft.alias(owner_id("8"), owner_id("1"))
    return freeze(draft)


def test_evolve_keeps_the_aliases_of_the_model() -> None:
    """It never rewrites and never changes them."""
    base = _aliased()
    assert evolve(base, put=(make_owner("4"),), origin=_CALL).aliases == base.aliases


def test_evolve_refuses_to_remove_the_record_an_alias_leads_to() -> None:
    """The alias would lead nowhere: a `RefError` on the alias, as `freeze` says it."""
    with pytest.raises(RefError, match="names no record") as excinfo:
        evolve(_aliased(), remove=(owner_id("1"), holder_id("5")))
    assert excinfo.value.field == "<alias>"
    assert excinfo.value.record_id == owner_id("8")


def test_evolve_refuses_a_record_whose_id_is_a_retired_id() -> None:
    """A retired id must not have a record of its own again."""
    with pytest.raises(RefError, match="retired id") as excinfo:
        evolve(_aliased(), put=(make_owner("8"),), origin=_CALL)
    assert excinfo.value.field == "<alias>"
    assert excinfo.value.record_id == owner_id("8")


def test_evolve_treats_a_retired_id_used_as_a_reference_as_any_dangling_id() -> None:
    """No rewriting: a put record that still says the old id points at nothing."""
    with pytest.raises(RefError, match="names no record") as excinfo:
        evolve(_aliased(), put=(make_holder("6", owner=owner_id("8")),), origin=_CALL)
    assert excinfo.value.target == owner_id("8")


def test_evolve_of_a_record_nested_too_deeply_raises_one_value_type_error() -> None:
    """As `freeze` does, but not wrapped in a `FreezeError`: `evolve` raises single problems."""
    nested: Any = 1
    for _ in range(5000):
        nested = frozendict({"k": nested})
    with pytest.raises(ValueTypeError, match="nested too deeply") as excinfo:
        evolve(_base(), put=(make_owner("4", ext=frozendict({"deep": nested})),), origin=_CALL)
    assert not isinstance(excinfo.value, FreezeError)
    assert excinfo.value.path == ()


def test_evolve_names_the_same_unique_offender_freeze_names() -> None:
    """The final table is in `Id` order, so the record reported is the one `freeze` reports."""
    with pytest.raises(SchemaError, match="per subject") as excinfo:
        evolve(_base(), put=(make_facet("6", "1"),), origin=_CALL)
    kept = (make_owner("1"), make_owner("2"), make_owner("3"), make_holder("5"))
    with pytest.raises(FreezeError) as frozen:
        freeze(draft_of(_BASE, *kept, make_facet("6", "1"), make_facet("7", "1")))
    first: Any = frozen.value.errors[0]
    assert excinfo.value.record_id == first.record_id
    assert excinfo.value.record_id == Id(kind="freeze_unique_probe", value="7" * 32)


def test_evolve_reports_a_kind_whose_annotations_cannot_be_resolved() -> None:
    """A class-level problem is a `SchemaError` from the put record's kind, as in `freeze`."""

    def body(namespace: dict[str, Any]) -> None:
        generic: Any = Id
        namespace["__annotations__"] = {
            "id": generic["EvolveGhostProbe"],
            "key": AuthoringKey,
            "ext": frozendict[str, Value],
            "ghost": generic["NoSuchRecordEither"],
        }
        namespace["ext"] = frozendict()

    ghost = record(kind="evolve_ghost_probe")(
        types.new_class("EvolveGhostProbe", (), exec_body=body)
    )
    made = ghost(id=Id(kind="evolve_ghost_probe", value="1" * 32), key=("g",), ghost=owner_id("1"))
    with pytest.raises(SchemaError, match="is not a registered record"):
        evolve(_base(), put=(made,), origin=_CALL)


def test_evolve_does_not_walk_the_model_when_nothing_disappears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only a removed record can leave a reference behind; a replaced one is still there."""
    module = importlib.import_module("fransys_model.kernel.evolve")
    walked: list[Any] = []
    real = module.check_record

    def counting(found: Any) -> Any:
        walked.append(found.id)
        return real(found)

    monkeypatch.setattr(module, "check_record", counting)
    evolve(_base(), put=(make_owner("4"),), origin=_CALL)
    replaced = make_owner("2", ext=frozendict({"a": 1}))
    evolve(_base(), put=(replaced,), remove=(owner_id("2"),), origin=_CALL)
    assert walked == []
    evolve(_base(), remove=(owner_id("3"),))
    staying = {
        owner_id("1"),
        owner_id("2"),
        holder_id("5"),
        Id(kind="freeze_unique_probe", value="7" * 32),
    }
    assert sorted(walked) == sorted(staying)


def test_evolve_orders_its_tables_as_freeze_does() -> None:
    """A kind that is new to the model does not go last: the table order is the sorted one."""
    evolved = evolve(_base(), put=(make_owner("4"),), remove=(holder_id("5"),), origin=_CALL)
    expected = _model(
        make_owner("1"), make_owner("2"), make_owner("3"), make_owner("4"), make_facet("7", "1")
    )
    assert list(evolved.tables) == list(expected.tables)
    assert list(evolved.tables) == sorted(evolved.tables)


@pytest.mark.parametrize(
    "remove",
    ["abc", None, 5, ("abc",), (None,), (5, owner_id("1")), owner_id("1")],
    ids=["str", "none", "int", "str-item", "none-item", "mixed", "one-id"],
)
def test_evolve_refuses_a_remove_that_is_not_an_iterable_of_ids(remove: Any) -> None:
    """A caller's mistake is a `SchemaError`, not an `AttributeError` or a `TypeError`."""
    with pytest.raises(SchemaError, match="remove takes") as excinfo:
        evolve(_base(), remove=remove)
    assert excinfo.value.kind == "evolve"


def test_evolve_refuses_a_put_that_is_not_an_iterable_of_records() -> None:
    """Forgetting the tuple around a single record is a mistake to name."""
    with pytest.raises(SchemaError, match="put takes an iterable") as excinfo:
        evolve(_base(), put=make_owner("4"), origin=_CALL)
    assert excinfo.value.kind == "evolve"


def test_evolve_refuses_a_conflict_with_a_record_that_has_no_origin() -> None:
    """A model that cannot say where a record came from cannot name it in a conflict."""
    gap = dataclasses.replace(_base(), origins=frozendict())
    with pytest.raises(SchemaError, match="no origin") as excinfo:
        evolve(gap, put=(make_owner("1", ext=frozendict({"a": 1})),), origin=_CALL)
    assert excinfo.value.record_id == owner_id("1")


def test_evolve_checks_its_arguments_in_a_fixed_order() -> None:
    """Malformed records, then a missing origin, then an unknown remove, then a conflict."""
    ghost, other = owner_id("9"), make_owner("1", ext=frozendict({"a": 1}))
    junk: Any = Holds(owner=owner_id("1"))
    with pytest.raises(SchemaError, match="@record instance"):
        evolve(_base(), put=(junk,), remove=(ghost,))
    with pytest.raises(SchemaError, match="needs an origin"):
        evolve(_base(), put=(other,), remove=(ghost,))
    with pytest.raises(SchemaError, match="no record with this id") as excinfo:
        evolve(_base(), put=(other,), remove=(ghost,), origin=_CALL)
    assert excinfo.value.record_id == ghost
    with pytest.raises(MergeConflict):
        evolve(_base(), put=(other,), origin=_CALL)


class _Zebra:
    """Not a record, and named to sort after `_Apple`."""


class _Apple:
    """Not a record either."""


def test_evolve_names_the_same_malformed_put_whatever_order_they_come_in() -> None:
    """Two entries that are not records: the class that sorts first is the one named."""
    zebra, apple = _Zebra(), _Apple()
    for put in ((zebra, apple), (apple, zebra)):
        bad: Any = put
        with pytest.raises(SchemaError, match="_Apple") as excinfo:
            evolve(_base(), put=bad, origin=_CALL)
        assert excinfo.value.kind.endswith("_Apple")


def test_evolve_names_the_same_malformed_remove_whatever_order_they_come_in() -> None:
    """Two things that are not ids: the type name that sorts first is the one named."""
    for remove in ((5, "abc"), ("abc", 5)):
        bad: Any = remove
        with pytest.raises(SchemaError, match="not a int") as excinfo:
            evolve(_base(), remove=bad)
        assert excinfo.value.kind == "evolve"


def test_evolve_lets_a_type_error_inside_the_callers_iterator_through() -> None:
    """The caller's own bug arrives as itself, not as "not an iterable"."""

    def broken() -> Any:
        yield make_owner("4")
        msg = "the caller's own bug"
        raise TypeError(msg)

    with pytest.raises(TypeError, match="the caller's own bug"):
        evolve(_base(), put=broken(), origin=_CALL)
    with pytest.raises(TypeError, match="the caller's own bug"):
        evolve(_base(), remove=broken())


@pytest.mark.parametrize("origin", ["nowhere", ("a.py", 1, ""), 3, None])
def test_evolve_needs_a_real_origin_not_just_something(origin: Any) -> None:
    """A stray value stored in `Model.origins` would break `merge` and `describe` later."""
    with pytest.raises(SchemaError, match="needs an origin"):
        evolve(_base(), put=(make_owner("4"),), origin=origin)


def test_evolve_refuses_a_conflict_with_a_record_whose_origin_is_not_an_origin() -> None:
    """A model holding something that is not an `Origin` cannot name it either."""
    gap = dataclasses.replace(_base(), origins=frozendict({owner_id("1"): "nowhere"}))
    with pytest.raises(SchemaError, match="no origin") as excinfo:
        evolve(gap, put=(make_owner("1", ext=frozendict({"a": 1})),), origin=_CALL)
    assert excinfo.value.record_id == owner_id("1")
