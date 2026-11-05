"""A one-part library folder in a test's `tmp_path`, shared by the part-file tests."""

import itertools

_LIBRARY = 'schema = 2\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
_roots = itertools.count()


def part_root(tmp_path, text):
    """A library folder holding `text` as its only part file."""
    root = tmp_path / f"lib-{next(_roots)}"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    (root / "parts" / "p.toml").write_text(text)
    return root
