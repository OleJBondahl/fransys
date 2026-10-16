"""WAGO module XML."""

import re
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from fransys_model.derive import rack_modules_for_cdp

from .signals import SIGNALS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.derive import CdpRackModule, ChannelScaling, ItemId, PlcRackChannel, UnitId
    from fransys_model.kernel import Model

# `escape` does `&`, `<` and `>`; a line break or a tab in an attribute would be read back as a
# space, so they are written as character references.
_ATTRIBUTE_ESCAPES = {'"': "&quot;", "\n": "&#10;", "\r": "&#13;", "\t": "&#9;"}


def _attr(value: str) -> str:
    """`value` for the inside of a double-quoted XML attribute."""
    return escape(value, _ATTRIBUTE_ESCAPES)


def _sanitise(text: str) -> str:
    """`text` as a CDP name: `[A-Za-z0-9_]` only, no `_` run or edge, `N_` before a first digit."""
    name = re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_]", "_", text)).strip("_")
    return f"N_{name}" if name[:1].isdigit() else name


def _letters(index: int) -> str:
    """0 is `a`, 25 is `z`, 26 is `aa`, 27 is `ab`, 702 is `aaa`: a total function of the index."""
    text = ""
    number = index + 1
    while number:
        number, rest = divmod(number - 1, 26)
        text = chr(ord("a") + rest) + text
    return text


def _element(
    tag: str, depth: int, attributes: Sequence[tuple[str, str]], children: Sequence[str] = ()
) -> list[str]:
    """The lines of one element: attributes as given, an explicit end tag, never `/>`."""
    indent = "  " * depth
    text = "".join(f' {name}="{_attr(value)}"' for name, value in attributes)
    if not children:
        return [f"{indent}<{tag}{text}></{tag}>"]
    return [f"{indent}<{tag}{text}>", *children, f"{indent}</{tag}>"]


def _point(name: str, raw: int, engineering: object) -> list[str]:
    attributes = [
        ("InValue", str(raw)),
        ("OutValue", str(engineering)),
        ("Model", "Automation.ScalingPoint<double>"),
        ("Name", name),
        ("Type", "double"),
    ]
    return _element("ScalingPoint", 4, attributes)


def _scaling(scaling: ChannelScaling) -> list[str]:
    points = [
        *_point("ScalingPoint", scaling.raw_min, scaling.eng_min),
        *_point("ScalingPoint1", scaling.raw_max, scaling.eng_max),
    ]
    attributes = [
        ("Interpolation", "Linear"),
        ("Model", "Automation.ScalingOperator<double>"),
        ("Name", "Scale"),
        ("Type", "double"),
    ]
    return _element("Operator", 3, attributes, points)


def _channel(channel: PlcRackChannel, nr: int) -> list[str]:
    signal = SIGNALS[channel.signal]
    attributes = [
        ("Input", "1" if signal.output else "0"),
        ("Model", f"CDPSignalChannel<{signal.kind}>"),
        ("Name", _sanitise(channel.name_stem)),
        ("NetworkConvert", "1"),
        ("Nr", str(nr)),
        ("Type", signal.kind),
        ("Value", "0"),
        ("Description", signal.description),
    ]
    children: list[str] = []
    if channel.scaling is not None:
        attributes.append(("Unit", channel.scaling.unit))
        children = _scaling(channel.scaling)
    return _element("Channel", 2, attributes, children)


def _module_name(entry: CdpRackModule) -> str:
    module = entry.module
    abbr = "MIX" if entry.single_signal is None else SIGNALS[entry.single_signal].abbr
    return f"{module.mpn}_{len(module.channels)}{abbr}_{_letters(entry.ordinal)}"


def _module(entry: CdpRackModule) -> list[str]:
    module = entry.module
    channels = [
        line for nr, channel in enumerate(module.channels) for line in _channel(channel, nr)
    ]
    attributes = [
        ("Model", "WagoIOModules.IOModule"),
        ("Name", _module_name(entry)),
        ("Description", module.description),
    ]
    return _element("Module", 1, attributes, channels)


def modules_xml(model: Model, rack: ItemId, *, unit: UnitId | None = None) -> str:
    """The `<Modules>` fragment of CDP Studio's `WagoPFCIOServer.xml` for `rack`, pure.

    Formatted from `rack_modules_for_cdp`; layout, names and escaping: `docs/SPEC.md`.

    Args:
        model: A frozen, numbered model with PLC allocation applied.
        rack: The rack item; its children are WAGO I/O modules.
        unit: The unit whose own document this is, as `rack_modules_for_cdp`; `None`: the full form.

    Returns:
        The module configuration as XML text. Same model digest, same bytes.

    Raises:
        SchemaError: as `rack_modules_for_cdp` raises it.
    """
    lines = [
        line for entry in rack_modules_for_cdp(model, rack, unit=unit) for line in _module(entry)
    ]
    return "\n".join(_element("Modules", 0, [], lines)) + "\n"
