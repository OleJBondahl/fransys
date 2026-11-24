"""The identifier of a pin name and the order of a pin by its marking (decision model-0128)."""

import re

from fransys_model.kernel import NaturalKey, natural_key

lazy from .templates import PortTemplate


def identifier(name: str) -> str:
    """The Python identifier of a part's function or pin `name`: `24V+` is `P_24V_plus`.

    In a pin or function name `-` is a sign (`24V-` is `P_24V_minus`), unlike a part number's.
    `+` and `-` become `_plus` and `_minus`, other non-word characters `_`, a leading digit `P_`.
    """
    text = re.sub(r"\W", "_", name.replace("+", "_plus").replace("-", "_minus"))
    return f"P_{text}" if text[:1].isdigit() else text


def port_order_key(template: PortTemplate) -> tuple[NaturalKey, str]:
    """Order of one end: its marking (its name when none is printed), then its name."""
    marking = template.name if template.marking is None else template.marking
    return natural_key(marking), template.name
