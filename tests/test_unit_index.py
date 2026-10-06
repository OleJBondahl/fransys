"""The per-unit index gives the answers the old full scans gave (decision model-0067).

Expected values are written out by key. The hand-built model carries keys of its own: the
index caches on the model digest.
"""

import dataclasses
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from fransys_model.kernel import Draft, Origin, SchemaError, freeze, make_id
from fransys_model.vocab import (
    CableFacet,
    CableProductFacet,
    Item,
    Part,
    PartCategory,
    PcbFacet,
    Unit,
    UnitRelease,
    membership,
)
from fransys_model.vocab.tables import functions, items
from fransys_model.vocab.tables import units as units_table
from fransys_model.vocab.unit_index import unit_index

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from scale_units_fixture import build_scale  # noqa: E402

_SCOPE = "uidx"


def _release(name):
    key = ("unit_release", name, "1", "1")
    return UnitRelease(
        id=make_id(UnitRelease, key), key=key, name=name, version=1, revision=1, interface="1"
    )


def _unit(name, parent=None):
    key = (_SCOPE, name)
    return Unit(
        id=make_id(Unit, key),
        key=key,
        release=_release(name).id,
        parent=None if parent is None else parent.id,
    )


def _part(name, category):
    key = (_SCOPE, "part", name)
    return Part(
        id=make_id(Part, key),
        key=key,
        mpn=name,
        manufacturer="none",
        description=name,
        category=category,
        class_code="X",
    )


def _item(name, *, unit=None, parent=None, part=None, external=False):
    key = (_SCOPE, "item", name)
    return Item(
        id=make_id(Item, key),
        key=key,
        part=None if part is None else part.id,
        parent=None if parent is None else parent.id,
        position=None,
        tag=None,
        description=name,
        unit=None if unit is None else unit.id,
        external=external,
    )


def _hand_built_model():
    """Three nested units, an external root and child, a cross-unit root, a board, a harness with
    a cable child, a unit `parent` cycle and two item `parent` cycles (one holding an external)."""
    top = _unit("top")
    mid = _unit("mid", top)
    deep = _unit("deep", mid)
    lone = _unit("lone")
    cycle_a = _unit("cycle-a")
    cycle_b = _unit("cycle-b", cycle_a)
    cycle_a = dataclasses.replace(cycle_a, parent=cycle_b.id)  # a's parent is b, b's is a
    board_part = _part("board", PartCategory.CONNECTOR)
    cable_part = _part("cable", PartCategory.CABLE)

    ext_root = _item("ext-root", unit=mid, external=True)
    ext_child = _item("ext-child", unit=mid, parent=ext_root)
    ext_grandchild = _item("ext-grandchild", unit=deep, parent=ext_child)
    free = _item("free")
    top_item = _item("top-item", unit=top)
    cross_root = _item("cross-root", unit=mid, parent=top_item)
    board = _item("board", unit=deep, part=board_part)
    board_child = _item("board-child", unit=deep, parent=board)
    harness = _item("harness", unit=mid)
    cable = _item("cable", unit=mid, parent=harness, part=cable_part)
    plain = _item("plain", unit=mid, parent=harness)
    lone_item = _item("lone-item", unit=lone)
    # a `parent` cycle of two, one of them a board; an item leading into it
    loop_p, loop_q = _item("loop-p", unit=cycle_a, part=board_part), _item("loop-q", unit=cycle_a)
    loop_p = dataclasses.replace(loop_p, parent=loop_q.id)
    loop_q = dataclasses.replace(loop_q, parent=loop_p.id)
    leads_in = _item("leads-in", unit=cycle_b, parent=loop_p)
    # a `parent` cycle holding an external item
    ring_s, ring_t = _item("ring-s", unit=lone), _item("ring-t", unit=lone, external=True)
    ring_s = dataclasses.replace(ring_s, parent=ring_t.id)
    ring_t = dataclasses.replace(ring_t, parent=ring_s.id)
    ring_in = _item("ring-in", unit=lone, parent=ring_s)

    def facet(kind, subject, **fields):
        key = (_SCOPE, "facet", subject.key[-1])
        return kind(id=make_id(kind, key), key=key, subject=subject.id, **fields)

    draft = Draft()
    draft.extend(
        (
            *(_release(u.key[1]) for u in (top, mid, deep, lone, cycle_a, cycle_b)),
            top,
            mid,
            deep,
            lone,
            cycle_a,
            cycle_b,
            board_part,
            cable_part,
            ext_root,
            ext_child,
            ext_grandchild,
            free,
            top_item,
            cross_root,
            board,
            board_child,
            harness,
            cable,
            plain,
            lone_item,
            loop_p,
            loop_q,
            leads_in,
            ring_s,
            ring_t,
            ring_in,
            facet(PcbFacet, board_part, revision="A"),
            facet(CableFacet, cable, length_mm=None),
            facet(
                CableProductFacet,
                cable_part,
                core_colours=(),
                gauge_mm2=Decimal("0.5"),
                shielded=False,
            ),
        ),
        origin=Origin(file="<unit index oracle>", line=1, note="model-0067"),
    )
    return freeze(draft)


