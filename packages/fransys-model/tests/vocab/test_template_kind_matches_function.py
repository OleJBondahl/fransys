"""A stamped function has its template's kind: `instantiate` copies `kind`, the role rows read it.

Every part file of `examples/demo-parts` is placed once, so every function the demo parts stamp
is checked against the `FunctionTemplate` it came from.
"""

import tomllib
from pathlib import Path

import fransys as fr
import pytest

from fransys_model.vocab.tables import function_templates, functions

_PART_FILES = Path(__file__).parents[4] / "examples" / "demo-parts" / "demo_parts" / "parts"


def _demo_parts() -> list[tuple[str, bool]]:
    """The MPN of every demo part file, in file-name order, and whether it has a terminal function (authored on a strip, R2102)."""
    files = [tomllib.loads(path.read_text(encoding="utf-8")) for path in sorted(_PART_FILES.glob("*.toml"))]
    return [(f["part"]["mpn"], any(fn.get("kind") == "terminal" for fn in f.get("function", ()))) for f in files]


@pytest.fixture(scope="module")
def model() -> fr.Model:
    """A design with one device of every demo part, built."""
    d = fr.design("demo_parts")
    for number, (mpn, terminal) in enumerate(_demo_parts(), start=1):
        if terminal:
            d.terminal_strip(f"P{number}", mpn, 1)
        else:
            d.device(f"P{number}", mpn)
    return fr.build(d).model


def test_every_stamped_function_has_its_template_kind(model: fr.Model) -> None:
    """Each `(function key, template kind, function kind)` where the two differ is listed."""
    templates = function_templates(model)
    stamped = list(functions(model).values())
    assert stamped, "the demo parts stamped no functions"
    mismatched = [
        (function.key, templates[function.template].kind, function.kind)
        for function in stamped
        if function.template is not None and templates[function.template].kind != function.kind
    ]
    assert mismatched == []
