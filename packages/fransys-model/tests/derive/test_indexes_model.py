"""WP11 tests: what every index holds, on a model that uses each of them (design/derive.md)."""

import dataclasses
from typing import Any

import pytest
from examples import core_model, relay_part_bundle

from fransys_model.derive import Indexes, build_indexes
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, Origin, evolve, make_id
from fransys_model.layout.hints import GroupHint
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.connectivity import Conductor, Net
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import Aspect, ConductorKind, NetClass, SignalType
from fransys_model.vocab.facets import CableFacet, PlcRequestFacet, TerminalFacet

_ORIGIN = Origin(file="test_indexes_model.py", line=1, note="fixture")
_PART = relay_part_bundle().part.id

_K1 = make_id(Item, ("plant", "k1"))
_HOUSING = make_id(Item, ("plant", "housing"))
_BOARD = make_id(Item, ("plant", "board"))
_CHILD_1 = make_id(Item, ("plant", "housing", "child-1"))
_CHILD_2 = make_id(Item, ("plant", "housing", "child-2"))
_COIL = make_id(Function, ("plant", "k1", "fn", "coil"))
_HOUSING_J1 = make_id(Function, ("plant", "housing", "j1"))
_BOARD_J1 = make_id(Function, ("plant", "board", "j1"))
_A1 = make_id(Port, ("plant", "k1", "coil", "a1"))
_A2 = make_id(Port, ("plant", "k1", "coil", "a2"))
_PIN = make_id(Port, ("plant", "housing", "j1", "1"))
_W1 = make_id(Conductor, ("plant", "w1"))
_W2 = make_id(Conductor, ("plant", "w2"))
_NET_24V = make_id(Net, ("plant", "24v"))
_NET_SIGNAL = make_id(Net, ("plant", "signal"))
_C1 = make_id(AspectNode, ("plant", "c1"))
_C2 = make_id(AspectNode, ("plant", "c2"))
_P_K1_C1 = make_id(Placement, ("plant", "k1", "c1"))
_P_CHILD_C1 = make_id(Placement, ("plant", "child-2", "c1"))
_P_CHILD_C2 = make_id(Placement, ("plant", "child-2", "c2"))
_TERMINAL = make_id(TerminalFacet, ("plant", "housing", "terminal"))
_CABLE = make_id(CableFacet, ("plant", "housing", "cable"))
_REQUEST = make_id(PlcRequestFacet, ("plant", "k1", "request"))
_HINT = make_id(GroupHint, ("plant", "k1", "hint"))


def _child(key: str, part: Id[Any] | None) -> Item:
    return Item(
        id=make_id(Item, ("plant", "housing", key)),
        key=("plant", "housing", key),
        part=part,
        parent=_HOUSING,
        position=None,
        tag=None,
        description="Invented child",
    )


def _busy_model() -> Model:
    """The core model plus what its single-use records leave out: shared keys of every index."""
    records: list[Any] = [
        _child("child-1", None),
        _child("child-2", _PART),
        AspectNode(
            id=_C2,
            key=("plant", "c2"),
            aspect=Aspect.LOCATION,
            parent=_C1,
            label="C2",
            description="Invented sub-enclosure",
        ),
        Placement(id=_P_CHILD_C1, key=("plant", "child-2", "c1"), item=_CHILD_2, node=_C1),
        Placement(id=_P_CHILD_C2, key=("plant", "child-2", "c2"), item=_CHILD_2, node=_C2),
        Net(
            id=_NET_SIGNAL,
            key=("plant", "signal"),
            name="SIG",
            net_class=NetClass.SIGNAL,
            ports=(_A1, _PIN),
        ),
        Conductor(
            id=_W2,
            key=("plant", "w2"),
            a=_A2,
            b=_PIN,
            kind=ConductorKind.WIRE,
            carrier=None,
        ),
        TerminalFacet(
            id=_TERMINAL,
            key=("plant", "housing", "terminal"),
            subject=_HOUSING,
            group="L1",
            index=3,
        ),
        CableFacet(id=_CABLE, key=("plant", "housing", "cable"), subject=_HOUSING, length_mm=None),
        GroupHint(id=_HINT, key=("plant", "k1", "hint"), function=_COIL, group=_C1),
        PlcRequestFacet(
            id=_REQUEST,
            key=("plant", "k1", "request"),
            subject=_COIL,
            signal=SignalType.DI,
            signal_name="Run",
            priority=1,
        ),
    ]
    return evolve(core_model(), put=records, origin=_ORIGIN)


