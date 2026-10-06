"""WP14 end-to-end tests over this repo's invented cabinet (ROADMAP WP14, package-layout.md 9).

Golden files live in `tests/golden/`. They are regenerated, never edited by hand:
`uv run pytest packages/fransys-layout --regenerate-golden` rewrites them from the current
engine, and `git diff` then shows what the layout change did. A golden is a claim about the
layout, so read that diff before committing it.

Regeneration must run single-process. `conftest.py` refuses `--regenerate-golden` when
`-n` is set, on the controller, before workers spawn: parallel workers would rewrite these
files concurrently and overwrite each other (decision 0013). The shared recipes run `-n 6`,
so this is enforced now rather than a convention to remember.
"""

from dataclasses import replace
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
from debug_svg import write_debug_pages
from layout_cabinet import build_cabinet

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic import engine, run_stages
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.engines.schematic.write import placements as placements_module
from fransys_layout.lint.codes import (
    CONNECTION_DRAWN_TWICE,
    CONNECTION_NOT_DRAWN,
    MARKER_UNPAIRED,
    ROUTE_SHORTS_NETS,
    ROUTE_WRONG_PORT,
)
from fransys_layout.stages import pagerun
from fransys_model.kernel import (
    Draft,
    Model,
    Origin,
    diff,
    dumps,
    evolve,
    freeze,
    loads,
    make_id,
)
from fransys_model.layout import Page, Profile, SheetFormat, SymbolPlacement, layout_of
from fransys_model.vocab import AspectNode

if TYPE_CHECKING:
    from collections.abc import Callable

    from _typeshed import DataclassInstance

    from fransys_layout.engines.schematic.read import StageInputs
    from fransys_layout.engines.schematic.write.keys import WriteKeys
    from fransys_model.kernel import Finding, Id, Record

_GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden"
_COHERENCE_CODES = {
    CONNECTION_DRAWN_TWICE,
    CONNECTION_NOT_DRAWN,
    MARKER_UNPAIRED,
    ROUTE_SHORTS_NETS,
    ROUTE_WRONG_PORT,
}
_PLACEMENT_KIND = "layout.symbol_placement"


@cache
def _run(**options: bool) -> tuple[Model, tuple[Finding, ...]]:
    """The cabinet built with `options`, frozen and laid out; one run per option set."""
    return lay_out_schematic(freeze(build_cabinet(**options)))


def _laid_out(**options: bool) -> Model:
    return _run(**options)[0]


@pytest.fixture
def regenerate(request: pytest.FixtureRequest) -> bool:
    """True under `--regenerate-golden`: the goldens are rewritten instead of compared."""
    return bool(request.config.getoption("--regenerate-golden"))


def _golden(name: str, actual: str, *, regenerate: bool) -> str:
    """The stored golden `name`; under `--regenerate-golden` it is first rewritten to `actual`."""
    path = _GOLDEN_DIR / name
    if regenerate:
        path.write_text(actual, encoding="utf-8", newline="\n")
    return path.read_text(encoding="utf-8")


_NORMALIZE_ORIGIN = Origin(file=__file__, line=1, note="golden version bump probe")


def _with_bumped_versions(model: Model) -> Model:
    """`model` with every `produced_by`/`library_version` field changed to a different,
    real-looking value, not the "0.0.0" token the `normalized` fixture writes.

    Only for `test_normalized_keeps_names_and_ignores_only_versions` below: proof that
    normalisation makes any two version values compare equal (not merely "already the fixed
    placeholder" by construction).
    """
    remove_ids = []
    put_records = []
    for table in model.tables.values():
        for record_id, record in table.items():
            changed = {}
            if hasattr(record, "produced_by"):
                changed["produced_by"] = "fransys-layout/schematic 9.9.9"
            if hasattr(record, "library_version"):
                changed["library_version"] = "electrical-symbols 9.9.9 / graphical-symbols 9.9.9"
            if changed:
                remove_ids.append(record_id)
                put_records.append(
                    cast("Record", replace(cast("DataclassInstance", record), **changed))
                )
    return evolve(model, remove=remove_ids, put=put_records, origin=_NORMALIZE_ORIGIN)


