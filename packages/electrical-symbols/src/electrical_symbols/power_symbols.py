"""The symbol key a power kind is drawn with: the one home of the kind-to-key table (es-0080)."""

from symdef import SymdefError

# The model's `PowerKind` values (a power-supply, ground or protective-earth net) to library keys.
_KEYS = {
    "supply": "power-supply",
    "ground": "ground",
    "pe": "protective-earth",
}


def power_symbol_key(kind: str) -> str:
    """The library key a net of power kind `kind` is drawn with.

    `kind` is a `PowerKind` value: "supply", "ground" or "pe". Any other string raises
    `SymdefError` naming the kind; the fix is a row in this table and a symbol of that key.
    """
    try:
        return _KEYS[kind]
    except KeyError:
        known = ", ".join(_KEYS)
        msg = f"no power symbol for kind {kind!r}; add it to power_symbols._KEYS (known: {known})"
        raise SymdefError(msg) from None
