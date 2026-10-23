"""The printed form of a revision under the `[revision] format` setting.

`vocab.revision_text` stays the identity form (folder names, keys); this one is what is shown.
"""

lazy from fransys_model.layout import RevisionForm

__all__ = ["revision_label"]


def revision_label(form: RevisionForm, version: int, revision: int) -> str:
    """The revision as printed: the `[revision] format` template (`1.1` by default)."""
    return form.format.format(version=version, revision=revision)