def test_normalized_keeps_names_and_ignores_only_versions(
    normalized: Callable[[Model], Model],
) -> None:
    """Permanent regression test for the `normalized` fixture (decisions layout-0046, -0119).

    A version-only change compares equal; a renamed producer or any other field change does not.
    All copies are in memory, never the tracked golden file.
    """
    model = _laid_out()
    original = dumps(normalized(model))
    assert dumps(normalized(_with_bumped_versions(model))) == original
    assert "fransys-layout/schematic 0.0.0" in original
    assert "electrical-symbols 0.0.0 / graphical-symbols 0.0.0" in original

    renamed = loads(dumps(model).replace("fransys-layout/", "other-layout/"))
    assert dumps(normalized(renamed)) != original
    renamed = loads(dumps(model).replace("electrical-symbols ", "other-symbols "))
    assert dumps(normalized(renamed)) != original

    placement_id, placement = next(iter(layout_of(model, SymbolPlacement).items()))
    moved = cast("Record", replace(placement, x=placement.x + 1))
    moved_model = evolve(model, remove=(placement_id,), put=(moved,), origin=_NORMALIZE_ORIGIN)
    assert dumps(normalized(moved_model)) != original


def _findings_text(model: Model, findings: tuple[Finding, ...]) -> str:
    """One line per finding: severity, code, the authoring keys of its subjects, the message."""
    lines = [
        f"{finding.severity.name} {finding.code} "
        f"{','.join('/'.join(model.tables[s.kind][s].key) for s in finding.subjects)} "
        f"{finding.message}"
        for finding in findings
    ]
    return "\n".join(lines) + "\n"


def test_cabinet_layout_matches_golden(
    *, regenerate: bool, normalized: Callable[[Model], Model]
) -> None:
    """The laid-out cabinet's canonical JSON is byte-stable against the golden file.

    Written and compared through the `normalized` fixture: producer names stay, versions are
    "0.0.0", so a version bump alone moves nothing and a renamed producer does (layout-0119).
    """
    actual = dumps(normalized(_laid_out()))
    golden = _golden("cabinet_laid_out.json", actual, regenerate=regenerate)
    assert actual == golden


def test_cabinet_layout_digest_matches_golden(
    *, regenerate: bool, normalized: Callable[[Model], Model]
) -> None:
    """`digests["layout"]` of the laid-out cabinet is the one in the golden file.

    The digest is computed on the version-normalised model, for the same reason as the JSON
    golden above.
    """
    actual = normalized(_laid_out()).digests["layout"] + "\n"
    assert actual == _golden("cabinet_layout_digest.txt", actual, regenerate=regenerate)


def test_cabinet_findings_match_golden(*, regenerate: bool) -> None:
    """The findings of the cabinet run: lamp `H1`, the one function in no chain, and its box.

    Under the deep dive the contact and coil functions the old golden listed as "in no chain"
    take part in chain discovery (D1), and board `A1`'s idle `edge` connector is not drawn (D8),
    so its `FUNCTION_UNPLACED_IN_COLUMN` and `SYMBOL_DEFAULTED` are gone.
    """
    model, findings = _run()
    actual = _findings_text(model, findings)
    assert actual == _golden("cabinet_findings.txt", actual, regenerate=regenerate)


def test_a_golden_comparison_can_fail(normalized: Callable[[Model], Model]) -> None:
    """A different layout differs from the JSON and digest goldens, a lost finding from the third.

    The relay cabinet lays out differently but raises the same findings, so the findings
    golden is tried against the cabinet's own findings with one of them missing.
    """
    stored = {
        name: (_GOLDEN_DIR / name).read_text(encoding="utf-8")
        for name in ("cabinet_laid_out.json", "cabinet_layout_digest.txt", "cabinet_findings.txt")
    }
    assert dumps(normalized(_laid_out(extra_relay=True))) != stored["cabinet_laid_out.json"]
    # The stored goldens are normalised (layout-0119): compare normalised against them.
    assert (
        normalized(_laid_out(extra_relay=True)).digests["layout"] + "\n"
        != stored["cabinet_layout_digest.txt"]
    )
    model, findings = _run()
    assert _findings_text(model, findings[1:]) != stored["cabinet_findings.txt"]


def test_layout_is_independent_of_authoring_order() -> None:
    """Shuffle test: the same design authored in two orders has one layout digest."""
    assert _laid_out().digests["layout"] == _laid_out(reverse=True).digests["layout"]


def test_layout_is_idempotent() -> None:
    """Laying out an already laid-out model changes no digest."""
    once = _laid_out()
    twice, _ = lay_out_schematic(once)
    assert twice.digests == once.digests


