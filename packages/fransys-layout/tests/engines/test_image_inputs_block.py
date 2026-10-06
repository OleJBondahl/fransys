"""V10, model-0119: `image_inputs` hands a block's contacts to its parent's contact table.

Contactor `K1` (a coil and a contact of its own) carries an untagged add-on block of one NO and
one NC contact. The block is no device: its contacts are owned by `K1`, so they are listed in
`K1`'s table and carry marks. Every name is invented.
"""

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.contact_marks import image_inputs
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.vocab import (
    Function,
    FunctionKind,
    Item,
    Part,
    PartCategory,
    Port,
    PortRole,
)

_ORIGIN = Origin(file="tests/engines/test_image_inputs_block.py", line=1, note="V10 block")
_PART = Part(
    id=make_id(Part, ("p",)),
    key=("p",),
    mpn="EXAMPLE-P",
    manufacturer="Example Co",
    description="Invented",
    category=PartCategory.GENERIC,
    class_code="K",
)

_KEYS = {"main": ("k1", "main"), "c53": ("blk", "c53"), "c61": ("blk", "c61")}


def _item(key: str, *, tag: str | None, parent: str | None) -> Item:
    return Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=_PART.id,
        parent=None if parent is None else make_id(Item, (parent,)),
        position=None,
        tag=tag,
        description="",
        installed=True,
    )


def _function(item: str, name: str, kind: FunctionKind, ports: tuple[str, ...]) -> list:
    key = (item, name)
    function = Function(
        id=make_id(Function, key),
        key=key,
        item=make_id(Item, (item,)),
        template=None,
        name=name,
        kind=kind,
    )
    made = [
        Port(
            id=make_id(Port, (*key, p)),
            key=(*key, p),
            function=function.id,
            template=None,
            name=p,
            role=PortRole.GENERIC,
        )
        for p in ports
    ]
    return [function, *made]


def _contactor_with_block():
    records = [
        _PART,
        _item("k1", tag="K1", parent=None),
        _item("blk", tag=None, parent="k1"),
        *_function("k1", "coil", FunctionKind.COIL, ("A1", "A2")),
        *_function("k1", "main", FunctionKind.CONTACT_NO, ("13", "14")),
        *_function("blk", "c53", FunctionKind.CONTACT_NO, ("53", "54")),
        *_function("blk", "c61", FunctionKind.CONTACT_NC, ("61", "62")),
    ]
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_a_blocks_contacts_are_owned_by_its_parent_and_carry_marks() -> None:
    """Every contact of `K1` and of its block maps to `K1`; the coil is no contact, so it is not."""
    # UNDO: read/contact_marks.py:image_inputs, `owned_contacts(model, item)` -> only those whose
    #     function is a spec of `item` itself (a block's contacts then have no owner)
    model = _contactor_with_block()
    inputs = image_inputs(model, read_inputs(model))
    fn = {name: make_id(Function, key) for name, key in _KEYS.items()}
    parent = make_id(Item, ("k1",))
    assert inputs.owners == {fn["main"]: parent, fn["c53"]: parent, fn["c61"]: parent}
    assert set(inputs.marks) == {fn["main"], fn["c53"], fn["c61"]}
