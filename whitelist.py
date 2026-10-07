"""vulture --min-confidence 60 whitelist, fed to every `just dead-code` line (decision 0050).

vulture's whitelist mechanism is name matching by AST, not `[tool.vulture]`: any name written
as a statement counts as a use of that name everywhere it is spelled the same, so an entry
here is a workspace-wide claim, not a per-file one -- this is why a bare identifier is never
enough (`nets_by_port` alone would also read as an *undefined name* to ruff/ty); each entry is
an attribute access on a dummy object instead, vulture's own documented pattern
(`vulture/whitelists/*.py` in the installed package: `SomeWhitelist().some_attr`).

One name per line, grouped by package, each with a trailing `# CLASS path:line` reason: the
reader class vulture's own per-package, per-src-tree scan cannot see (root CLAUDE.md's four
reader classes, decision 0050) plus one concrete file:line where that class applies --

    FIELDS  a field of a `@record`/`@value` class, read generically via `dataclasses.fields()`
            (`fransys-model/src/fransys_model/kernel/schema.py:37`) for hashing,
            freezing and canonical JSON -- true of every field of every such class in any
            package, so the class alone is sufficient evidence, no cross-package hit required.
    DICT    read as `vars(cls)[...]`/`vars(cls).get(...)` dict access rather than literal
            attribute syntax.
    OTHER   read by literal `obj.attr`/call syntax from another workspace package's `src/`.
            It is proven used there, so the ceiling does not count an OTHER entry whose cited
            file is in a different package from every package defining the name (decision 0115).
    TESTS   read only from the defining package's own `tests/` (or, for the author DSL, also
            the consumer guide/README/examples -- a fluent builder returns `self`/a handle, so
            nothing inside the package's own `src/` ever calls its own methods).

`tests/test_vulture_whitelist.py` holds every entry to these two mechanical checks: still
defined somewhere under `packages/*/src`, and the line matches the `# CLASS path:line` shape;
plus a shrink-only ceiling on the entries that count (decision 0115).
"""


class _Whitelist:
    """Any attribute access on it resolves, never raises.

    A whitelist entry parses and type-checks without importing or touching the real module.
    """

    def __getattr__(self, name: str) -> None:
        del name


_ = _Whitelist()

# --- fransys-model --------------------------------------------------------------------