def _sorted(*ids: Id[Any]) -> tuple[Id[Any], ...]:
    return tuple(sorted(ids))


def test_every_index_holds_what_its_name_says() -> None:
    """One assertion per index, against ids written out by hand."""
    idx = build_indexes(_busy_model())
    assert dict(idx.functions_by_item) == {
        _K1: (_COIL,),
        _HOUSING: (_HOUSING_J1,),
        _BOARD: (_BOARD_J1,),
    }
    assert dict(idx.ports_by_function) == {_COIL: _sorted(_A1, _A2), _HOUSING_J1: (_PIN,)}
    assert dict(idx.conductors_by_port) == {
        _PIN: _sorted(_W1, _W2),
        _A1: (_W1,),
        _A2: (_W2,),
    }
    assert dict(idx.nets_by_port) == {
        _A1: _sorted(_NET_24V, _NET_SIGNAL),
        _A2: (_NET_24V,),
        _PIN: (_NET_SIGNAL,),
    }
    assert dict(idx.items_by_part) == {_PART: _sorted(_K1, _CHILD_2)}
    assert dict(idx.children_by_item) == {_HOUSING: _sorted(_CHILD_1, _CHILD_2)}
    assert dict(idx.facets_by_subject) == {
        _HOUSING: _sorted(_TERMINAL, _CABLE),
        _COIL: (_REQUEST,),
    }
    assert dict(idx.placements_by_item) == {
        _K1: (_P_K1_C1,),
        _CHILD_2: _sorted(_P_CHILD_C1, _P_CHILD_C2),
    }
    assert dict(idx.nodes_by_parent) == {_C1: (_C2,)}


def test_a_key_with_nothing_under_it_is_absent_not_empty() -> None:
    """Roots and childless items have no entry: `.get(key, ())` is the way to read one."""
    idx = build_indexes(_busy_model())
    assert _BOARD not in idx.children_by_item
    assert _K1 not in idx.children_by_item
    assert _BOARD_J1 not in idx.ports_by_function
    assert None not in idx.children_by_item
    assert None not in idx.items_by_part
    assert None not in idx.nodes_by_parent


def test_a_model_without_the_kinds_gives_empty_indexes() -> None:
    """Every index of an empty model is an empty mapping, not a missing table."""
    empty = evolve(
        core_model(),
        remove=tuple(
            record.id for table in core_model().tables.values() for record in table.values()
        ),
    )
    idx = build_indexes(empty)
    for field in dataclasses.fields(idx):
        assert getattr(idx, field.name) == {}


def test_every_index_is_sorted_and_names_only_records_of_the_model() -> None:
    """Keys and members are in id order (no order of a table leaks) and all exist."""
    model = _busy_model()
    idx = build_indexes(model)
    for field in dataclasses.fields(idx):
        table = getattr(idx, field.name)
        assert list(table) == sorted(table), field.name
        for key, members in table.items():
            assert key in model.tables[key.kind], field.name
            assert list(members) == sorted(members), field.name
            assert len(set(members)) == len(members), field.name
            for member in members:
                assert member in model.tables[member.kind], field.name


def test_the_indexes_are_frozendicts_of_tuples_of_ids_all_the_way_down() -> None:
    """Nothing reachable from an `Indexes` can be changed."""
    idx = build_indexes(_busy_model())
    for field in dataclasses.fields(idx):
        table = getattr(idx, field.name)
        assert type(table) is frozendict, field.name
        for key, members in table.items():
            assert type(key) is Id
            assert type(members) is tuple
            assert all(type(member) is Id for member in members)


def test_terminal_cable_and_plc_request_facets_are_found_through_their_subject() -> None:
    """Three facet kinds, three kinds of subject (an item, a function): all are found."""
    idx = build_indexes(_busy_model())
    kinds = {facet.kind for members in idx.facets_by_subject.values() for facet in members}
    assert kinds == {"facet.terminal", "facet.cable", "facet.plc_request"}


