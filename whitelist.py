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
_.unconnected  # OTHER fransys-kicad/src/fransys_kicad/check.py:158
_.jumper_group  # OTHER fransys-pdf/src/fransys_pdf/_lists_terminal.py:53
_.conductor_mark  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.footprint_library  # OTHER fransys-kicad/src/fransys_kicad/netlist.py:37
_.footprint_name  # OTHER fransys-kicad/src/fransys_kicad/netlist.py:37
_.mate_port_designation  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.mate_designation  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.from_label  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.to_label  # DICT fransys-model/src/fransys_model/derive/rows.py:765
_.added  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.changed  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.produced_by  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.cover  # OTHER fransys-pdf/src/fransys_pdf/checks.py:240
_.library_version  # OTHER fransys-el/src/fransys_el/draw_layout.py:166
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
_.band_rank  # TESTS fransys-model/tests/derive/test_typed_accessors.py:23
_.PORT  # TESTS fransys-model/tests/derive/test_typed_accessors.py:37
_.operator  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:28
_.bar  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:32
_.switched  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:49
_.protective  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:50
_.bar_holder  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:75
_.plc_module  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:79
_.accessory  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:82
_.bridge  # FIELDS fransys-model/src/fransys_model/vocab/roles_types.py:98
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

# core/ placement names cut from `__all__` (decision 0226): read today by layout's own tests and
# by internal/ (placement corpus, count tests), wired into the engine at P6.1. `score` is both
# `core/score.py` score() and the `Scene.score` field.
_.assign_blocks  # TESTS fransys-layout/tests/core/pipeline_fixtures.py:21
_.marker_box  # TESTS fransys-layout/tests/core/test_marker_box.py:37
_.shape_key  # TESTS fransys-layout/tests/core/test_geometry.py:177
_.outline_hull  # TESTS fransys-layout/tests/core/test_outline.py:10
_.route_pages  # TESTS fransys-layout/tests/core/pipeline_fixtures.py:52
_.score  # TESTS fransys-layout/tests/core/test_score_plants.py:171
_.mark_pages  # TESTS fransys-layout/tests/core/test_text_markers_rename.py:41
_.widen  # TESTS fransys-layout/tests/core/test_widen_rename.py:88
_.label_nets  # TESTS fransys-layout/tests/core/test_wire_labels.py:106

# --- fransys-overview -------------------------------------------------------------------

# _vendor_cytoscape.py CYTOSCAPE_VERSION/CYTOSCAPE_SHA256: the vendored-library provenance
# constants (decision overview-0001), read only by fransys-overview's own test_vendor.py.
_.CYTOSCAPE_VERSION  # TESTS fransys-overview/tests/test_vendor.py:37
_.CYTOSCAPE_SHA256  # TESTS fransys-overview/tests/test_vendor.py:28

# --- DEL-4: record fields and enum members whose only reader was a deleted stored kind --------
# The records stay (Page, PowerSymbol, LayoutSheet, Membership, the readability rows); their
# fields are read generically. A cleanup round trims the fields no consumer reads.
_.symbols  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.wire_crossings  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.wire_bends  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.wire_length_g  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.struck_labels  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.text_overlaps  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.loose  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.marker_padding  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.pin_x  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.pin_y  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.orientation  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.sheet_kind  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.connector_housing  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.BLOCK  # TESTS fransys-model/tests/layout/test_membership.py:44
_.REFERENCE  # TESTS fransys-model/tests/layout/test_membership.py:157


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
_.limits  # TESTS fransys-author/tests/surface/test_coverage_facts.py:89