# derive/rows.py, derive/indexes.py, layout/formats.py, layout/hints.py, layout/results.py,
# kernel/diff.py, vocab/document.py, vocab/facets/supply.py, vocab/project.py, vocab/ratings.py,
# vocab/revision.py: fields read by literal `obj.attr` syntax from another workspace package's
# `src/` (OTHER), through `derive.rows.column_rows`'s generic `getattr(record, name)` on a
# `*_COLUMNS` tuple (DICT, `derive/columns.py`), or -- for a field with neither, still a real
# `@record`/`@value` field read generically via `dataclasses.fields()` for hashing, freezing and
# canonical JSON (FIELDS, `kernel/schema.py:37`, sufficient alone) -- never within
# fransys-model/src itself.
_.nets_by_port  # OTHER fransys-layout/src/fransys_layout/engines/schematic/read/roles.py:48
_.hide_unused_pins  # OTHER fransys-layout/src/fransys_layout/engines/schematic/read/steps.py:129
_.internal_ends  # OTHER fransys-pdf/src/fransys_pdf/_lists.py:538
_.external_ends  # OTHER fransys-pdf/src/fransys_pdf/_lists.py:538
_.jumper_group  # OTHER fransys-pdf/src/fransys_pdf/_lists.py:576
_.MOUNT  # OTHER fransys-author/src/fransys_author/wiring.py:95
_.LINE  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:22
_.L1  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:15
_.L2  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:17
_.L3  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:19
_.L_PLUS  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:13
_.L_MINUS  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:14
_.M  # TESTS fransys-parts/tests/test_pole_facts.py:139
_.pole_side  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.conductor_mark  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.wired_to  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.field_device  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.field_device_designation  # OTHER fransys-wago/src/fransys_wago/modules.py:84
_.cable_designation  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.footprint_library  # OTHER fransys-kicad/src/fransys_kicad/netlist.py:37
_.footprint_name  # OTHER fransys-kicad/src/fransys_kicad/netlist.py:37
_.mate_port_designation  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.mate_designation  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.from_label  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.cross_section_mm2  # DICT fransys-model/src/fransys_model/derive/rows.py:165
_.to_label  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.via_designation  # OTHER fransys-overview/src/fransys_overview/html.py:52
_.added  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.changed  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.change  # OTHER fransys-reports/src/fransys_reports/changes.py:62
_.width_mm  # OTHER fransys-render/src/fransys_render/pages.py:48
_.height_mm  # OTHER fransys-render/src/fransys_render/pages.py:48
_.content_x_mm  # OTHER fransys-render/src/fransys_render/_symbols.py:64
_.content_y_mm  # OTHER fransys-render/src/fransys_render/_symbols.py:65
_.column_gap  # OTHER fransys-layout/src/fransys_layout/stages/place.py:146
_.row_gap  # OTHER fransys-layout/src/fransys_layout/stages/place.py:151
_.row_spacing  # OTHER fransys-layout/src/fransys_layout/stages/place.py:154
_.route_margin  # OTHER fransys-layout/src/fransys_layout/stages/route.py:386
_.text_height  # OTHER fransys-layout/src/fransys_layout/stages/images.py:72
_.marker_padding  # OTHER fransys-layout/src/fransys_layout/stages/images.py:73
_.route_turn_penalty  # OTHER fransys-layout/src/fransys_layout/stages/route.py:414
_.route_crossing_penalty  # OTHER fransys-layout/src/fransys_layout/stages/route.py:415
_.band_ranks  # OTHER fransys-layout/src/fransys_layout/stages/place.py:164
_.group_ranks  # OTHER fransys-layout/src/fransys_layout/stages/partition.py:175
_.symbol  # OTHER fransys-render/src/fransys_render/_symbol_geometry.py:74
_.port_map  # OTHER fransys-layout/src/fransys_layout/engines/schematic/read/reading.py:205
_.produced_by  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.orientation  # OTHER fransys-render/src/fransys_render/_symbol_geometry.py:87
_.library_version  # OTHER fransys-render/src/fransys_render/check.py:63
_.view  # OTHER fransys-render/src/fransys_render/_markers.py:90
_.cover  # OTHER fransys-pdf/src/fransys_pdf/_cover_checks.py:78
_.logo  # OTHER fransys-pdf/src/fransys_pdf/document.py:62
_.supplier  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.supplier_part_number  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.customer  # OTHER fransys-pdf/src/fransys_pdf/_geometry.py:218
_.author  # OTHER fransys-pdf/src/fransys_pdf/_geometry.py:221
_.notice  # OTHER fransys-pdf/src/fransys_pdf/checks.py:361
_.nominal_voltage_v  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.max_voltage_v  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.min_voltage_v  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.capacity_ah  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
# F8 (2026-10-02): data-only record fields, no reader yet (model-0125)
_.nominal_power_w  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.power_loss_w  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.resistance_ohm  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.checked  # OTHER fransys-pdf/src/fransys_pdf/_pages.py:66
_.approved  # OTHER fransys-pdf/src/fransys_pdf/_pages.py:67

# `layout/results.py` `PowerSymbol.pin_x`/`pin_y`: the lead's start, read only by render.
_.pin_x  # OTHER fransys-render/src/fransys_render/_symbols.py:82
_.pin_y  # OTHER fransys-render/src/fransys_render/_symbols.py:83

# `kernel/draft.py`: a method called from the author package's own fluent DSL (`design.py`),
# never called within fransys-model/src itself.
_.record_of  # OTHER fransys-author/src/fransys_author/design.py:278

# `kernel/record.py`: `@record` class metadata, written with dot syntax by the `record()`
# decorator itself but read only as `vars(cls)[...]`/`.get(...)` dict access elsewhere in the
# kernel and in `vocab/tables.py` -- never as literal `obj.__kind__` syntax vulture would see.
_.__kind__  # DICT fransys-model/src/fransys_model/kernel/conform.py:88
_.__subject__  # DICT fransys-model/src/fransys_model/kernel/checks.py:157
_.__unique__  # DICT fransys-model/src/fransys_model/kernel/checks.py:158
_.__singleton__  # DICT fransys-model/src/fransys_model/kernel/checks.py:154

# `kernel/record.py:130`: `FieldSpec.ref_kind`, read by plain attribute access but only from
# fransys-model's own tests (never from any package's src, including its own).
_.ref_kind  # TESTS fransys-model/tests/kernel/test_record.py:95

