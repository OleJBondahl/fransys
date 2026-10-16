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
            (`fransys-kernel/src/fransys_kernel/schema.py:37`) for hashing,
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
# canonical JSON (FIELDS, `fransys_kernel/schema.py:37`, sufficient alone) -- never within
# fransys-model/src itself.
_.name_stem  # OTHER fransys-wago/src/fransys_wago/modules.py:85
_.single_signal  # OTHER fransys-wago/src/fransys_wago/modules.py:101
_.hide_unused_pins  # OTHER fransys-layout/src/fransys_layout/engines/schematic/read/steps.py:129
_.see  # OTHER fransys/src/fransys/_finding_text.py:27
_.unconnected  # OTHER fransys-kicad/src/fransys_kicad/check.py:158
_.beside  # OTHER fransys-layout/src/fransys_layout/stages/columns.py:80
_.jumper_group  # OTHER fransys-pdf/src/fransys_pdf/_lists_terminal.py:53
_.MOUNT  # OTHER fransys-author/src/fransys_author/wiring.py:95
_.L1  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:15
_.L2  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:17
_.L3  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:19
_.L_PLUS  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:13
_.L_MINUS  # OTHER fransys-parts/src/fransys_parts/_pole_facts.py:14
_.M  # TESTS fransys-parts/tests/test_pole_facts.py:139
_.conductor_mark  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.footprint_library  # OTHER fransys-kicad/src/fransys_kicad/netlist.py:37
_.footprint_name  # OTHER fransys-kicad/src/fransys_kicad/netlist.py:37
_.mate_port_designation  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.mate_designation  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.from_label  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.to_label  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.added  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.changed  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.loose_symbols  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.width_mm  # OTHER fransys-render/src/fransys_render/pages.py:48
_.height_mm  # OTHER fransys-render/src/fransys_render/pages.py:48
_.content_x_mm  # OTHER fransys-render/src/fransys_render/_symbols.py:64
_.content_y_mm  # OTHER fransys-render/src/fransys_render/_symbols.py:65
_.column_gap  # OTHER fransys-layout/src/fransys_layout/stages/place.py:146
_.row_gap  # OTHER fransys-layout/src/fransys_layout/stages/place.py:151
_.row_spacing  # OTHER fransys-layout/src/fransys_layout/stages/place.py:154
_.route_margin  # OTHER fransys-layout/src/fransys_layout/stages/_edge_paths.py:127
_.route_turn_penalty  # OTHER fransys-layout/src/fransys_layout/stages/_edge_paths.py:155
_.route_crossing_penalty  # OTHER fransys-layout/src/fransys_layout/stages/_edge_paths.py:156
_.band_ranks  # OTHER fransys-layout/src/fransys_layout/stages/place.py:164
_.group_ranks  # OTHER fransys-layout/src/fransys_layout/stages/partition.py:175
_.symbol  # OTHER fransys-render/src/fransys_render/_symbol_geometry.py:74
_.port_map  # OTHER fransys-layout/src/fransys_layout/engines/schematic/read/reading.py:205
_.produced_by  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.orientation  # OTHER fransys-render/src/fransys_render/_symbol_geometry.py:87
_.library_version  # OTHER fransys-render/src/fransys_render/check.py:63
_.cover  # OTHER fransys-pdf/src/fransys_pdf/checks.py:240
_.supplier  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.supplier_part_number  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.customer  # OTHER fransys-model/src/fransys_model/derive/title_block.py:27
_.author  # OTHER fransys-pdf/src/fransys_pdf/_geometry.py:221
_.nominal_voltage_v  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.max_voltage_v  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.min_voltage_v  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.capacity_ah  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
# F8 (2026-10-02): data-only record fields, no reader yet (model-0125)
_.nominal_power_w  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.power_loss_w  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.resistance_ohm  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
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
_.__kind__  # DICT fransys-kernel/src/fransys_kernel/conform.py:88
_.__subject__  # DICT fransys-kernel/src/fransys_kernel/checks.py:157
_.__unique__  # DICT fransys-kernel/src/fransys_kernel/checks.py:158
_.__singleton__  # DICT fransys-kernel/src/fransys_kernel/checks.py:154

# `kernel/record.py:130`: `FieldSpec.ref_kind`, read by plain attribute access but only from
# fransys-model's own tests (never from any package's src, including its own).
_.ref_kind  # TESTS fransys-kernel/tests/test_record.py:27

# `kernel/cache.py`: `DigestCached.builds`, a cache-hit counter read only by fransys-model's
# own tests to assert a builder ran the expected number of times; never read from any src.
_.builds  # TESTS fransys-kernel/tests/test_cache.py:40

