"""Field case: the module `fransys parts-module` writes passes the workspace ty by default.

The engineering shape: a part library turned into a typed parts module, which a design imports and
a consumer's ty gate checks together with the design, under ty's default rules.

The bug (consumer on ty 0.0.88, which the workspace now pins): each generated `__getitem__` was
an error,
`invalid-attribute-override`, because `TypedDevice` and `TypedFn` declared `__getitem__:
ClassVar[None]` to hide the catch-all and the stub's method could not override a `None`. The
workspace pin was 0.0.84, which lacks that check, so the TY6 gate stayed green.
The fix (decision 0203, amended 2026-10-15): the base declares `__getitem__(self, m: Never) ->
Pin` for the type checker, a valid base for the stub's narrowing override; a typo stays one error.
"""

import subprocess
from pathlib import Path

from fransys.parts_module import parts_module

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "uv.lock").is_file())


def test_the_generated_stub_has_no_ty_finding_on_the_workspace_ty(tmp_path) -> None:
    stub = tmp_path / "gparts.py"
    stub.write_text(parts_module("demo_parts"), encoding="utf-8")
    run = subprocess.run(  # noqa: S603 -- the workspace's pinned ty, fixed arguments
        [
            *("uv", "run", "ty", "check", "--project", str(tmp_path)),
            *("--python", str(ROOT / ".venv"), "--output-format", "concise", str(stub)),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert run.returncode == 0, run.stdout + run.stderr
