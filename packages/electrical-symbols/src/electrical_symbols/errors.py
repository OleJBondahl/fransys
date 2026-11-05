"""The package's one error base."""


class SymbolsError(ValueError, KeyError):
    """A bad argument to a symbol call: a value out of range (`ValueError`) or an unknown key (`KeyError`)."""
