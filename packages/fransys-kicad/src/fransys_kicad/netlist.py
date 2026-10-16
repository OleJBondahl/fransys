"""KiCad netlist writer."""

import uuid
from typing import TYPE_CHECKING

from fransys_model.derive import board_netlist, board_pins

if TYPE_CHECKING:
    from fransys_model.derive import NetlistPart, PinNet
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item

# Every component timestamp is a `uuid5` of this namespace and the item's id, so one item always
# gets one timestamp and KiCad keeps its footprint matched when the netlist is regenerated.
_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_DNS, "schematika_kicad"
)  # predates the rename: seed, never changed

_ESCAPES = str.maketrans({"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r"})


def _quote(text: str) -> str:
    """`text` as a KiCad string: quoted, with a backslash, a quote and a line break escaped."""
    return f'"{text.translate(_ESCAPES)}"'


def _header(source: str) -> str:
    return (
        '(export (version "E")\n'
        "  (design\n"
        f"    (source {_quote(source)})\n"
        '    (tool "fransys_kicad"))'
    )


def _comp(part: NetlistPart) -> str:
    footprint = f"{part.footprint_library}:{part.footprint_name}"
    dnp = "" if part.installed else '      (property (name "dnp"))\n'
    return (
        f"    (comp (ref {_quote(part.designation)})\n"
        f"      (value {_quote(part.mpn)})\n"
        f"      (footprint {_quote(footprint)})\n"
        f"{dnp}"
        '      (sheetpath (names "/") (tstamps "/"))\n'
        f"      (tstamps {_quote(str(uuid.uuid5(_NAMESPACE, part.item.value)))}))"
    )


def _net(code: int, net: PinNet) -> str:
    nodes = "\n".join(
        f"      (node (ref {_quote(pin.ref)}) (pin {_quote(pin.pad)}))" for pin in net.pins
    )
    return f'    (net (code "{code}") (name {_quote(net.name)})\n{nodes})'


def _section(name: str, blocks: list[str]) -> str:
    if not blocks:
        return f"  ({name})"
    return f"  ({name}\n" + "\n".join(blocks) + ")"


def netlist(model: Model, board: Id[Item]) -> str:
    """Write the KiCad 9.0 s-expression netlist of one board (`kicad-0001`), LF line ends.

    Timestamps are `uuid5` of the item id, so footprints stay matched. A comp-less node is
    written as the rows give it (`check`); a part not installed is a `comp` marked `dnp`.

    Args:
        model: A frozen, numbered model.
        board: The board item; its part carries a ``pcb`` facet.

    Returns:
        The netlist as KiCad s-expression text. Same model digest, same text.

    Raises:
        SchemaError: as `board_netlist` (`board` unknown, or an item has no designation).
    """
    rows = board_netlist(model, board)
    pins = board_pins(model, board)
    sections = [
        _header(rows.board_designation),
        _section("components", [_comp(part) for part in rows.parts]),
        _section(
            "nets",
            [_net(code, net) for code, net in enumerate(pins.nets, start=1)],
        ),
    ]
    return "\n".join(sections) + ")\n"