def test_records_of_other_namespaces_are_not_facets() -> None:
    """A layout hint declares a `subject` too, but only the `facet` namespace is indexed."""
    idx = build_indexes(_busy_model())
    members = {member for group in idx.facets_by_subject.values() for member in group}
    assert not {_P_K1_C1, _NET_24V, _W1, _HINT} & members
    assert _COIL in idx.facets_by_subject
    assert idx.facets_by_subject[_COIL] == (_REQUEST,)


def test_equal_content_gives_equal_indexes_and_a_change_gives_different_ones() -> None:
    """Adding an item changes `children_by_item`, and the indexes it does not touch stay equal."""
    before = build_indexes(_busy_model())
    extra = _child("child-3", None)
    after_model = evolve(_busy_model(), put=(extra,), origin=_ORIGIN)
    after = build_indexes(after_model)
    assert after.children_by_item[_HOUSING] == _sorted(_CHILD_1, _CHILD_2, extra.id)
    assert after.functions_by_item == before.functions_by_item
    assert after != before
    assert build_indexes(_busy_model()) == before


def test_the_cache_returns_one_object_per_digest_whatever_the_origins() -> None:
    """Origins are not content: the same records from other lines share one `Indexes`."""
    first = _busy_model()
    other_origin = Origin(file="elsewhere.py", line=99, note="moved")
    second = evolve(core_model(), put=_put_records(first), origin=other_origin)
    assert first.digest == second.digest
    assert first.origins != second.origins
    assert build_indexes(first) is build_indexes(second)


def _put_records(model: Model) -> list[Any]:
    """The records `_busy_model` added to the core model."""
    core = core_model()
    return [
        record
        for kind, table in model.tables.items()
        for record in table.values()
        if record.id not in core.tables.get(kind, {})
    ]


def test_different_content_is_a_different_indexes_object() -> None:
    """The cache is keyed by content: two digests never share a result."""
    assert build_indexes(_busy_model()) is not build_indexes(core_model())


def _distinct_model(number: int) -> Model:
    return evolve(
        core_model(),
        put=(
            Item(
                id=make_id(Item, ("cache", str(number))),
                key=("cache", str(number)),
                part=None,
                parent=None,
                position=None,
                tag=None,
                description="Invented",
            ),
        ),
        origin=_ORIGIN,
    )


def test_the_cache_is_bounded_and_an_evicted_result_is_rebuilt_equal() -> None:
    """A long-running Fransys session does not keep every model it ever indexed."""
    models = [_distinct_model(n) for n in range(DIGEST_CACHE_SIZE + 1)]
    first_result = build_indexes(models[0])
    for model in models[1:]:
        build_indexes(model)
    again = build_indexes(models[0])
    assert again is not first_result
    assert again == first_result


def test_the_most_recently_used_result_survives_a_full_cache() -> None:
    """Least recently used goes first: a result asked for again stays."""
    models = [_distinct_model(100 + n) for n in range(DIGEST_CACHE_SIZE + 1)]
    kept = build_indexes(models[0])
    for model in models[1:DIGEST_CACHE_SIZE]:
        build_indexes(model)
    assert build_indexes(models[0]) is kept
    build_indexes(models[DIGEST_CACHE_SIZE])
    assert build_indexes(models[0]) is kept


def test_indexes_is_a_frozen_keyword_only_dataclass() -> None:
    """No positional construction, no assignment (decision 0012)."""
    idx = build_indexes(core_model())
    positional: Any = Indexes
    with pytest.raises(TypeError):
        positional(*([frozendict()] * 9))
    assert dataclasses.is_dataclass(idx)


def test_the_indexes_do_not_depend_on_the_order_of_a_models_tables() -> None:
    """Tables in another order (they are sets), under another digest so the cache is not used."""
    model = _busy_model()
    backwards = dataclasses.replace(
        model,
        digest="reversed-tables-test-indexes-model",  # unique: the caches key on digest
        tables=frozendict(
            {
                kind: frozendict(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )
    assert list(backwards.tables) != list(model.tables)
    assert build_indexes(backwards) == build_indexes(model)