def test_engineering_digests_are_untouched() -> None:
    """A layout run never changes the plant: `core` and `facet` digests stay equal."""
    authored = freeze(build_cabinet())
    laid_out, _ = lay_out_schematic(authored)
    assert laid_out.digests["core"] == authored.digests["core"]
    assert laid_out.digests["facet"] == authored.digests["facet"]
    assert laid_out.digests["layout"] != authored.digests["layout"]


def _leak(monkeypatch: pytest.MonkeyPatch, extra_gap: Callable[[Model], int]) -> None:
    """Make the engine's column gap depend on `extra_gap(model)`: a layout that reads the model.

    A stand-in for a real defect (a stage that lets table order or earlier layout records
    steer the result), so a check that says the layout does not depend on them can be seen
    to fail.
    """
    real = engine.read_inputs

    def read(model: Model) -> StageInputs:
        inputs = real(model)
        gap = inputs.profile.column_gap + extra_gap(model)
        return replace(inputs, profile=replace(inputs.profile, column_gap=gap))

    monkeypatch.setattr(engine, "read_inputs", read)


def test_the_kernel_erases_authoring_order_at_freeze() -> None:
    """Why the shuffle test above cannot fail on the engine: both orders freeze to one model.

    `freeze` canonicalises, so the engine is handed equal models whatever order the records
    were authored in. `test_layout_is_independent_of_the_order_of_the_stage_inputs` is the
    shuffle that reaches the stages.
    """
    forward, backward = freeze(build_cabinet()), freeze(build_cabinet(reverse=True))
    assert forward == backward


def _reordered(inputs: StageInputs, order: Callable[[tuple], tuple]) -> StageInputs:
    """`inputs` with every tuple of records in another order: what a different iteration gives."""
    return replace(
        inputs,
        functions=order(inputs.functions),
        connections=order(inputs.connections),
        net_groups=order(inputs.net_groups),
        rails=order(inputs.rails),
        chains=order(inputs.chains),
        choices=order(inputs.choices),
        groups=order(inputs.groups),
        locations=order(inputs.locations),
        label_texts=order(inputs.label_texts),
    )


@pytest.mark.parametrize(
    "order",
    [lambda records: records[::-1], lambda records: records[1::2] + records[::2]],
    ids=["reversed", "interleaved"],
)
def test_layout_is_independent_of_the_order_of_the_stage_inputs(
    order: Callable[[tuple], tuple],
) -> None:
    """The shuffle that reaches the stages: every input tuple reordered, the same layout out."""
    model = freeze(build_cabinet())
    inputs = read_inputs(model)
    assert run_stages(model, _reordered(inputs, order)) == run_stages(model, inputs)