def _names(table):
    """The ids of a records table by joined key (`"uidx/item/board"`), and back."""
    by_name = {"/".join(record.key): record.id for record in table.values()}
    return by_name, {id_: name for name, id_ in by_name.items()}


def _facts(model):
    """Every membership answer of `model`, per unit and per item, named by joined key."""
    unit_id, unit_name = _names(units_table(model))
    item_id, item_name = _names(items(model))

    def named(ids):
        return sorted(item_name[i] for i in ids)

    def by_unit(query):
        return {name: query(model, id_) for name, id_ in unit_id.items()}

    def by_item(query):
        return {name: query(model, id_) for name, id_ in item_id.items()}

    return {
        "subtree": {
            name: sorted(unit_name[u] for u in ids)
            for name, ids in by_unit(membership.unit_subtree).items()
        },
        "item_count": {name: len(ids) for name, ids in by_unit(membership.unit_items).items()},
        "items": {name: named(ids) for name, ids in by_unit(membership.unit_items).items()},
        "standalone": {name for name, yes in by_unit(membership.standalone).items() if yes},
        # in the items table's order, not sorted
        "roots": {
            name: [item_name[i] for i in ids]
            for name, ids in by_unit(membership.unit_own_roots).items()
        },
        "sole_root": {n for n, yes in by_item(membership.is_sole_unit_root).items() if yes},
        "external": {n for n, yes in by_item(membership.external).items() if yes},
        "cable_children": {
            name: named(ids) for name, ids in by_item(membership.cable_children).items() if ids
        },
        "harness": {n for n, yes in by_item(membership.is_harness).items() if yes},
        "boards": {
            name: [item_name[i] for i in ids]
            for name, ids in by_item(membership.enclosing_boards).items()
            if ids
        },
    }


# Every literal below is what the scan `vocab.membership` had before the index answered
# (checked with `claude-tools/run_unit_oracle.py`, which runs the old scan against the index).


def test_the_hand_built_model_answers_the_old_scan_per_unit():
    facts = _facts(_hand_built_model())
    assert facts["subtree"] == {
        "uidx/top": ["uidx/deep", "uidx/mid", "uidx/top"],
        "uidx/mid": ["uidx/deep", "uidx/mid"],
        "uidx/deep": ["uidx/deep"],
        "uidx/lone": ["uidx/lone"],
        # a unit `parent` cycle: each reaches the other
        "uidx/cycle-a": ["uidx/cycle-a", "uidx/cycle-b"],
        "uidx/cycle-b": ["uidx/cycle-a", "uidx/cycle-b"],
    }
    assert facts["item_count"] == {
        "uidx/top": 10,
        "uidx/mid": 9,
        "uidx/deep": 3,
        "uidx/lone": 4,
        "uidx/cycle-a": 3,
        "uidx/cycle-b": 3,
    }
    assert facts["items"]["uidx/deep"] == [
        "uidx/item/board",
        "uidx/item/board-child",
        "uidx/item/ext-grandchild",  # an item of `deep` under an external item of `mid`
    ]
    assert facts["items"]["uidx/lone"] == [
        "uidx/item/lone-item",
        "uidx/item/ring-in",
        "uidx/item/ring-s",
        "uidx/item/ring-t",
    ]
    # `free` has no unit, so no unit holds every item
    assert facts["standalone"] == set()
    assert facts["roots"] == {
        "uidx/top": ["uidx/item/top-item"],
        # `cross-root`'s parent belongs to `top`; `ext-root` and its descendants are external
        "uidx/mid": ["uidx/item/harness", "uidx/item/cross-root"],
        "uidx/deep": ["uidx/item/board"],
        "uidx/lone": ["uidx/item/lone-item"],
        # `loop-p` and `loop-q` are each other's parent in one unit: no root
        "uidx/cycle-a": [],
        "uidx/cycle-b": ["uidx/item/leads-in"],
    }


def test_the_hand_built_model_answers_the_old_scan_per_item():
    facts = _facts(_hand_built_model())
    assert facts["sole_root"] == {
        "uidx/item/board",
        "uidx/item/leads-in",
        "uidx/item/lone-item",
        "uidx/item/top-item",
    }
    assert facts["external"] == {
        "uidx/item/ext-root",
        "uidx/item/ext-child",
        "uidx/item/ext-grandchild",  # only an ancestor is flagged
        "uidx/item/ring-s",  # a `parent` cycle holding the flagged `ring-t`
        "uidx/item/ring-t",
        "uidx/item/ring-in",  # leads into that cycle
    }
    assert facts["cable_children"] == {"uidx/item/harness": ["uidx/item/cable"]}
    assert facts["harness"] == {"uidx/item/harness"}
    assert facts["boards"] == {
        "uidx/item/board": ["uidx/item/board"],
        "uidx/item/board-child": ["uidx/item/board"],
        # `loop-p` is a board in a `parent` cycle: the walk ends at the repeat
        "uidx/item/loop-p": ["uidx/item/loop-p"],
        "uidx/item/loop-q": ["uidx/item/loop-p"],
        "uidx/item/leads-in": ["uidx/item/loop-p"],
    }


