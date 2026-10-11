"""`AuthorError`: a mistake seen at the call; the rest is `freeze`'s (A-r2).

The builder never calls `freeze` and never re-implements a model rule.
"""


class AuthorError(Exception):
    """A design mistake the builder catches at the call, with a message an author can act on."""
