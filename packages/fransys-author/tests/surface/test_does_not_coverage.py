"""EA13 for `Layout`: it is reached only as a return value, so the surface walk misses it."""

from fransys_author.surface._layout import Layout

from .test_does_not_lines import has_does_not

_MEMBERS = (
    "chain",
    "keep_together",
    "break_before",
    "order",
    "symbol",
    "draw_in",
    "sheet",
    "profile",
)


def test_layout_and_each_hint_say_what_they_do_not_do() -> None:
    missing = [n for n in _MEMBERS if not has_does_not(getattr(Layout, n).__doc__)]
    assert not has_does_not(None)
    assert has_does_not(Layout.__doc__)
    assert not missing, f"no 'Does not' line: {missing}"


def test_the_member_list_is_every_public_layout_callable() -> None:
    public = {n for n, v in vars(Layout).items() if not n.startswith("_") and callable(v)}
    assert public == set(_MEMBERS)
