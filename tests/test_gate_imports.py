"""Import gates E1 and E2 (spec SURFACE-COHERENCE R1): who may take a build-stage name.

E10 (no `fransys_kernel.<submodule>` import outside the kernel) needs no code here: the plant
fails `test_boundaries.py::test_package_crosses_into_another_package_only_through_its_surface`.
"""

from gate_scan import Import, imports_of, in_package, src_imports

KERNEL_SOURCES = ("fransys_model.kernel", "fransys_kernel")
FREEZE_NAMES = frozenset(["freeze", "merge"])
FREEZE_PACKAGES = frozenset(["fransys", "fransys_model", "fransys_kernel"])

LAY_OUT_NAMES = frozenset(
    ["lay_out_cables", "lay_out_diagrams", "lay_out_overview", "lay_out_schematic"]
)
PASS_NAMES = frozenset(["number", "allocate_plc", "resolve_wire_rows"])
STAGE_PACKAGES = frozenset(["fransys", "fransys_model", "fransys_layout"])


def freeze_imports(rows: list[Import]) -> list[Import]:
    """E1: rows outside `fransys` and the model that take `freeze` or `merge` from the kernel."""
    return [
        row
        for row in rows
        if row.name in FREEZE_NAMES
        and any(in_package(row.source, kernel) for kernel in KERNEL_SOURCES)
        and row.package not in FREEZE_PACKAGES
    ]


def stage_imports(rows: list[Import]) -> list[Import]:
    """E2: rows outside `fransys`, the model and layout that take a `lay_out_*` or pass name."""
    return [
        row
        for row in rows
        if row.package not in STAGE_PACKAGES
        and (
            (row.name in LAY_OUT_NAMES and in_package(row.source, "fransys_layout"))
            or (row.name in PASS_NAMES and in_package(row.source, "fransys_model.derive"))
        )
    ]


def _sites(rows: list[Import]) -> list[str]:
    return [f"{r.module}:{r.line} {r.source}.{r.name}" for r in rows]


def test_only_the_facade_freezes_or_merges():
    rows = src_imports()
    assert any(r.package == "fransys" and r.name == "freeze" for r in rows), "no positive hit"
    assert _sites(freeze_imports(rows)) == []


def test_only_the_facade_the_model_and_layout_take_a_stage():
    rows = src_imports()
    assert any(r.package == "fransys" and r.name == "lay_out_cables" for r in rows)
    assert _sites(stage_imports(rows)) == []


def test_the_freeze_gate_can_fail():
    forms = [
        "from fransys_model.kernel import freeze",
        "from fransys_kernel import (\n    merge,\n)",
        "from fransys_kernel.freeze import freeze",
        "import fransys_kernel as k\nk.freeze(1)",
        "from fransys_model import kernel\nkernel.merge(1)",
        "import fransys_kernel.merge as m\nm.merge",
    ]
    for source in forms:
        assert freeze_imports(imports_of(source, "fransys_author")), source
    assert freeze_imports(imports_of(forms[0], "fransys.pipeline")) == []
    assert freeze_imports(imports_of("from fransys_model.kernel import Model", "x")) == []


def test_the_stage_gate_can_fail():
    forms = [
        "from fransys_layout import lay_out_schematic",
        "from fransys_layout.engines.cable import lay_out_cables",
        "from fransys_model.derive import number",
        "from fransys_model.derive.passes.wire_rows import resolve_wire_rows",
        "import fransys_layout as fl\nfl.lay_out_overview",
        "from fransys_model import derive\nderive.allocate_plc(1)",
    ]
    for source in forms:
        assert stage_imports(imports_of(source, "fransys_pdf")), source
    assert stage_imports(imports_of(forms[0], "fransys_layout.x")) == []
    assert stage_imports(imports_of("from fransys_model.derive import bom_lines", "x")) == []
