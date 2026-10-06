"""Structural guard of decision model-0067: each per-unit index is built once per model.

However many lookups a build, a document or a list makes, the vocab layer's `UnitIndex` and
derive's `UnitNodes` are each built once for the one model digest. The guard counts builder
calls (never wall-clock) on the scale fixture, after clearing the caches so an earlier test's
result cannot hide a rebuild.
"""

import sys
from pathlib import Path

from fransys_model.derive import item_designation, reference_designation
from fransys_model.derive import unit_nodes as unit_nodes_module
from fransys_model.derive.designation import own_nodes
from fransys_model.derive.drawing_text import page_title
from fransys_model.layout import Page
from fransys_model.layout import layout_of as layout_of_model
from fransys_model.vocab import membership
from fransys_model.vocab.tables import items, units
from fransys_model.vocab.unit_index import unit_index

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from scale_units_fixture import build_scale  # noqa: E402

_N = 4


def _cold_caches():
    """Empty both caches and their build counts: the build that made the model filled them."""
    unit_index.cache_clear()
    unit_nodes_module._unit_nodes.cache_clear()


def _lookups(model) -> int:
    """Every per-unit and per-item query the build, the documents and the lists make; the count."""
    made = 0
    for unit in units(model):
        membership.unit_own_roots(model, unit)
        membership.unit_items(model, unit)
        membership.unit_subtree(model, unit)
        membership.standalone(model, unit)
        own_nodes(model, unit)
        made += 5
        for item in items(model):
            item_designation(model, item, unit=unit)
            reference_designation(model, item, unit=unit)
            made += 2
    for item in items(model):
        membership.external(model, item)
        membership.is_sole_unit_root(model, item)
        membership.is_harness(model, item)
        membership.cable_children(model, item)
        membership.enclosing_boards(model, item)
        made += 5
    for page in layout_of_model(model, Page).values():
        page_title(model, page)
        made += 1
    return made


def test_the_unit_index_and_the_own_nodes_are_each_built_once_per_model():
    # `with_document=True`: `_lookups` reads `layout_of_model(model, Page)`/`page_title`, both
    # empty with no document under decision 0037 (PS1) -- `build_scale`'s own default must stay
    # document-free (MODEL-BUILD acceptance 6), so this test asks for one explicitly instead.
    model = build_scale(_N, with_document=True).model
    _cold_caches()

    made = _lookups(model)

    assert made > 40 * _N, "many lookups, so one build is a fact and not a trivial count"
    assert unit_index.builds == 1
    assert unit_nodes_module._unit_nodes.builds == 1


def test_a_second_model_is_a_second_build_of_each():
    """The guard counts builds per digest, not per process: two models are two builds."""
    first = build_scale(_N, with_document=True).model
    second = build_scale(_N + 1, with_document=True).model
    assert first.digest != second.digest
    _cold_caches()

    _lookups(first)
    _lookups(second)

    assert unit_index.builds == 2
    assert unit_nodes_module._unit_nodes.builds == 2
