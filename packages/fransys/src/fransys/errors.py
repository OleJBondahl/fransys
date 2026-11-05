"""The facade's one error base."""


class FransysError(TypeError, ValueError):
    """A bad argument to a facade call: a wrong type (`TypeError`) or a bad value (`ValueError`)."""
