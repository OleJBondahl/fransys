"""The printed form of a revision, re-exported from `vocab.revision_text` (FD4, SC2).

The function lives in `vocab` because `vocab.validators.revisions` names a revision in its
messages and `vocab` never imports `derive`; callers keep importing it from here.
"""

from fransys_model.vocab.revision_text import revision_text

__all__ = ["revision_text"]
