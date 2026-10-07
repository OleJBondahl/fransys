"""RR-O5 (layout-0132): the one rule for which marker heads a reference group.

A reference group is a net's markers that share one `#n`. Layout counts the groups of a set to
size `#n`'s digits; derive numbers them. Both ask this, on plain values.
"""

from fransys_model.layout import MarkerSide, StarKind


def heads_group(star: str, side: str, *, named: bool = False) -> bool:
    """Whether a marker with this `star` and `side` heads a reference group.

    `star` is a `StarKind` value, or `""` for a plain marker; `side` a `MarkerSide` value. A star
    reference heads its group; so does the owner end of a cut or of a split pair. A merged off
    stub heads one only when branches name it (`named`); a pure stub never does.
    """
    if star == StarKind.REF.value:
        return True
    if star == StarKind.OFF.value:
        return named
    return side == MarkerSide.OWNER.value
