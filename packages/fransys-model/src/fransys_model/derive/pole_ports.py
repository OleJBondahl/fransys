"""The printed port-name prefix of each pole of a repeated symbol."""


def pole_prefix(index: int, poles: int) -> str:
    """The prefix of pole `index` (0-based): `"1."` for the first of several, `""` for one pole.

    `electrical_symbols.repeat` names pole N's ports with an `N.` prefix; the through path
    names the base ports, so every caller joins this prefix to them.
    """
    return "" if poles <= 1 else f"{index + 1}."