# `kernel/cache.py`: `DigestCached.builds`, a cache-hit counter read only by fransys-model's
# own tests to assert a builder ran the expected number of times; never read from any src.
_.builds  # TESTS fransys-model/tests/kernel/test_cache.py:40

# --- fransys-author --------------------------------------------------------------------

# design.py/handles.py/wiring.py: the fluent authoring DSL. A builder method returns
# self/a handle, so nothing inside fransys_author/src itself ever chains it; every one is
# exercised by fransys-author's own tests (most also named by example in the consumer
# guide, packages/fransys/src/fransys/guide/*.md, though four -- chain, order, profile,
# plc -- are only named there as a concept, not shown as the DSL call).
_.location  # TESTS fransys-author/tests/test_origins.py:61
_.scope  # TESTS fransys-author/tests/test_perf_draft.py:27
_.boundary  # TESTS fransys-author/tests/test_errors.py:441
_.unused  # TESTS fransys-author/tests/test_errors.py:482
_.strip  # TESTS fransys-author/tests/test_origins.py:90
_.cable  # TESTS fransys-author/tests/test_origins.py:109
_.harness  # TESTS fransys-author/tests/test_external.py:83
_.rack  # TESTS fransys-author/tests/surface/test_s4b_handles.py:82
_.wiring  # TESTS fransys-author/tests/test_errors.py:178
_.net  # TESTS fransys-author/tests/test_origins.py:150
_.mate  # TESTS fransys-author/tests/test_origins.py:164
_.bridge  # TESTS fransys-author/tests/test_errors.py:261
_.link  # TESTS fransys-author/tests/test_link.py:21
_.chain  # TESTS fransys-author/tests/test_origins.py:192
_.keep_together  # TESTS fransys-author/tests/test_design.py:546
_.break_before  # TESTS fransys-author/tests/test_design.py:554
_.order  # TESTS fransys-author/tests/test_errors.py:240
_.project  # TESTS fransys-author/tests/test_design.py:68
_.profile  # TESTS fransys-author/tests/test_origins.py:236
_.draft  # TESTS fransys-author/tests/test_origins.py:52
_.plc  # TESTS fransys-author/tests/test_origins.py:256
_.outer  # TESTS fransys-author/tests/test_origins.py:121
_.core  # TESTS fransys-author/tests/test_origins.py:121
_.run  # TESTS fransys-author/tests/test_errors.py:233

# design.py:833 draw_in, handles.py:161 scale: same fluent DSL shape, exercised only in
# fransys-author's own tests (plus draw_in's own README example); not named in the guide.
_.draw_in  # TESTS fransys-author/tests/test_design.py:813
_.scale  # TESTS fransys-author/tests/test_origins.py:261

# surface/ (EA-CORE): the engineer surface is off `__all__` until EA-SWAP, so only its own tests
# call device/terminal_strip and the colour constants.
_.device  # TESTS fransys-author/tests/surface/test_device.py:24
_.terminal_strip  # TESTS fransys-author/tests/surface/test_terminal_strip.py:18
_.BK  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.BN  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.RD  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.OG  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.BU  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.VT  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.GY  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.WH  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.PK  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.GD  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.SR  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.TQ  # TESTS fransys-author/src/fransys_author/surface/colours.py:23
_.SH  # TESTS fransys-author/src/fransys_author/surface/colours.py:23

# --- fransys-layout --------------------------------------------------------------------

# engines/schematic/read/house.py DEFAULT_PROFILE, electrical_symbols/text_metrics FONT_NAME: read
# only from fransys-layout's own tests, never from fransys_layout/src or another package.
_.DEFAULT_PROFILE  # TESTS fransys-layout/tests/engines/test_defaults.py:68
_.FONT_NAME  # TESTS electrical-symbols/tests/test_text.py:36

# stages/types.py:221 KindRoles.contact_closed: KindRoles is a fransys_model `@value` class
# (same FIELDS mechanism as the model section above), set by keyword in defaults.py's own
# KIND_ROLES table and exercised through KindRoles's generated `__eq__` in
# test_vocabulary_constants.py; never read by literal `.contact_closed` attribute syntax
# anywhere (a later consumer is still pending, decision layout-0085), but that is exactly the
# FIELDS class's own point -- a field's dataclass-generated dunders read it either way.
_.contact_closed  # FIELDS fransys-layout/src/fransys_layout/stages/types.py:221

# --- fransys-overview -------------------------------------------------------------------

