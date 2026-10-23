"""The placement core's own error: stdlib only, with no convention of ours in it."""


class CoreError(Exception):
    """Base of every error the general placement core raises; the core is meant to stand alone.

    The facade does not wrap it: a Fransys layout fault; report it with the design.
    """
