"""WP8 tests: instance-level vocab kinds (ROADMAP WP8, design/vocabulary.md 6)."""

from fransys_model.kernel import Id
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, PortRole


def test_item_has_the_designed_fields() -> None:
    """`Item` carries `part`, `parent`, `position`, `tag`, `description`, `installed`."""
    part_id = Id(kind="part", value="0" * 32)
    item = Item(
        id=Id(kind="item", value="1" * 32),
        key=("examples", "relay-1"),
        part=part_id,
        parent=None,
        position=None,
        tag=None,
        description="Invented example relay instance",
    )
    assert item.part == part_id
    assert item.tag is None
    assert item.installed is True


def test_item_installed_false_is_explicit() -> None:
    """`installed=False` keeps the item constructible; the BOM query drops it (design/vocabulary.md
    6)."""
    item = Item(
        id=Id(kind="item", value="2" * 32),
        key=("examples", "spare-relay"),
        part=None,
        parent=None,
        position=None,
        tag="-K99",
        description="Invented spare, not installed",
        installed=False,
    )
    assert item.installed is False


def test_function_has_the_designed_fields() -> None:
    """`Function` carries `item`, `template`, `name`, `kind`."""
    item_id = Id(kind="item", value="1" * 32)
    template_id = Id(kind="function_template", value="3" * 32)
    coil = Function(
        id=Id(kind="function", value="4" * 32),
        key=("examples", "relay-1", "fn", "coil"),
        item=item_id,
        template=template_id,
        name="coil",
        kind=FunctionKind.COIL,
    )
    assert coil.item == item_id
    assert coil.template == template_id


def test_port_has_the_designed_fields() -> None:
    """`Port` carries `function`, `template`, `name`, `role`."""
    function_id = Id(kind="function", value="4" * 32)
    a1 = Port(
        id=Id(kind="port", value="5" * 32),
        key=("examples", "relay-1", "fn", "coil", "port", "A1"),
        function=function_id,
        template=None,
        name="A1",
        role=PortRole.GENERIC,
    )
    assert a1.function == function_id
    assert a1.name == "A1"
