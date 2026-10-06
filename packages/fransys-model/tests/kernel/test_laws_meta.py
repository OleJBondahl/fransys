"""What the strategies of `test_laws.py` reach, so no law passes vacuously (REVIEW-M M2)."""

from collections import Counter

from hypothesis import given, settings
from laws_checks import EvolveCase, MergeCase, evolve_cases, evolve_plan, merge_cases
from laws_pool import Pool, pools

from fransys_model.kernel import Id

_EXPECTED_KINDS = frozenset(
    [
        "part_library",
        "part",
        "function_template",
        "port_template",
        "internal_link",
        "facet.supply",
        "facet.connector",
        "unit_release",
        "unit",
        "item",
        "function",
        "port",
        "facet.terminal",
        "facet.scaling",
        "conductor",
        "net",
        "mate",
        "boundary",
        "unused_boundary",
    ]
)


def test_pools_reach_every_kind_and_shape() -> None:
    """Across the pool budget: 19 kinds, nested items and units, a `Decimal`, an alias, ext."""
    seen: set[str] = set()
    shapes: Counter[str] = Counter()

    @settings(max_examples=40)
    @given(pool=pools())
    def probe(pool: Pool) -> None:
        seen.update(record.id.kind for record in pool.records)
        for record in pool.records:
            kind = record.id.kind
            shapes["nested_item"] += kind == "item" and record.parent is not None
            shapes["nested_unit"] += kind == "unit" and record.parent is not None
            shapes["decimal"] += kind == "facet.scaling"
            shapes["ext_map"] += any(type(v) is frozendict for v in record.ext.values())
            shapes["ext_id"] += any(type(v) is Id for v in record.ext.values())
            shapes["negative_int"] += kind == "item" and (record.position or 0) < 0
            shapes["big_int"] += any(type(v) is int and abs(v) > 2**64 for v in record.ext.values())
            shapes["quote_or_backslash"] += (
                any(c in record.description for c in '"\\') if kind == "item" else False
            )
        shapes["alias"] += bool(pool.aliases)

    probe()
    assert seen == _EXPECTED_KINDS
    assert len(_EXPECTED_KINDS) == 19
    assert min(shapes.values()) > 0, shapes
    assert len(shapes) == 9


def test_cases_exercise_overlap_put_remove_replace_and_alias() -> None:
    """Merge operands overlap and are proper subsets; evolve puts, removes, replaces, aliases."""
    seen: Counter[str] = Counter()

    @settings(max_examples=40)
    @given(merge_case=merge_cases(), evolve_case=evolve_cases())
    def probe(merge_case: MergeCase, evolve_case: EvolveCase) -> None:
        ids = [{r.id for r in records} for records in merge_case.operands]
        total = len(merge_case.pool.records)
        seen["overlap"] += len(ids[0] & ids[1]) > 0
        seen["proper_subset"] += all(len(operand) < total for operand in ids)
        put, remove, replaced = evolve_plan(evolve_case.base, evolve_case.final)
        seen["added"] += bool({record.id for record in put} - set(remove))
        seen["dropped"] += bool(set(remove) - replaced)
        seen["replace"] += bool(replaced)
        seen["nonempty_base"] += bool(evolve_case.base)
        seen["alias"] += bool(evolve_case.aliases)

    probe()
    assert min(seen.values()) > 0, seen
    assert len(seen) == 7
