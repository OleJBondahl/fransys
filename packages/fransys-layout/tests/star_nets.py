"""A cabinet of `n` three-terminal star nets: `n` `#n` numbers in one drawing set.

A net of three ports is drawn as markers (R7 B4), one `#n` number each, so the number count is
`n` however the pages fall. Invented parts from `layout_cabinet`.
"""

from functools import cache

from layout_cabinet import _ORIGIN, _Builder, _specs

from fransys_model.kernel import Draft, Model, freeze
from fransys_model.vocab import Aspect, FunctionKind


@cache
def star_nets(n: int) -> Model:
    """`n` stars: terminal `XA:i` to `XB:n-1-i` to `XC:i`, frozen, not laid out."""
    b = _Builder(second_location=False, chains_enabled=False)
    for group in ("ga", "gb"):
        b._node(group, Aspect.FUNCTION, group.upper())
        b.location[group] = "c1"
    parts = {spec.key: b.part(spec) for spec in _specs()}
    b.choice(FunctionKind.TERMINAL, "terminal", {"internal": "n", "external": "s"})
    strips = [b.strip(tag) for tag in ("XA", "XB", "XC")]
    ta, tb, tc = (
        [b.terminal(parts["terminal"], strip, i + 1, group) for i in range(n)]
        for strip, group in zip(strips, ("ga", "gb", "gb"), strict=True)
    )
    for i in range(n):
        b.wire(ta[i].port("terminal", "external"), tb[n - 1 - i].port("terminal", "external"))
        b.wire(tb[n - 1 - i].port("terminal", "external"), tc[i].port("terminal", "external"))
    draft = Draft()
    draft.extend(b.records, origin=_ORIGIN)
    return freeze(draft)
