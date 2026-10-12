"""`AuthorError`: a mistake seen at the call; the rest is `freeze`'s (A-r2).

The builder never calls `freeze` and never re-implements a model rule.
"""


class AuthorError(Exception):
    """A design mistake, caught at the call or, for a layout hint, at build."""


class AuthorAttributeError(AuthorError, AttributeError):
    """A name a device or function lacks, as an error `hasattr` and `getattr` defaults read."""
