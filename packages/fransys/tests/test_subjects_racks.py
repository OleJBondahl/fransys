"""`_subjects.racks` is the parents of `derive.is_plc_module` children only."""

import fransys as fr
from _model_build_cover import layout_trigger_document
from fransys import _subjects

from fransys_model.kernel import Draft, Origin, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.templates import Part

_ORIGIN = Origin(file="packages/fransys/tests/test_subjects_racks.py", line=1, note="invented")


def _part(key: str, category: PartCategory) -> Part:
    return Part(
        id=make_id(Part, (key,)),
        key=(key,),
        mpn=f"SIM-{key}",
        manufacturer="Example Co",
        description=key,
        category=category,
        class_code="A",
    )


def _item(key: str, part: Part | None, parent: Item | None) -> Item:
    return Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=None if part is None else part.id,
        parent=None if parent is None else parent.id,
        position=None,
        tag=key.upper(),
        description=key,
    )


def test_only_the_parent_of_a_plc_module_is_a_rack() -> None:
    module_part = _part("module", PartCategory.PLC_MODULE)
    other_part = _part("relay", PartCategory.ELECTROMECHANICAL)
    rack = _item("rack", None, None)
    cabinet = _item("cab", None, None)
    module = _item("module-item", module_part, rack)
    relay = _item("relay-item", other_part, cabinet)
    draft = Draft()
    draft.extend([module_part, other_part, rack, cabinet, module, relay], origin=_ORIGIN)
    model = fr.build(draft, layout_trigger_document()).model
    assert _subjects.racks(model) == (rack.id,)