# _vendor_cytoscape.py CYTOSCAPE_VERSION/CYTOSCAPE_SHA256: the vendored-library provenance
# constants (decision overview-0001), read only by fransys-overview's own test_vendor.py.
_.CYTOSCAPE_VERSION  # TESTS fransys-overview/tests/test_vendor.py:37
_.CYTOSCAPE_SHA256  # TESTS fransys-overview/tests/test_vendor.py:28

# --- fransys-layout: LabelKind.WIRE ---------------------------------------------------------

# stages/types.py `LabelKind.WIRE` mirrors the model's `LabelKind.WIRE` (their member names are
# held equal by a test); no stage requests it since WIRE-LIST-2 (V8), so only tests read it.
_.WIRE  # TESTS fransys-layout/tests/stages/test_sizing.py:27

# --- EF-B first half: wired by EF-B's second half (P4 resolve, P6 pole order) ---------------------
# `pole_order` (model-0128) is read through `vocab` by layout and author; tests call it too.
_.pole_order  # TESTS fransys-model/tests/vocab/test_markings.py:48

# --- fransys_author surface: coverage (EA-COVERAGE) ---------------------------------------
# Surface calls off `fransys_author.__all__` until EA-SWAP; their tests call them.
_.layout  # TESTS fransys-author/tests/surface/test_coverage_layout.py:46
_.busbar  # TESTS fransys-author/tests/equivalence/test_coverage_pairs.py:119
_.rail_bond  # TESTS fransys-author/tests/equivalence/test_coverage_pairs.py:120

# --- fransys_author surface: series, supplies (EA-SERIES) ----------------------------------
# Surface calls off `fransys_author.__all__` until EA-SWAP; their tests call them.
_.series  # TESTS fransys-author/tests/surface/test_series.py:77
_.parallel  # TESTS fransys-author/tests/surface/test_series.py:120
_.ac_supply  # TESTS fransys-author/tests/surface/test_supplies.py:74
_.dc_supply  # TESTS fransys-author/tests/surface/test_supplies.py:121

# --- fransys-model: ProtectionType members (model-0127) -------------------------------------

# vocab/enums.py: the five device types a part file names; the loader builds them by value.
_.FUSE  # TESTS fransys-parts/tests/test_lint_rest_protection.py:211
_.MCB  # TESTS fransys-parts/tests/test_lint_rest_protection.py:212
_.MOTOR_BREAKER  # TESTS fransys-parts/tests/test_lint_rest_protection.py:226
_.OVERLOAD  # TESTS fransys-parts/tests/test_lint_rest_protection.py:227
_.RCD  # TESTS fransys-parts/tests/test_lint_rest_protection.py:228
_.port_pairs  # OTHER fransys-layout/src/fransys_layout/engines/schematic/read/pairs.py:29
_.limits  # TESTS fransys-author/tests/surface/test_coverage_facts.py:89

# CT5-1C: stub_a and stub_b of layout/cable_results.py CoreWire; engines/cable/write writes
# them, render draws a stub as the wire's own end segment. Vulture runs per package, so a
# model field read only in layout or render stays here (CT5-2, layout-0141).
_.stub_a  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
_.stub_b  # FIELDS fransys-model/src/fransys_model/kernel/schema.py:37
# CT5-2: the cable drawing's fields and enum members, read by render's cable_blocks
_.pitch  # OTHER fransys-layout/tests/engines/test_cable_engine.py:269
_.text_x  # OTHER fransys-render/src/fransys_render/cables.py:109
_.text_y  # OTHER fransys-render/src/fransys_render/cables.py:109
_.TOP  # OTHER fransys-render/src/fransys_render/cables.py:62
_.BOTTOM  # OTHER fransys-render/src/fransys_render/cables.py:62
_.HARNESS  # OTHER fransys-render/src/fransys_render/cables.py:49
_.SOLID  # OTHER fransys-render/src/fransys_render/cables.py:61
_.DASHED  # OTHER fransys-render/src/fransys_render/cables.py:61
_.BLANK  # OTHER fransys-render/src/fransys_render/cables.py:85
_.tab_a  # OTHER fransys-render/src/fransys_render/diagram.py:55
_.tab_b  # OTHER fransys-render/src/fransys_render/diagram.py:56
_.text_width  # OTHER fransys-render/src/fransys_render/_diagram_boxes.py:46
_.dashed  # OTHER fransys-render/src/fransys_render/_diagram_boxes.py:68