# `derive/facts/keep_whole.py`: `KeepWhole` fields, read only by its own tests for now.
_.item_boxes  # TESTS fransys-model/tests/derive/test_keep_whole_sets.py:27
_.pole_groups  # TESTS fransys-model/tests/derive/test_keep_whole_sets.py:41
_.line_units  # TESTS fransys-model/tests/derive/test_keep_whole_sets.py:86
# EL-2a role-table fields (model-0288): FIELDS are `@record` fields; TESTS are read by tests only.
_.is_unit_boundary  # TESTS fransys-model/tests/derive/test_typed_accessors.py:16
_.band_rank  # TESTS fransys-model/tests/derive/test_typed_accessors.py:23
_.PORT  # TESTS fransys-model/tests/derive/test_typed_accessors.py:37
_.ASPECT_NODE  # DICT fransys-model/src/fransys_model/derive/facts/subjects.py:15
_.plain_contact  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:25
_.changeover  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:27
_.operator  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:28
_.pin_group  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:30
_.bar  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:32
_.protects  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:33
_.joins_net  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:48
_.switched  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:49
_.protective  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:50
_.bar_holder  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:75
_.plc_module  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:79
_.accessory  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:82
_.connector_housing  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:83
_.carries  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:95
_.lands  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:96
_.bridge  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:98
_.rail_link  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:99
_.mount  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:100
_.power  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:108
_.control  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:109


# --- fransys-author --------------------------------------------------------------------

# design.py/handles.py/wiring.py: the fluent authoring DSL. A builder method returns
# self/a handle, so nothing inside fransys_author/src itself ever chains it; every one is
# exercised by fransys-author's own tests (most also named by example in the consumer
# guide, packages/fransys/src/fransys/guide/*.md, though four -- chain, order, profile,
# plc -- are only named there as a concept, not shown as the DSL call).
_.harness  # TESTS fransys-author/tests/test_external.py:83
_.rack  # TESTS fransys-author/tests/surface/test_s4b_handles.py:82

# design.py:833 draw_in, handles.py:161 scale: same fluent DSL shape, exercised only in
# fransys-author's own tests (plus draw_in's own README example); not named in the guide.
_.page_title  # TESTS fransys-author/tests/surface/test_layout_page_title.py:27

# surface/ (EA-CORE): the engineer surface is off `__all__` until EA-SWAP, so only its own tests
# call device/terminal_strip and the colour constants.
_.terminal_strip  # TESTS fransys-author/tests/surface/test_terminal_strip.py:18

# --- fransys-layout --------------------------------------------------------------------

# engines/schematic/read/house.py DEFAULT_PROFILE: read
# only from fransys-layout's own tests, never from fransys_layout/src or another package.
_.DEFAULT_PROFILE  # TESTS fransys-layout/tests/engines/test_defaults.py:68

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

# --- fransys_author surface: coverage (EA-COVERAGE) ---------------------------------------
# Surface calls off `fransys_author.__all__` until EA-SWAP; their tests call them.
_.layout  # TESTS fransys-author/tests/surface/test_coverage_layout.py:46
_.busbar  # TESTS fransys-author/tests/equivalence/test_coverage_pairs.py:119
_.rail_bond  # TESTS fransys-author/tests/equivalence/test_coverage_pairs.py:120
_.star  # TESTS fransys-author/tests/surface/test_detail_star.py:33
_.detail  # TESTS fransys-author/tests/surface/test_chain_beside.py:20

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

# --- fransys-model: OperatedBy members (parts-0020) ------------------------------------------

# vocab/enums.py: what operates a part's contacts; the loader builds them by value.
_.PUSH  # TESTS fransys-model/tests/derive/test_operated_by_model.py:86
_.MUSHROOM  # TESTS fransys-model/tests/derive/test_operated_by_model.py:43
_.TURN  # TESTS fransys-model/tests/derive/test_operated_by_model.py:50
_.POSITION  # TESTS fransys-model/tests/derive/test_operated_by_model.py:58
_.port_pairs  # OTHER fransys-layout/src/fransys_layout/engines/schematic/read/pairs.py:29
_.limits  # TESTS fransys-author/tests/surface/test_coverage_facts.py:89