def test_the_scale_model_answers_the_old_scan():
    facts = _facts(build_scale(2).model)
    units_named = ["unit", "pump1/unit", "pump1/io/unit", "pump2/unit", "pump2/io/unit"]
    assert facts["subtree"]["unit"] == sorted(units_named)  # the container covers 2N + 1 units
    assert facts["subtree"]["pump1/unit"] == ["pump1/io/unit", "pump1/unit"]
    assert facts["subtree"]["pump2/io/unit"] == ["pump2/io/unit"]
    assert facts["item_count"] == {
        "unit": 18,
        "pump1/unit": 9,
        "pump1/io/unit": 3,
        "pump2/unit": 9,
        "pump2/io/unit": 3,
    }
    # only the container holds every item
    assert facts["standalone"] == {"unit"}
    assert facts["roots"] == {
        "unit": [],
        "pump1/unit": ["pump1/X2", "pump1/w1"],
        "pump1/io/unit": ["pump1/io/board"],
        "pump2/unit": ["pump2/X2", "pump2/w1"],
        "pump2/io/unit": ["pump2/io/board"],
    }
    assert facts["sole_root"] == {"pump1/io/board", "pump2/io/board"}
    assert facts["external"] == set()
    assert facts["cable_children"] == {"pump1/w1": ["pump1/w1c"], "pump2/w1": ["pump2/w1c"]}
    assert facts["harness"] == {"pump1/w1", "pump2/w1"}
    assert facts["boards"]["pump1/io/k1"] == ["pump1/io/board"]
    assert facts["boards"]["pump2/io/X1"] == ["pump2/io/board"]
    assert len(facts["boards"]) == 6  # each board, its `X1` and its `k1`


def test_the_refusals_are_kept():
    model = _hand_built_model()
    unknown_unit = make_id(Unit, (_SCOPE, "nowhere"))
    unknown_item = make_id(Item, (_SCOPE, "item", "nowhere"))
    for query in (
        membership.unit_items,
        membership.unit_subtree,
        membership.standalone,
        membership.boundary,
    ):
        with pytest.raises(SchemaError):
            query(model, unknown_unit)
    for query in (membership.external, membership.is_sole_unit_root):
        with pytest.raises(SchemaError):
            query(model, unknown_item)
    assert membership.unit_own_roots(model, unknown_unit) == ()


def test_containing_lists_every_unit_whose_subtree_holds_a_unit():
    model = _hand_built_model()
    unit_id, unit_name = _names(units_table(model))
    containing = unit_index(model).containing
    assert {
        name: sorted(unit_name[u] for u in containing[id_]) for name, id_ in unit_id.items()
    } == {
        "uidx/top": ["uidx/top"],
        "uidx/mid": ["uidx/mid", "uidx/top"],
        "uidx/deep": ["uidx/deep", "uidx/mid", "uidx/top"],
        "uidx/lone": ["uidx/lone"],
        # a unit `parent` cycle: each is held by the other
        "uidx/cycle-a": ["uidx/cycle-a", "uidx/cycle-b"],
        "uidx/cycle-b": ["uidx/cycle-a", "uidx/cycle-b"],
    }
    # a unit the model does not hold is no key
    assert make_id(Unit, (_SCOPE, "nowhere")) not in containing


def test_boundary_of_lists_each_units_boundary_functions_once_in_id_order():
    model = build_scale(2).model
    unit_id, _unit_name = _names(units_table(model))
    function_names = {id_: "/".join(f.key) for id_, f in functions(model).items()}
    boundary_of = unit_index(model).boundary_of
    assert {
        name: sorted(function_names[f] for f in boundary_of[id_]) for name, id_ in unit_id.items()
    } == {
        "unit": [],
        "pump1/unit": ["pump1/X2/terminal/1/fn/terminal", "pump1/X2/terminal/2/fn/terminal"],
        "pump1/io/unit": ["pump1/io/X1/fn/x1"],
        "pump2/unit": ["pump2/X2/terminal/1/fn/terminal", "pump2/X2/terminal/2/fn/terminal"],
        "pump2/io/unit": ["pump2/io/X1/fn/x1"],
    }
    for id_ in unit_id.values():
        assert list(boundary_of[id_]) == sorted(boundary_of[id_])
        assert membership.boundary(model, id_) == boundary_of[id_]
    assert len(boundary_of) == len(unit_id)
