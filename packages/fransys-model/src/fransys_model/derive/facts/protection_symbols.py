"""The symbol a protection type draws as: the one home of the type-to-symbol table (R3359)."""

from typing import Final

_SYMBOLS: Final = {
    "none": ("circuit-breaker",),
    "fuse": ("fuse",),
    "mcb": ("circuit-breaker",),
    "motor_breaker": ("circuit-breaker",),
    "overload": ("thermal-overload",),
    "rcd": ("rcd",),
}


def protection_symbols(protection_type: str | None) -> tuple[str, ...]:
    """The symbol keys a protection `type` takes, the default first; `()` for a type this table does not know; `None` reads as `none`.

    Example: `mcb` and `motor_breaker` take `circuit-breaker`; `none` (a protection with no type) does too.
    """
    return _SYMBOLS.get(protection_type or "none", ())