def test_the_stage_input_shuffle_can_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stage that follows the order of its input gives another layout when the order changes.

    The stages sort defensively at several layers, so no single real edit makes the shuffle
    above fail (removing every sort in `columns.py` leaves it green, `partition` sorts too);
    a stand-in that reads the first and last function of its input shows the comparison bites.
    """
    real = engine.stage_results

    def leaky(model: Model, inputs: StageInputs):
        first, last = inputs.functions[0].function, inputs.functions[-1].function
        gap = inputs.profile.column_gap + (8 if first < last else 0)
        return real(model, replace(inputs, profile=replace(inputs.profile, column_gap=gap)))

    monkeypatch.setattr(engine, "stage_results", leaky)
    model = freeze(build_cabinet())
    inputs = read_inputs(model)
    reversed_inputs = _reordered(inputs, lambda records: records[::-1])
    assert run_stages(model, reversed_inputs) != run_stages(model, inputs)


def test_the_idempotence_check_can_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """An engine that lets earlier layout records steer the result changes a digest on a rerun."""
    _leak(monkeypatch, lambda model: 8 if model.tables.get("layout.route") else 0)
    once, _ = lay_out_schematic(freeze(build_cabinet()))
    twice, _ = lay_out_schematic(once)
    assert twice.digests != once.digests


def test_the_engineering_digests_notice_an_engineering_change() -> None:
    """`core` differs once a relay is added, so the equality above means something."""
    base, relay = freeze(build_cabinet()), freeze(build_cabinet(extra_relay=True))
    assert base.digests["core"] != relay.digests["core"]


def _coherence(findings: tuple[Finding, ...]) -> list[str]:
    return [f.code for f in findings if f.code in _COHERENCE_CODES]


def test_no_coherence_findings_on_the_cabinet() -> None:
    """Every model connection is drawn, severed by one pair, or covered by an echo."""
    _, findings = _run()
    assert _coherence(findings) == []


def test_the_coherence_check_can_fail_on_the_cabinet(monkeypatch: pytest.MonkeyPatch) -> None:
    """The same run with the first route of every page lost names a connection not drawn."""
    real = pagerun.route

    def lossy(*args: Any, **kwargs: Any) -> tuple[tuple, tuple]:
        routes, findings = real(*args, **kwargs)
        return routes[1:], findings

    monkeypatch.setattr(pagerun, "route", lossy)
    _, findings = lay_out_schematic(freeze(build_cabinet()))
    assert CONNECTION_NOT_DRAWN in _coherence(findings)


@pytest.mark.parametrize("width_mm", [300, 245])
def test_no_coherence_findings_when_the_cabinet_is_split_over_more_pages(width_mm: int) -> None:
    """Narrower sheets cut wires between pages: markers, echoes and replicas, still coherent.

    The rule is that a cabinet split over pages stays coherent, so the precondition asserted
    is a split (more than one page) that severs a signal: a marker with no `star` kind, the
    D9 star markers being on the sheet whether or not it is split. The page count itself is
    not a rule: D4 packs groups by their measured widths (D13), so it moves with the text
    (300 mm gives 2 pages now, 245 mm still gives 3); the narrow golden pins one exact split.
    """
    model = freeze(_on_sheet(width_mm))
    inputs = read_inputs(model)
    layout, _, findings = run_stages(model, inputs)
    assert len(layout.pages) > 1
    assert [marker for marker in layout.markers if not marker.star]
    assert _coherence(findings) == []


def _on_sheet(width_mm: int, **options: bool) -> Draft:
    """The cabinet on an authored sheet `width_mm` wide, the house profile values otherwise."""
    draft = build_cabinet(**options)
    sheet = SheetFormat(
        id=make_id(SheetFormat, ("test", "sheet")),
        key=("test", "sheet"),
        name="narrower",
        width_mm=width_mm + 20,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=width_mm,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    profile = Profile(
        id=make_id(Profile, ("test", "profile")),
        key=("test", "profile"),
        sheet_format=sheet.id,
        column_gap=DEFAULT_PROFILE.column_gap,
        row_gap=DEFAULT_PROFILE.row_gap,
        route_margin=DEFAULT_PROFILE.route_margin,
        text_height=DEFAULT_PROFILE.text_height,
        marker_padding=DEFAULT_PROFILE.marker_padding,
        route_turn_penalty=DEFAULT_PROFILE.route_turn_penalty,
        route_crossing_penalty=DEFAULT_PROFILE.route_crossing_penalty,
        band_ranks=DEFAULT_PROFILE.band_ranks,
        group_ranks=DEFAULT_PROFILE.group_ranks,
    )
    draft.extend((sheet, profile), origin=Origin(file=__file__, line=1, note="narrower sheet"))
    return draft


# The width spec X5 (`docs/archive/specs/2026-09-22-cross-reference-partner.md`) requires: a width
# that gives all three required contents at once (at least one severed cut, one
# `CROSS_REFERENCE` label, one net-group cut). 158, not the spec's original 150: model-0040
# (spec B1) draws board `A1`'s `edge` connector, which shifts where this cabinet splits
# (model-0040 has the measured table); 150-157 mm give zero tag-echo decisions, 158 mm is
# the narrowest that gives one (Q4: measured at 1 mm resolution, re-measured after
# `effective_placement` landed -- unchanged, since this fixture places every function
# directly, no fallback is exercised). `fransys-render`'s tests load this package's own
# golden by path and hardcode a marker position and a page count, both of which 118-171 mm
# still give, so 158 keeps those green too (the root spec needs the new number, listed in
# the hand-back).
_NARROW_WIDTH_MM = 158


@cache
def _narrow_run(**options: bool) -> tuple[Model, tuple[Finding, ...]]:
    """The cabinet on the narrow sheet (`_NARROW_WIDTH_MM`), frozen and laid out."""
    return lay_out_schematic(freeze(_on_sheet(_NARROW_WIDTH_MM, **options)))


def _narrow_laid_out(**options: bool) -> Model:
    return _narrow_run(**options)[0]


@cache
def _two_location_laid_out() -> Model:
    """The house-sheet cabinet with `=P2` moved to a second location `+C2`, laid out.

    No narrow sheet needed: the severed control signal from `-K1` `aux` (`=P1`, `+C1`) to
    `-K2` `aux` (`=P2`, `+C2`) already crosses drawing sets at the default width.
    """
    return lay_out_schematic(freeze(build_cabinet(second_location=True)))[0]


def _changed_placements(before: Model, after: Model) -> list[Id[Any]]:
    """The ids of the `layout.symbol_placement` records both models hold that differ."""
    return [i for i in diff(before, after).changed if i.kind == _PLACEMENT_KIND]


def _off_group_pages_of(ids: list[Id[Any]], after: Model, group: Id[Any]) -> list[Id[Any]]:
    """The `ids` that, in `after`, sit on a page whose groups do not include `group`."""
    pages, placements = layout_of(after, Page), layout_of(after, SymbolPlacement)
    return [i for i in ids if all(one.group != group for one in pages[placements[i].page].groups)]


def _off_group_pages(before: Model, after: Model, group: Id[Any]) -> list[Id[Any]]:
    """The changed placements of `after` that sit on a page whose groups do not include `group`."""
    return _off_group_pages_of(_changed_placements(before, after), after, group)


def _added_placements(before: Model, after: Model) -> list[Id[Any]]:
    """The ids of `layout.symbol_placement` records `after` holds that `before` does not."""
    return [i for i in diff(before, after).added if i.kind == _PLACEMENT_KIND]


def test_adding_one_relay_moves_only_its_own_group(*, regenerate: bool) -> None:
    """Stability (D17): the relay in `=P2` changes placements only on the pages of `=P2`.

    A placement on a page that does not hold `=P2` never changes; a group sharing a page with
    it (`=SUP` after the relay, on `=P2`'s page) may shift along that page. The number of
    changed placements is part of the golden, so a regression in stability shows up as a diff
    even while it stays on `=P2`'s pages.
    """
    before, after = _laid_out(), _laid_out(extra_relay=True)
    changed = _changed_placements(before, after)
    # 15 since the tag keep-out trim (designer): narrower columns put more of =P2 on shared
    # pages, so more of its own placements shift; the locality checks below are unchanged
    stored = _golden("cabinet_stability.txt", f"{len(changed)}\n", regenerate=regenerate)
    assert len(changed) == int(stored.split()[0])
    group = make_id(AspectNode, ("p2",))
    assert _off_group_pages(before, after, group) == []
    assert [i for i in diff(before, after).removed if i.kind == _PLACEMENT_KIND] == []
    assert _off_group_pages_of(_added_placements(before, after), after, group) == []


def test_the_stability_check_can_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """An engine whose layout shifts when the model grows moves placements outside `=P2`."""
    functions = len(freeze(build_cabinet()).tables["function"])
    _leak(monkeypatch, lambda model: 8 if len(model.tables["function"]) > functions else 0)
    before, _ = lay_out_schematic(freeze(build_cabinet()))
    after, _ = lay_out_schematic(freeze(build_cabinet(extra_relay=True)))
    assert _off_group_pages(before, after, make_id(AspectNode, ("p2",))) != []


def test_the_added_placement_check_can_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """A spurious extra placement outside `=P2` would slip past the `.changed`/`.removed` checks.

    Stand-in for a real defect (an engine that mis-groups a replica): `write.placements.placements`
    is patched to fabricate one more `SymbolPlacement`, for an existing function, on a page
    outside `=P2`'s groups, only once the relay has grown the model.
    """
    functions = len(freeze(build_cabinet()).tables["function"])
    real = placements_module.placements
    group = make_id(AspectNode, ("p2",))

    def leaky(
        keys: WriteKeys, results: Any, page_of: Any, sets: Any, stamp: str
    ) -> tuple[list[Any], Any]:
        records, discriminator = real(keys, results, page_of, sets, stamp)
        if len(keys.function) > functions:
            off_group = next(p for p in page_of.values() if all(g.group != group for g in p.groups))
            key = (*records[0].key, "bogus")
            bogus = replace(
                records[0], id=make_id(SymbolPlacement, key), key=key, page=off_group.id
            )
            records = [*records, bogus]
        return records, discriminator

    monkeypatch.setattr(placements_module, "placements", leaky)
    before, _ = lay_out_schematic(freeze(build_cabinet()))
    after, _ = lay_out_schematic(freeze(build_cabinet(extra_relay=True)))
    assert _off_group_pages_of(_added_placements(before, after), after, group) != []


def test_cabinet_narrow_layout_matches_golden(
    *, regenerate: bool, normalized: Callable[[Model], Model]
) -> None:
    """The 158 mm cabinet's canonical JSON is byte-stable against the narrow golden file.

    Spec X5: this sheet is the one narrow enough to give a severed cut, a `CROSS_REFERENCE`
    label and a net-group cut all at once, which is why the D2 equality test needs it.
    Written and compared through the `normalized` fixture (decision layout-0119).
    """
    actual = dumps(normalized(_narrow_laid_out()))
    golden = _golden("cabinet_narrow_laid_out.json", actual, regenerate=regenerate)
    assert actual == golden


def test_cabinet_narrow_layout_digest_matches_golden(
    *, regenerate: bool, normalized: Callable[[Model], Model]
) -> None:
    """`digests["layout"]` of the 158 mm cabinet is the one in the narrow golden file."""
    actual = normalized(_narrow_laid_out()).digests["layout"] + "\n"
    assert actual == _golden("cabinet_narrow_layout_digest.txt", actual, regenerate=regenerate)


def test_cabinet_narrow_findings_match_golden(*, regenerate: bool) -> None:
    """The findings of the 158 mm cabinet run: no `ROUTE_FAILED` (decision `layout-0038`
    closed that), and one WARNING, `GROUP_SPLIT` for `=P1`, whose columns still do not fit one page.

    D4 and D13 (groups packed by measured text widths) took the other `GROUP_SPLIT`s away, and
    with them the label and content-box warnings the old, wider text slots caused.
    """
    model, findings = _narrow_run()
    actual = _findings_text(model, findings)
    assert actual == _golden("cabinet_narrow_findings.txt", actual, regenerate=regenerate)


def test_adding_one_relay_on_the_narrow_sheet_moves_only_its_own_group(*, regenerate: bool) -> None:
    """Stability at 158 mm (D17): the relay in `=P2` changes placements only on `=P2`'s pages.

    Nine placements change (the golden), all of them `=P2`'s own: the relay widens `=P2`'s
    columns, which restacks the group and spreads it over a second page of its own; `=P1` and
    `=SUP` have no page in common with it and stay put.
    """
    before, after = _narrow_laid_out(), _narrow_laid_out(extra_relay=True)
    changed = _changed_placements(before, after)
    stored = _golden("cabinet_narrow_stability.txt", f"{len(changed)}\n", regenerate=regenerate)
    assert len(changed) == int(stored.split()[0])
    group = make_id(AspectNode, ("p2",))
    assert _off_group_pages(before, after, group) == []
    assert [i for i in diff(before, after).removed if i.kind == _PLACEMENT_KIND] == []
    assert _off_group_pages_of(_added_placements(before, after), after, group) == []


def test_cabinet_two_location_layout_matches_golden(
    *, regenerate: bool, normalized: Callable[[Model], Model]
) -> None:
    """The two-location cabinet's canonical JSON is byte-stable against its golden file.

    Written and compared through the `normalized` fixture (decision layout-0119).
    """
    actual = dumps(normalized(_two_location_laid_out()))
    golden = _golden("cabinet_two_location_laid_out.json", actual, regenerate=regenerate)
    assert actual == golden


def test_cabinet_two_location_layout_digest_matches_golden(
    *, regenerate: bool, normalized: Callable[[Model], Model]
) -> None:
    """`digests["layout"]` of the two-location cabinet is the one in its golden file."""
    actual = normalized(_two_location_laid_out()).digests["layout"] + "\n"
    assert actual == _golden(
        "cabinet_two_location_layout_digest.txt", actual, regenerate=regenerate
    )


def test_debug_pages_are_written_for_a_human_to_look_at(tmp_path: Path) -> None:
    """One SVG per page; looking at them is part of done for placement and routing work."""
    model = freeze(build_cabinet())
    inputs = read_inputs(model)
    layout, _, _ = run_stages(model, inputs)
    paths = write_debug_pages(layout, tmp_path, sheet=inputs.sheet)
    assert len(paths) == len(layout.pages) > 0
    assert all(path.read_text(encoding="utf-8").startswith("<svg") for path in paths)
