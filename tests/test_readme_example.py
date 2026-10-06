"""The first python block of README.md is website/example.py, byte for byte.

The README shows the one example the site and the tests run; a copy that drifts misleads (PM10).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_readme_example_is_website_example() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    block = readme.split("```python\n", 1)[1].split("\n```", 1)[0]
    example = (ROOT / "website" / "example.py").read_text(encoding="utf-8")
    assert block == example.removesuffix("\n")
