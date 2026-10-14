"""Twisted pairs and pair screens of a cable product (CC8, CC9): the lint's `CABLE_PAIR_INVALID`.

A pair is `{ cores = [a, b], screen = n }`, `screen` optional. Core numbers are 1-based indexes
into `core_colours`. The `SH` core named by no pair is the overall screen and is not checked here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

_PAIR_SIZE = 2


def check_pairs(cable_product: _toml.Table, path: str, line: int) -> list[Finding]:
    """One `CABLE_PAIR_INVALID` per broken rule; a non-dict pair is `FIELD_TYPE`'s to report."""
    colours, pairs = cable_product.get("core_colours"), cable_product.get("pairs")
    if type(colours) is not list or type(pairs) is not list:
        return []
    return [
        _toml.finding("CABLE_PAIR_INVALID", path, line, f"[cable_product] pairs: {problem}")
        for problem in _problems([p for p in pairs if type(p) is dict], colours)
    ]


def _problems(pairs: list[_toml.Table], colours: list[str]) -> list[str]:
    problems: list[str] = []
    named: list[int] = []
    screens: list[int] = []
    for pair in pairs:
        cores = pair.get("cores")
        if (
            type(cores) is not list
            or len(cores) != _PAIR_SIZE
            or any(type(c) is not int for c in cores)
        ):
            problems.append("cores must hold exactly two core numbers")
            continue
        named.extend(cores)
        problems.extend(_core_problems(cores, colours))
        if "screen" in pair:
            problems.extend(_screen_problems(pair["screen"], colours, screens))
    problems.extend(f"core {c} is in two pairs" for c in _repeated(named))
    problems.extend(f"screen {s} is named by two pairs" for s in _repeated(screens))
    return problems


def _core_problems(cores: list[int], colours: list[str]) -> list[str]:
    problems: list[str] = []
    for core in cores:
        if not 1 <= core <= len(colours):
            problems.append(f"core {core} is out of range 1..{len(colours)}")
        elif colours[core - 1] == "SH":
            problems.append(f"core {core} is SH and cannot be in a pair")
    return problems


def _screen_problems(screen: object, colours: list[str], screens: list[int]) -> list[str]:
    if type(screen) is not int or not 1 <= screen <= len(colours) or colours[screen - 1] != "SH":
        return [f"screen {screen!r} is not an SH core"]
    screens.append(screen)
    return []


def _repeated(values: list[int]) -> list[int]:
    return sorted({v for v in values if values.count(v) > 1})
