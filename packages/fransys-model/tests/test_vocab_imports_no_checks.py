"""`vocab` does not import `checks`: validators sit a layer above the records (model-0299)."""

import re
import subprocess
import sys
from pathlib import Path

_CODE = (
    "import sys, fransys_model.vocab\n"
    "print(sorted(m for m in sys.modules if m.startswith('fransys_model.checks')))"
)


def test_vocab_imports_no_checks() -> None:
    """A fresh interpreter importing `fransys_model.vocab` loads no `fransys_model.checks`."""
    run = subprocess.run(  # noqa: S603 - fixed argv, no input
        [sys.executable, "-I", "-c", _CODE], capture_output=True, text=True, check=True
    )
    assert run.stdout.strip() == "[]"


def test_vocab_source_names_no_derive_or_checks() -> None:
    """No vocab source line names `fransys_model.derive` or `fransys_model.checks` (EL-3 goal)."""
    root = Path(__file__).resolve().parents[1] / "src" / "fransys_model" / "vocab"
    hits = [
        f"{path.name}:{n}"
        for path in sorted(root.rglob("*.py"))
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if re.search(r"fransys_model\.(derive|checks)", line)
    ]
    assert hits == []
