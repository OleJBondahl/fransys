# Moving to 0.14

This page lists every `fr.derive` name 0.14 removes, and what to use instead.
`fr.derive` now holds the names a consumer needs to read a model, and every one has a guide entry. The rest stay in the workspace for layout, render and the outputs. A consumer script that used a removed name changes as below.

## Removed names

| removed | use instead | why |
|---|---|---|
| `location_node_designation` | `node_designation` | It prints any aspect node's signed path, `+` or `=`, so the name no longer says location. |
| `number`, `allocate_plc` | `fr.build(d)` | They are passes; the facade runs them. |
| `ext_usage`, `ExtUsage` | none | A migration diagnostic with no consumer use. |
| `overview_graph`, `OverviewGraph`, `OverviewLink`, `OverviewLinkKind`, `OverviewNode`, `OverviewPort`, `OverviewSignal` | none; use `fr.derive.items`, `ports` and `conductors` | The overview output is being reshaped; its graph types are not stable. |
| `box_pairs`, `BoxPair`, `draws_as_line`, `supply_share`, `connector_box_lines`, `connector_at_line_end`, `line_conductors`, `line_stub_line`, `check_side_hints` | the model records: `fr.derive.conductors`, `harness_line_ends`, `line_designation` | Drawing helpers. The model records hold the facts they read. |
| `black_box_unit`, `drawing_set_is_replica_only`, `is_black_box_item`, `schematic_functions`, `own_nodes`, `enclosing_boards`, `first_leg`, `rail_pairs`, `link_state`, `LinkState`, `changeover_throws`, `Throws`, `owned_contacts`, `Indexes`, `build_indexes` | none, or `fr.derive.functions` and `aspect_nodes` | Layout internals. |
| `profile_of` | read the `layout.profile` table of the model | The profile is a record. |
| `physical_nets`, `unused_terminals` | `fr.derive.net_of`, `fr.derive.port_is_unused` | One net, one port at a time. |
| `terminal_strips` | `fr.derive.terminal_items`, `fr.derive.unit_strips` | The kept pair covers a model and a unit. |
| `unit_items`, `unit_subtree` | filter `fr.derive.items` by `item.unit` | A plain filter of a kept table. |
| `current_revision`, `same_version` | `fr.derive.revision_history`, `fr.derive.release_order` | Compare the ordered pairs. |
| `document_unit` | `document.unit` | A field of the document record. |
| `list_context` | pass the location node you want to a row function's `context` | A value the caller passes. |
| `connector_label`, `connector_segments`, `designation_holder`, `takes_parents_designation`, `is_own_unit_root`, `is_sole_unit_root`, `standalone` | `fr.derive.item_designation`, `printed_designation` | The designation functions print the text; the helpers behind them are internal. |
| `core_colour`, `conductors_on_item` | `fr.derive.cable_rows`, `fr.derive.conductors` | The rows carry the colour; the conductors table carries the rest. |
| `cell_parts`, `cell_text`, `column_rows`, `column_values`, `pin_lines` | read the fields of a row and order them by the `*_COLUMNS` constant | Output formatting. |
