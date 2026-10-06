"""KiCad symbol to part-file skeleton (spec section 8; dev tool, not a runtime input)."""

from typing import cast

from ._sexpr import Sexpr, parse_sexpr

# The fields a human must fill in, in the order they are written under [part] (spec P10).
_HUMAN_FIELDS = ("mpn", "manufacturer", "description", "category", "class_code")

# A symbol's own body style, second segment of a nested "<symbol>_<unit>_<style>" name.
# Style "2" is an alternate graphical convention (KiCad's "de Morgan" body) for the same
# electrical pins as style "1", so only style "1" is read; reading both would report every
# pin twice.
_BASE_STYLE = "1"

# A "(tag value ...)" s-expression node needs at least this many elements to have a value.
_TAGGED_LEN = 2

# KiCad's convention for "this pin has no name of its own", never a marking to carry over.
_NO_NAME = "~"


def part_file_skeleton(kicad_sym: str, symbol: str) -> str:
    """Build a part-file skeleton (spec section 7, `kicad-0002`) from one symbol of a library text.

    One port template per pin; a pin's KiCad name is its `marking` (F2), left out when it is `"~"`.

    Args:
        kicad_sym: The contents of a `.kicad_sym` library file.
        symbol: The name of the symbol to read within that library.

    Returns:
        A TOML part-file skeleton as text.

    Raises:
        ValueError: `kicad_sym` is no `kicad_symbol_lib`, or has no symbol named `symbol`.
    """
    library = _parse_library(kicad_sym)
    symbol_node = _find_symbol(library, symbol)
    pins = _pins(symbol_node, symbol)
    return _render(pins)


def _parse_library(kicad_sym: str) -> Sexpr:
    try:
        tree = parse_sexpr(kicad_sym)
    except ValueError as error:
        msg = f"not a parsable KiCad symbol library: {error}"
        raise ValueError(msg) from error
    if not tree or tree[0] != "kicad_symbol_lib":
        msg = "not a parsable KiCad symbol library: expected a kicad_symbol_lib root"
        raise ValueError(msg)
    return tree


def _find_symbol(library: Sexpr, name: str) -> Sexpr:
    """The top-level `(symbol "<name>" ...)` node of `library`."""
    for node in library[1:]:
        if (
            isinstance(node, list)
            and len(node) >= _TAGGED_LEN
            and node[0] == "symbol"
            and node[1] == name
        ):
            return node
    msg = f"no symbol {name!r} in this KiCad symbol library"
    raise ValueError(msg)


def _unit_style(sub_name: str, top_name: str) -> tuple[str, str] | None:
    """`(unit, style)` of a nested `"<top_name>_<unit>_<style>"` sub-symbol name, or `None`."""
    prefix = f"{top_name}_"
    if not sub_name.startswith(prefix):
        return None
    parts = sub_name[len(prefix) :].rsplit("_", 1)
    return (parts[0], parts[1]) if len(parts) == _TAGGED_LEN else None


def _pin_tag(pin_node: Sexpr, tag: str) -> str | None:
    for child in pin_node[1:]:
        if isinstance(child, list) and child and child[0] == tag and len(child) >= _TAGGED_LEN:
            return cast("str", child[1])  # a number or name is an atom, never a nested list
    return None


def _pin(pin_node: Sexpr) -> tuple[str, str | None] | None:
    """A pin's `(number, marking)`, or `None` when it has no number (spec P10, F2)."""
    number = _pin_tag(pin_node, "number")
    if number is None:
        return None
    name = _pin_tag(pin_node, "name")
    return (number, None if name is None or name == _NO_NAME else name)


def _pins(symbol_node: Sexpr, top_name: str) -> list[tuple[str, str | None]]:
    """Every pin's `(number, marking)` under `symbol_node`, file order, one body style per unit."""
    found: list[tuple[str, str | None]] = []
    for child in symbol_node[1:]:
        if not isinstance(child, list) or not child:
            continue
        if child[0] == "pin":
            pin = _pin(child)
            if pin is not None:
                found.append(pin)
        elif child[0] == "symbol" and len(child) >= _TAGGED_LEN:
            style = _unit_style(cast("str", child[1]), top_name)  # a symbol's name is an atom
            if style is not None and style[1] != _BASE_STYLE:
                continue
            found.extend(_pins(child, top_name))
    return found


def _toml_string(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n").replace("\r", "\\r")
    return f'"{escaped}"'


def _render(pins: list[tuple[str, str | None]]) -> str:
    lines = ["schema = 1", "", "[part]"]
    lines.extend(f'{field} = ""  # TODO: fill in' for field in _HUMAN_FIELDS)
    lines.extend(["", "[[function]]", 'name = "main"', 'kind = "generic"', "ports = ["])
    lines.extend(
        f'    {{ name = {_toml_string(number)}, role = "generic"'
        + ("" if marking is None else f", marking = {_toml_string(marking)}")
        + " },"
        for number, marking in pins
    )
    lines.append("]")
    return "\n".join(lines) + "\n"