# CT5-1C: stub_a and stub_b of layout/cable_results.py CoreWire; engines/cable/write writes
# them, render draws a stub as the wire's own end segment. Vulture runs per package, so a
# model field read only in layout or render stays here (CT5-2, layout-0141).
_.stub_a  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.stub_b  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.stub_of  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
# CT5-2: the cable drawing's fields and enum members, read by render's cable_blocks
_.pitch  # OTHER fransys-layout/tests/engines/test_cable_engine.py:269
_.text_x  # OTHER fransys-render/src/fransys_render/cables.py:109
_.text_y  # OTHER fransys-render/src/fransys_render/cables.py:109
_.TOP  # OTHER fransys-render/src/fransys_render/cables.py:62
_.BOTTOM  # OTHER fransys-render/src/fransys_render/cables.py:62
_.status  # OTHER fransys-overview/src/fransys_overview/_data_changes.py:20
_.SOLID  # OTHER fransys-render/src/fransys_render/cables.py:61
_.DASHED  # OTHER fransys-render/src/fransys_render/cables.py:61
_.BLANK  # OTHER fransys-render/src/fransys_render/cables.py:85
# CABLE-CORES: drawn-mark and open-core row fields read in other packages
_.core_a  # OTHER fransys-render/src/fransys_render/cables.py:143
_.core_b  # OTHER fransys-render/src/fransys_render/cables.py:143
_.tick  # OTHER fransys-pdf/src/fransys_pdf/_bridge.py:90
_.room  # OTHER fransys-layout/src/fransys_layout/engines/cable/read/facts.py:157
_.shorter  # OTHER fransys-pdf/src/fransys_pdf/_sheet_index.py:36
_.SHEET_INDEX  # OTHER fransys-pdf/src/fransys_pdf/document.py:46
_.heading_1  # OTHER fransys-pdf/src/fransys_pdf/_geometry.py:115
_.heading_2  # OTHER fransys-pdf/src/fransys_pdf/_geometry.py:116
_.svg  # OTHER fransys-pdf/src/fransys_pdf/_background.py:59
_.counter_box  # OTHER fransys-pdf/src/fransys_pdf/_background.py:60
_.logo_box  # OTHER fransys-pdf/src/fransys_pdf/_background.py:64
_.title_room_mm  # OTHER fransys-pdf/src/fransys_pdf/_sheet_index.py:39
# `fransys_model/derive/rows_sheet_pages.py`: `SheetFrame` and `FrameStrip` values, read by
# `fransys_render._sheet_draw` (render-0019).
_.cell_width  # OTHER fransys-render/src/fransys_render/_sheet_draw.py:44
_.cell_height  # OTHER fransys-render/src/fransys_render/_sheet_draw.py:44
_.border  # OTHER fransys-render/src/fransys_render/_sheet_draw.py:41
_.band_top  # OTHER fransys-render/src/fransys_render/_sheet_draw.py:53
_.title_width  # OTHER fransys-render/src/fransys_render/_sheet_draw.py:54
_.logo_x  # OTHER fransys-render/src/fransys_render/_sheet_draw.py:59
# `electrical_symbols/sheet_title.py`: the `TitleBlock` font layers, read by
# `fransys_render._sheet_draw` (render-0019).
_.bold  # OTHER fransys-render/src/fransys_render/_sheet_draw.py:78
_.labels  # OTHER fransys-render/src/fransys_render/_sheet_draw.py:84
_.heading  # OTHER fransys-render/src/fransys_render/_labels.py:79
_.titles  # OTHER fransys-render/src/fransys_render/_labels.py:80
_.export_kind  # OTHER fransys/src/fransys/pipeline.py:551
_.title_band_mm  # OTHER fransys-render/src/fransys_render/sheet_check.py:44
# PLACEMENT-FACTS: read by the problem builder later
_.in_strip_row  # FIELDS fransys-model/src/fransys_model/derive/rows_footprints.py:23
# CORE-WAVE0: contract fields the stages read later; jsonform walks them with dataclasses.fields()
_.D  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.Q  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.R  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.X  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.band_align  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.bend_penalty  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.bottom_pin  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.boundary_of  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.box_pin_pitch_min  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.box_pins  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.child_of  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.colour  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.colours  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.column_gap_min  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.corner_order  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.cross_links  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.crossed  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.cycle_split  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.demand  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.detour  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.draw_in  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.drivers  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.exact_order_limit  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.exact_order_nodes  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.failed  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.fixed_order  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.forced_break_before  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.forced_end  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.height_est  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.justify  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.keep_whole  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.ladders  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.min_fill  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.min_pitch  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.natural_edge  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.open_stub  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.order_pairs  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.orientations  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.pin_edges  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.reference_plan  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.reroute_rounds  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.row_footprint  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.row_group  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.row_tags  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.short  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.short_height  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.slack  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.tag_stagger  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.top_pin  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.trunks  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.w_arrow  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.w_f  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.w_p  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.w_ref  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.w_row  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.w_tag  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.w_violation  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.width_est  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.wire_label_sides  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.wire_labels  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.wire_min  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.wiring_grid  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.order_cost  # FIELDS fransys-layout/src/fransys_layout/core/order.py:54
_.collinear  # FIELDS fransys-layout/src/fransys_layout/core/route_counts.py:43

# `electrical_symbols/natural.py`: `Natural` fields, read by the builder of the first engine
# switch (SYMDEF-SLOTS SS6); until then only its own tests read them.
_.keepout  # TESTS electrical-symbols/tests/test_natural.py:48
_.cut_x  # TESTS electrical-symbols/tests/test_natural.py:75
_.cut_y  # TESTS electrical-symbols/tests/test_natural.py:75
# `fransys_model/layout/drawn_results.py`: `DrawnSymbol` orient, tint and muted, read by render
# once it draws the scene through symdef (REVIEW-OUTPUTS O3, layout-0278).
_.orient  # FIELDS packages/fransys-model/src/fransys_model/layout/drawn_results.py:40
_.tint  # FIELDS packages/fransys-model/src/fransys_model/layout/drawn_results.py:47
_.muted  # FIELDS packages/fransys-model/src/fransys_model/layout/drawn_results.py:48