# CT5-1C: stub_a and stub_b of layout/cable_results.py CoreWire; engines/cable/write writes
# them, render draws a stub as the wire's own end segment. Vulture runs per package, so a
# model field read only in layout or render stays here (CT5-2, layout-0141).
_.stub_a  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.stub_b  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.stub_of  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
# CT5-2: the cable drawing's fields and enum members, read by render's cable_blocks
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
_.pin_edges  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.reference_plan  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.reroute_rounds  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.row_footprint  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
_.row_group  # FIELDS fransys-layout/src/fransys_layout/core/jsonform.py:33
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
_.DIGITAL_IN  # OTHER fransys-model/src/fransys_model/derive/rows_plc.py:111
_.DIGITAL_OUT  # OTHER fransys-model/src/fransys_model/derive/rows_plc.py:112
_.ANALOGUE_IN  # OTHER fransys-model/src/fransys_model/derive/rows_plc.py:113
_.ANALOGUE_OUT  # OTHER fransys-model/src/fransys_model/derive/rows_plc.py:114
_.lane_heads  # OTHER fransys-overview/src/fransys_overview/_data.py:182
_.pdf  # FIELDS packages/fransys/src/fransys/settings.py:46
_.look  # FIELDS packages/fransys/src/fransys/settings.py:47
# `fransys_layout/drawing.py`: `Style`, `Sheet` and `DrawnWire` fields, read by render `draw.svg`
# (render-0022) or by their tests (DRAWING-VALUE A1/A2; SETTINGS-A2 replaces the Style numbers).
_.style  # OTHER fransys-render/src/fransys_render/draw.py:143
_.family  # OTHER fransys-render/src/fransys_render/draw.py:68
_.dashes  # OTHER fransys-render/src/fransys_render/draw.py:94
_.line_thin_mm  # OTHER fransys-render/src/fransys_render/draw.py:82
_.line_thick_mm  # OTHER fransys-render/src/fransys_render/draw.py:82
_.muted_colour  # OTHER fransys-render/src/fransys_render/draw.py:135
_.module_mm  # OTHER fransys-render/src/fransys_render/draw.py:40
_.g_per_module  # OTHER fransys-render/src/fransys_render/draw.py:40
_.frame_key  # TESTS fransys-layout/tests/test_drawing.py:60
_.dash_mm  # TESTS fransys-layout/tests/test_drawing.py:45
_.tints  # TESTS fransys-layout/tests/test_drawing.py:44
_.line_rule_mm  # TESTS fransys-layout/tests/test_drawing.py:50
_.junction_dot_mm  # TESTS fransys-layout/tests/test_drawing.py:51
_.width_mm  # TESTS fransys-el/tests/test_style.py:39
_.height_mm  # OTHER fransys-render/src/fransys_render/draw.py:67
# fransys_model/layout: DrawnText.turned and the Corner members, read by the Label mapping
_.turned  # FIELDS packages/fransys-model/src/fransys_model/layout/drawn_results.py:103
_.NW  # FIELDS packages/fransys-model/src/fransys_model/layout/enums.py:131
_.NE  # FIELDS packages/fransys-model/src/fransys_model/layout/enums.py:132
_.SW  # FIELDS packages/fransys-model/src/fransys_model/layout/enums.py:133
_.SE  # FIELDS packages/fransys-model/src/fransys_model/layout/enums.py:134
_.no_cells  # FIELDS packages/fransys-model/src/fransys_model/derive/rows_footprints.py:29
_.nc_cells  # FIELDS packages/fransys-model/src/fransys_model/derive/rows_footprints.py:30
# KIT-FACTS: @value fields of derive/rows_device_chains.py, rows_pin_views.py and rows_undrawn.py,
# read by fransys_layout's read package and generically via dataclasses.fields() (FIELDS).
_.fed  # FIELDS fransys-model/src/fransys_model/derive/rows_device_chains.py:35
_.feeder  # FIELDS fransys-model/src/fransys_model/derive/rows_device_chains.py:36
_.fed  # FIELDS fransys-model/src/fransys_model/derive/rows_device_chains.py:43
_.feeder  # FIELDS fransys-model/src/fransys_model/derive/rows_device_chains.py:44
_.elsewhere  # FIELDS fransys-model/src/fransys_model/derive/rows_pin_views.py:23
_.idle  # FIELDS fransys-model/src/fransys_model/derive/rows_undrawn.py:18
_.elsewhere  # FIELDS fransys-model/src/fransys_model/derive/rows_undrawn.py:19
_.L1  # TESTS fransys-author/tests/surface/test_supplies.py:74
_.L2  # TESTS fransys-author/tests/surface/test_supplies.py:74
_.L3  # TESTS fransys-author/tests/surface/test_supplies.py:74
_.letter_rule  # OTHER fransys-parts/src/fransys_parts/lint.py:218
_.BLOCK  # TESTS fransys-model/tests/layout/test_membership.py:41
_.sheet_kind  # FIELDS fransys-model/src/fransys_model/layout/sheets.py:23

# DEL-12: the old engine was the only reader of these two model fields; each is dead now. The
# citation is the field itself. Delete the fields with DEL-3 (model change, not this lane).
_.port_pairs  # OTHER fransys-model/src/fransys_model/derive/pairing.py:28
_.pitch  # OTHER fransys-model/src/fransys_model/layout/cable_results.py:35
# --- fransys: old SYMBOL_PORT_MISSING finding, kept for GAP-FLIP-203; DEL-12 cut its only test
_.symbol_port_missing_finding  # OTHER fransys/src/fransys/_layout_need.py:69

# --- FAN-2 (R338): fields and members whose only reader was the deleted old engine --------
# The records and values stay (Profile, Chain hints, SymbolChoice, the text-placement options);
# their fields are read generically. A cleanup round trims the fields no consumer reads.
_.column_gap  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.row_gap  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.row_spacing  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.route_margin  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.beside  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.port_map  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.steps  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.mirror  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.priority  # FIELDS fransys-kernel/src/fransys_kernel/schema.py:37
_.route_turn_penalty  # OTHER fransys-layout/src/fransys_layout/engines/cable/read/facts.py:180
_.route_crossing_penalty  # OTHER fransys-layout/src/fransys_layout/engines/cable/read/facts.py:181
_.stretch  # OTHER fransys-render/src/fransys_render/draw.py:107
_.leads  # OTHER fransys-render/src/fransys_render/draw.py:137
_.MARKING  # OTHER fransys-el/src/fransys_el/texts.py:33
_.CROSS_REFERENCE  # OTHER fransys-el/src/fransys_el/texts.py:41
_.HARNESS_LINE  # OTHER fransys-el/src/fransys_el/texts.py:53
