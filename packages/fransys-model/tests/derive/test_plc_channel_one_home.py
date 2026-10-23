"""One home for the PLC channel facet read: only `derive/facts/roles.py` calls `facets_of` on it."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "fransys_model"
HOME = Path("derive") / "facts" / "roles.py"


def _is_plc_channel_call(node: ast.AST) -> bool:
    """True for `facets_of(_, PlcChannelFacet)`, however `facets_of` is reached."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
    if name != "facets_of" or len(node.args) < 2:
        return False
    second = node.args[1]
    return isinstance(second, ast.Name) and second.id == "PlcChannelFacet"


def _plc_channel_calls() -> list[tuple[Path, int]]:
    """Every (file, line) under the model source that reads the PLC channel facet."""
    hits = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        hits.extend(
            (path.relative_to(SRC), node.lineno)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _is_plc_channel_call(node)
        )
    return hits


def test_plc_channel_facet_read_has_one_home() -> None:
    """The PLC channel facet is read through one `facets_of` call, in `roles.py`."""
    hits = _plc_channel_calls()
    assert len(hits) == 1, f"expected 1 facets_of(..., PlcChannelFacet) call, found {hits}"
    path, _line = hits[0]
    assert path == HOME, f"the call must live in {HOME}, found in {path}"
