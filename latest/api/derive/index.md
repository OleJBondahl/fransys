# `fransys_model.derive`

## Functions

### actuated_group

```python
def actuated_group(model: Model, function: Id[Function]) -> tuple[Id[Function], ...]
```

The switches the actuator of `function` moves, in list order; empty with no operator.

### actuator_each_contact

```python
def actuator_each_contact(model: Model, unit: Id[Unit] | None) -> bool
```

Whether `unit`'s profile draws the actuator on every contact (the default).

### allocate_plc

```python
def allocate_plc(model: Model) -> tuple[Model, tuple[Finding, ...]]
```

Bind every `plc_request` facet to a free channel of matching `SignalType`.

Wiring first: a request whose ports share a physical net with channel functions binds to the
first free one in serving order whose net holds no other request's function, in any unit. The
rest are served by the first unit on their chain (item's unit, then each `Unit.parent`, top
level last) that declares a channel of their signal type, from one free queue per (unit, signal
type). Siblings never share and nothing reaches downward. If that unit's channels are all taken,
or the chain declares none, the request gets `PLC_REQUEST_UNSERVABLE` with no fall-through.
Requests serve by `(priority, requesting Function.key, Function.id)`, channels by `(rack
Item.key, module position, module Item.key, plc_channel.channel, Function.id)`. A request
already carrying a `plc_binding` is skipped. Returns the model with one `plc_binding` per
request served and one finding per request left (`PLC_CHANNEL_CONTESTED` once per channel wired
to two or more kind-matched requests, which bind nothing); a model with nothing to bind comes
back as the same object.

### aspect_nodes

```python
def aspect_nodes(model: Model) -> frozendict[Id[AspectNode], AspectNode]
```

Return every `AspectNode` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `AspectNode` in `model`, keyed by id; the model's own table, so nothing is
    copied. Empty when the model holds none.

### bar_items

```python
def bar_items(model: Model) -> frozenset[Id[Item]]
```

Every item that holds a bar function, built once per model digest.

### black_box_unit

```python
def black_box_unit(model: Model, unit: Id[Unit], set_unit: Id[Unit] | None) -> Id[Unit]
```

The unit directly in `set_unit` that holds `unit`: the black box its page draws.

`unit` itself when no ancestor stands directly in `set_unit`; `set_unit` `None` is the top.

### board_netlist

```python
def board_netlist(model: Model, board: Id[Item]) -> BoardNetlist
```

`board`'s parts, footprints and nets as one `BoardNetlist`.

Parts are the footprinted descendants of `board`. Nets join its internal conductors and its
declared nets, never `Mate`s; part designations are relative to `board`.

Args:
    model: The model to read.
    board: The item whose netlist is built.

Returns:
    A `BoardNetlist` (defined in `derive.rows`) for `board`.

Raises:
    SchemaError: `board` is not an item of `model`, or it or a listed item has no designation.

### board_pins

```python
def board_pins(model: Model, board: Id[Item]) -> BoardPins
```

`board_netlist`'s nets with each pin resolved once, and the open pins of its parts.

A pin of an item with no part row takes its board-relative designation. `unconnected` lists,
per part in `board_netlist` order, every port of its functions whose `ref:pad` is in no net.

Args:
    model: The model to read.
    board: The item whose netlist is built.

Returns:
    A `BoardPins` (defined in `derive.rows_netlist`).

Raises:
    SchemaError: as `board_netlist`.

### boards

```python
def boards(model: Model) -> tuple[Id[Item], ...]
```

Every item whose `Part` carries a `pcb` facet, in designation order.

`PcbFacet.subject` is a `Part`, not an item: an item is a board when its own `part` is one
that carries the facet. Shared by `fransys`'s export enumeration
and the pdf document contents, so the two never disagree about what a board is.

Args:
    model: The model to read.

Returns:
    Every board item's id, by natural designation, then id.

### bom_lines

```python
def bom_lines(model: Model, scope: Id[Item] | Id[AspectNode] | Id[Unit] | TopLevelScope | None=None, *, without: Collection[Id[Item]]=()) -> tuple[BomLine, ...]
```

One `BomLine` per `Part` of an installed, not external item, by `(mpn, revision, part)`.

An item with no `part` has no line; a crimp contact part has one, counted per used pin.
`designations` are `printed_designation`s; `revision` is `""` on a part line. `scope` narrows:

- `None` (default): every installed item of the model, no unit lines.
- `Id[Item]`: that item and its descendants; `Id[AspectNode]`: the items at or below it.
- `Id[Unit]`: its own items and a `part=None` line per nested unit; its sole root prints none.
- `TOP_LEVEL`: items with no unit, plus one line per top-level unit, the same way.
- `without`: items the `None`, item and node scopes leave out (a document's undrawn harness).

Raises:
    SchemaError: `scope` is none of the above kinds, names a unit the model does not hold,
        or a counted item has no designation.

### bom_sort_key

```python
def bom_sort_key(model: Model, item: Id[Item]) -> tuple[int, NaturalKey, str, int]
```

Sort key for one item within a `bom_lines` line's `designations`.

A terminal with a parent sorts `(0, its strip's item_designation, its own group, its own
index)`: by strip, then group, then index. `group`/`index` come straight off the
`TerminalFacet`, never re-parsed from rendered text, so `"L1:10"` sorts after `"L1:2"`. Any
other item sorts
`(1, natural_key(its own item_designation), "", 0)`: digit runs by value (`-K2`, `-K10`).

Raises:
    SchemaError: as `item_designation`.

### boundaries

```python
def boundaries(model: Model) -> frozendict[Id[Boundary], Boundary]
```

Return every `Boundary` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `Boundary` in `model`, keyed by id; the model's own table, so nothing is
    copied. Empty when the model holds none.

### boundary

```python
def boundary(model: Model, unit: Id[Unit]) -> tuple[Id[Function], ...]
```

The functions that are part of `unit`'s interface, in `Id` order.

One function may be `unit`'s boundary through more than one `Boundary` record; it is
listed once.

Raises:
    SchemaError: `unit` is not a unit of `model`.

### boundary_operating

```python
def boundary_operating(model: Model, boundary: Id[Boundary]) -> Operating | None
```

The operating envelope a unit states on `boundary`; `None` with no facet or none in it.

Args:
    model: The model to read.
    boundary: The boundary whose stated operating envelope is looked up.

Returns:
    The `Operating` `boundary`'s unit states, or `None` with no facet or none in it.

### boundary_rating

```python
def boundary_rating(model: Model, boundary: Id[Boundary]) -> Rating | None
```

The rating a unit states on `boundary`; `None` with no facet or no rating in it.

No fallback: the function's own part rating is a separate source, read through
`function_rating`.

Args:
    model: The model to read.
    boundary: The boundary whose stated rating is looked up.

Returns:
    The `Rating` `boundary`'s unit states, or `None` with no facet or no rating in it.

### box_pairs

```python
def box_pairs(model: Model, drawn: Collection[Id[Port]] | None=None) -> dict[Id[Function], BoxPair]
```

Each function wired point to point to one function of another item, and the port pairs.

Every port of the function has a two-port net to a port of that one function, one to one, and
that function has no other port. Two partners, a split group, a third member or a net of
three ports leave the function out. The relation is symmetric; which box is fed is layout's
reading of the box sides. With `drawn`, only the ports in it count on either
side: a port the profile leaves off the page is no member of its function.

### bridge_piece_key

```python
def bridge_piece_key(piece: str) -> str
```

The key of a Bridge mark piece in the map render hands pdf; one spelling for both.

### build_indexes

```python
def build_indexes(model: Model) -> Indexes
```

Build every index together off `model`.

Cached on `model.digest`, holding the last few results: two calls with an equal digest
return the identical `Indexes` object, so a caller never has to thread it through by hand.
The digest ignores origins and aliases, which no index reads, and an `Indexes` holds only
ids, so equal digests mean equal results. Identity is guaranteed within one thread.

### bundle_of

```python
def bundle_of(model: Model, port: Id[Port]) -> tuple[Id[Port], int] | None
```

The `(bundle id, pole index)` of the physical net of `port`, or `None` when in no bundle.

### cable_block_sizes

```python
def cable_block_sizes(model: Model) -> dict[str, CableBlockSize]
```

Each laid-out cable block's size in G and sheet module, by `cable_block_key`.

### cable_blocks

```python
def cable_blocks(model: Model, document: Id[Document], cables: tuple[HarnessCable, ...]) -> tuple[CableBlockRef, ...]
```

The document's blocks, one per `cable_subject`, each at its first cable's place.

A document reads absolutely unless it is a unit document, whose reading is its unit. A
harness with wires gets its one block too (`DocumentScope.harnesses`), after the cable blocks.

`document` is the document's id.

### cable_items

```python
def cable_items(model: Model) -> frozenset[Id[Item]]
```

Every item whose part carries a `cable_product` facet, built once per digest.

The one selection rule behind `is_cable`: an item is in this set exactly when its `Item.part`
is one of the parts a `CableProductFacet` names as `subject`. Reads nothing else -- not
`category`, not the item's own `CableFacet` (installed length only).

Args:
    model: The model to read.

Returns:
    Every item id whose part carries a `cable_product` facet.

### cable_list_rows

```python
def cable_list_rows(model: Model, *, unit: Id[Unit] | None=None) -> tuple[CableListRow, ...]
```

One `CableListRow` per cable of one reading: `unit`'s own, or the top-level ones.

`unit=None`: every cable item (`is_cable`) with no unit, harness cables included. A unit: the
cables whose own `Item.unit` is `unit`, read with its facts. Rows sort by `(designation, id)`.
`from_label` is the first end's `designation`; `to_label` the others', joined by ", ".

Args:
    model: The frozen model to read.
    unit: The unit whose own cables to list; `None` is the top-level ones.

Raises:
    SchemaError: `unit` is no unit, or an item has no designation.

### cable_list_rows_of

```python
def cable_list_rows_of(model: Model, cables: set[Id[Item]]) -> tuple[CableListRow, ...]
```

The `CableListRow`s of exactly `cables`, each read in its own unit, in list order.

### cable_rows

```python
def cable_rows(model: Model, cable: Id[Item], *, unit: Id[Unit] | None=None) -> tuple[CableRow, ...]
```

One `CableRow` per core of `cable`, sorted by `(core.index, conductor id)`.

Cores are the `core`-kind conductors naming `cable` as `carrier`; the colour is `core_colour`'s.

Args:
    model: The frozen model to read.
    cable: The cable item whose cores to list.
    unit: The unit whose own document draws the cable, keyword-only; `None` is the whole model.

Returns:
    One `CableRow` per core of `cable`, sorted.

Raises:
    SchemaError: `cable` is no item, an end has no designation, or `unit` is no unit of `model`.

### cable_runs

```python
def cable_runs(blocks: Iterable[CableBlockRef]) -> tuple[CableRun, ...]
```

`blocks` grouped by part number, parts sorted by it, blocks in their given order.

Blocks with no part number form the last run, headed `NO_PART`.

### cable_title

```python
def cable_title(cable: HarnessCable) -> str
```

The cable's printed title: its designation, then its MPN when it has one.

Args:
    cable: The cable's own row to render.

Returns:
    The designation, a space, and the MPN when `cable.mpn` is set; the designation alone
    otherwise.

### cell_parts

```python
def cell_parts(cell: tuple[object, ...]) -> tuple[str, ...]
```

The non-empty text of each part of a tuple-valued list cell; a nested tuple is one part.

Args:
    cell: A list cell's raw tuple value.

Returns:
    `cell_text` of each part, empty ones left out.

### cell_text

```python
def cell_text(cell: object) -> str
```

`cell` as the text of one list cell: `None` empty, an enum its value, a tuple its parts.

A tuple's parts are joined by `CELL_SEPARATOR`, empty parts left out (`cell_parts`).

Args:
    cell: A row field's raw value.

Returns:
    The text one list cell prints for it.

### changeover_functions

```python
def changeover_functions(model: Model) -> set[tuple[Id[Part], str]]
```

The (part, name) of every changeover function template (its kind is the one fact).

### changeover_throws

```python
def changeover_throws(model: Model, function: Id[Function]) -> tuple[Throws, ...]
```

The poles of the `CONTACT_CO` function `function`, one `Throws` per common port.

A common port gets a `Throws` when a `switched` internal link joins it to a `BREAK` or `MAKE`
port of the same function. Roles come from the part's `PortTemplate`s, never a pin name.
Sorted by `common`; it never raises. Cached on `model.digest`.

Args:
    model: The model to read.
    function: The `CONTACT_CO` function whose poles are found.

Returns:
    One `Throws` per common port, sorted by `common`; empty for a function that is not a
    changeover, is not in `model`, or whose ports carry no `COMMON`/`BREAK`/`MAKE` roles.

### channel_pins

```python
def channel_pins(model: Model) -> frozenset[Id[Port]]
```

The pins that are a channel: a PLC channel template's, and every pin of a part-less device.

The second case is an external item with no part: its channels are unknown, so each pin is one.

### check_side_hints

```python
def check_side_hints(model: Model) -> tuple[Finding, ...]
```

Warn once per side hint whose interface stands at no harness line's end: it does nothing.

### child_items

```python
def child_items(model: Model, item: Id[Item]) -> tuple[Id[Item], ...]
```

The ids of `item`'s children by `Item.parent`, in `Id` order; empty for a leaf.

### column_label

```python
def column_label(field: str) -> str
```

`field` as a table header: underscores to spaces, first letter upper-cased.

### column_rows

```python
def column_rows(records: Iterable[object], columns: tuple[str, ...]) -> list[tuple[object, ...]]
```

One `column_values` line per record, in the order given.

Args:
    records: The rows to read, in the order to print them.
    columns: The field names to read, in print order.

Returns:
    One `column_values` tuple per record, in `records`' order.

### column_values

```python
def column_values(record: object, columns: tuple[str, ...]) -> tuple[object, ...]
```

`record`'s fields named by `columns`, in that order.

Args:
    record: A row (or a `ConnectorPin`) to read fields of.
    columns: The field names to read, in print order.

Returns:
    `record`'s value for each name in `columns`, in that order.

### conductor_role

```python
def conductor_role(model: Model, conductor: Id[Conductor]) -> ConductorRole
```

The role of a conductor: its kind's row.

### conductors

```python
def conductors(model: Model) -> frozendict[Id[Conductor], Conductor]
```

Return every `Conductor` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `Conductor` in `model`, keyed by id; the model's own table, so nothing is
    copied. Empty when the model holds none.

### conductors_on_item

```python
def conductors_on_item(model: Model, item: Id[Item]) -> frozendict[Id[Item], frozendict[PortRole, tuple[Id[Conductor], ...]]]
```

`item`'s conductors, grouped by terminal child item and then by port role.

Holds only the `terminal`-facet children with a conductor and, per child, only the roles with
one; a conductor with both ends on one child is listed once per role it touches.

Args:
    model: The model to read.
    item: The item whose terminal children's conductors are grouped.

Returns:
    `item`'s terminal children, each mapped to its conductors by `PortRole`.

Raises:
    SchemaError: `item` is not an item of `model`.

### connector_at_line_end

```python
def connector_at_line_end(model: Model, function: Id[Function]) -> bool
```

Whether `function` is a plug, the function a plug mates, or a fan-out pin's function.

Read from `harness_line_ends` of the lines `draws_as_line` holds, and nothing else. The box
rule, the middle-outline edge rule and the side hint's WARNING call it and never ask again. A
connector at no line gives `False`.

### connector_box_lines

```python
def connector_box_lines(model: Model, function: Id[Function], *, unit: Id[Unit] | None=None) -> tuple[str, ...]
```

The lines of `function`'s connector box: its designation, its part line, its landed pins.

The designation is `connector_designation` in `unit`'s context. The part line is the MPN, only
when every function of the item is a connector function. A unit boundary then prints the
`port_designation` of each pin a conductor lands on; any other connector prints none. A line
prints once however many ports or conductors reach it.

### connector_facets

```python
def connector_facets(model: Model) -> frozendict[Id[FunctionTemplate], ConnectorFacet]
```

Every `connector` facet by the function template it describes.

### connector_item

```python
def connector_item(model: Model, connector: Id[Function]) -> Id[Item]
```

The item that owns the connector function `connector`.

Raises:
    SchemaError: `connector` is not a function of `model`.

### connector_items

```python
def connector_items(model: Model) -> tuple[Id[Item], ...]
```

Every item with a connector function of a `connector`-faceted template, designation order.

The items a connector table can be headed by; `unit_connector_items` keeps a unit's own.

### connector_label

```python
def connector_label(marking: str | None, name: str) -> str | None
```

The label a connector function prints, `None` for none: the one home of that rule.

`marking` is the `connector` facet's (or the part file's) `marking`, read like `Port.marking`:
`None` means the function's own `name` is the label (`None` again for an empty name), and
`""` means no label (a shell or an earth stud, whose pins print under the item). A function
that is no connector has no label either: the caller does not ask. `_connector_label` here
and the part lint call it after reading their own inputs.

Args:
    marking: The connector facet's (or part file's) `marking`, or `None` for unset.
    name: The function's own name, the fallback label when `marking` is `None`.

Returns:
    The label to print, or `None` for none.

### connector_rows

```python
def connector_rows(model: Model, board: Id[Item], *, unit: Id[Unit] | None=None, context: Id[AspectNode] | None=None) -> tuple[ConnectorRow, ...]
```

One `ConnectorRow` per connector of `board`, with its pins, nets and mate.

A connector is a `connector`-kind `Function` of `board` or a descendant whose template carries a
`connector` facet. `designation` is `connector_designation`: the item's own designation, or
`<item designation>-<label>` when the item has two or more connector functions. Rows sort by
`(designation, connector id)`. `mate` is the other end of a `Mate`; a pin's `mate_port` is the
port of equal name on it, and its `net` the declared net listing its port. `pins` sort by
marking, digits first by value. `context` (default `None`, full paths) is the location the list
prints against. `unit` is the unit whose document prints it: inside it reads unit-relative, and
for a nested `unit` a mate outside its subtree prints `None`; `context` is ignored once `unit`
has one.

Raises:
    SchemaError: `board` is not an item of `model`, or an item shown has no designation.

### connector_rows_of

```python
def connector_rows_of(model: Model, item_ids: Collection[Id[Item]], *, unit: Id[Unit] | None=None, context: Id[AspectNode] | None=None) -> tuple[ConnectorRow, ...]
```

One `ConnectorRow` per connector function of exactly the items `item_ids`, sorted.

`connector_rows` is this over a board and its descendants; the rest is its contract.

### connector_segments

```python
def connector_segments(labels: Iterable[str | None]) -> tuple[str, ...]
```

The segment each function prints behind its item's designation, in order.

`labels` holds the connector label of each function of one item: `""` or `None` for none
(a function that is no connector, or a shell that says `marking=""`). A device prints its
connectors as sub-parts (`-U2-X1:1`) when two or more of its functions have a label, so that
two pins named alike never print one text: a labelled function then gives `-<label>`, an
unlabelled one `""`. With no label, or one, every segment is `""` (`-J1:1`). This is the
one place the rule is decided: `connector_segment` and the part lint both call it.

Args:
    labels: Each function's connector label, in index order, `""` or `None` for none.

Returns:
    Each function's printed segment, in the same order: `-<label>` or `""`.

### contact_list_key

```python
def contact_list_key(model: Model, function: Id[Function]) -> ListKey
```

The key a contact list sorts its contacts by: a 3-pole-plus first, then the first entry.

The caller breaks a tie by the function id.

### contacts_not_drawn

```python
def contacts_not_drawn(model: Model) -> Counter[Id[Page]]
```

The contact-image entries that print N/A, by the page of the coil's image.

An entry is a spare contact when it names no partner port (`image_entries`).

### contents_rows

```python
def contents_rows(cables: tuple[HarnessCable, ...]) -> tuple[ContentsRow, ...]
```

One `ContentsRow` per cable, in the order given.

Pure reshaping of `HarnessCable`s a caller already built (`harness_cables_for`,
`top_level_cables`, `unit_cables`): no `Model` parameter, no re-sort -- the caller's own
order, already sorted where it needs to be, is kept. `ends` is every end's `designation`,
blanks dropped, joined by an en dash (moved here verbatim from pdf's own
copy).

Args:
    cables: The `HarnessCable`s to reshape, in the order to keep.

Returns:
    One `ContentsRow` per cable, same order, same length.

### core_colour

```python
def core_colour(model: Model, conductor: Id[Conductor]) -> str
```

The colour of core `conductor`: its carrier's `core_colours[index - 1]`.

The one reader of a core's colour: the facet holds only the index, and the colour is the cable
product's fact. `cable_rows`, the harness rows and wireviz read it here.

Args:
    model: The frozen model to read.
    conductor: The core conductor whose colour to render.

Returns:
    The core's colour, an IEC 60757 code (or code pair); "" for a core past its product.

Raises:
    SchemaError: `conductor` is not a core of a cable, or has no `core` facet.

### core_list_rows

```python
def core_list_rows(model: Model, *, unit: Id[Unit] | None=None) -> tuple[CoreListRow, ...]
```

One `CoreListRow` per core of every cable `cable_list_rows` lists, in its order.

Cores sort by number within a cable. The ends are `cable_rows`' and `open_core_rows`' own texts.

Args:
    model: The frozen model to read.
    unit: The unit whose own cables to list; `None` is the top-level ones.

Raises:
    SchemaError: `unit` is no unit, or an item has no designation.

### cores_text

```python
def cores_text(core_count: int | None, pairs: int | None) -> str
```

The cable list's Cores cell: `2x2` for a paired product, the count otherwise.

### crosses_unit

```python
def crosses_unit(model: Model, one: Id[Item], other: Id[Item]) -> bool
```

Whether the two items lie in different units, strictly.

A sub-unit is a different unit from its parent, so a nested unit's item crosses against
the parent's. An item in no unit differs from one in a unit, and equals another in none.

### csv_name

```python
def csv_name(label: str) -> str
```

A heading as its CSV header: spaces to `_`, lower-cased (`Side A` is `side_a`).

### current_chains

```python
def current_chains(model: Model) -> tuple[CurrentChain, ...]
```

The rated current paths of `model` grouped by loop, and what bounds each.

The result is `facts.current.chains.chains_unordered`, whose module docstring holds the graph
and the law, with each chain's positions run in path order from its supply end.
A chain's positions are edges of a block; its end ports are the nodes one
position touches. The supply end is the end with the best `port_potential_rank`; with no
ranked end, or a tie, the lower designation text. The positions follow a walk from it.

A block that is no path (a loop with no end, a star, a position in parallel) runs by a
depth-first walk from its best end, or its best node when it has none; at a fork the
position with the lower designation text goes first, function ids only on equal texts.
Chains sort by their ordered positions'
functions, so the result is the same for any record order. Cached
on `model.digest`, the last few results of `chain_blocks`.

### current_revision

```python
def current_revision(model: Model, release: Id[UnitRelease] | None=None) -> Revision | None
```

The history entry that is `release`'s current revision, or the project's when `None`.

Its own `(version, revision)` equals the release's (the `Project`'s for the project): the
current revision, not merely the latest entry. `None` when no entry matches, and for the
project when the model has no `Project` (there is no current revision to miss). The date a
title block, the PDF metadata and the PDF's embedded timestamp print is this entry's `date`.
Pure: `REVISION_CURRENT_MISSING` reports the gap.

Raises:
    SchemaError: `release` is not `None` and names no `UnitRelease` of `model`.

### cut_to_width

```python
def cut_to_width(text: str, *, size_mm: float, bold: bool=False, width_mm: float) -> tuple[str, bool]
```

`(shown, was_cut)`: `text` if it fits, else cut by character plus `…`.

### designation_holder

```python
def designation_holder(model: Model, item: Id[Item], *, held_switches: bool=True) -> Id[Item]
```

The item whose own label `item` prints: `item` itself, or the top of its accessory chain.

Walks `parent` while `takes_parents_designation` holds; a parent cycle ends the walk.

Args:
    model: The frozen model to read.
    item: The item whose label holder to find.
    held_switches: as `takes_parents_designation`.

Returns:
    `item` itself, or the topmost accessory ancestor whose label `item` prints.

### designation_list

```python
def designation_list(model: Model, *, unit: Id[Unit] | None=None) -> tuple[DesignationRow, ...]
```

One `DesignationRow` per `Item`, terminals included, sorted by `(designation, id)`.

`designation` is `printed_designation` (`"-X1:L1:1"`, `"-K1"`); `reference` is
`reference_designation`. An accessory (`takes_parents_designation`) has no row.

Args:
    model: The frozen model to read.
    unit: Keep only rows of this unit, keyword-only; its sole root has no row.

Returns:
    One `DesignationRow` per item, sorted by `(designation, id)`.

Raises:
    SchemaError: an item has no designation, or `unit` names no unit of `model`.

### designation_moves

```python
def designation_moves(source: NumberingPins, current: NumberingPins) -> tuple[DesignationMove, ...]
```

Every pin still matched (as in `gone_or_moved`) whose current own text now differs.

`own_designation_or_none` reads the authored tag first, as `NumberingItem.text` does.

### diagram_sheet_order_key

```python
def diagram_sheet_order_key(sheet: DiagramSheet) -> tuple[str, int]
```

Sort key of a sheet: its reading's render id (`""` for the absolute one), then number.

### diagram_sheets

```python
def diagram_sheets(model: Model, document: Id[Document]) -> tuple[DiagramSheet, ...]
```

The diagram sheets of the document's reading, by number: SYSTEM's absolute or its unit's.

`document` is the document's id.

### diff_marks

```python
def diff_marks(model: Model, rows: ViewRows, diff: ListingDiff) -> DiffViewMarks
```

The boxes and lines of the view `rows` that `diff` marks, and which rows marked.

A subject not drawn counts on its nearest drawn ancestor box. A line wins over a box for one
row; an added mark is never turned into a changed one. Boxes come first, by index.

### diff_rest

```python
def diff_rest(diff: ListingDiff, views: Sequence[DiffViewMarks]) -> tuple[DiffRest, ...]
```

The rows no view marked, once per kind and subject: removed, then added, then changed.

### document_bom_lines

```python
def document_bom_lines(model: Model, document: Id[Document]) -> tuple[BomLine, ...]
```

The BOM lines of `document`: its `bom_scope` less the harness items it does not draw.

`document` is the document's id.

### document_drawing_sets

```python
def document_drawing_sets(model: Model, document: Id[Document]) -> tuple[DrawingSet, ...]
```

The drawing sets of `document` by `number`: a location's top-level set, a unit's sets.

`document` is the document's id.

### document_export_name

```python
def document_export_name(model: Model, unit: Id[Unit] | None, record: Document) -> str
```

One document's PDF name, from its own subject, never its cover.

Unit subject (`record.unit`, or `record.unit_name` via `document_unit`): its own prefix.
Location, item, SYSTEM: the write scope's; empty prefix gives bare `<cover-stem>.pdf` here.

### document_facts

```python
def document_facts(model: Model, document: Id[Document]) -> tuple[str, str, str, str, str, str]
```

`project_facts`, or for a unit document the unit release's own, customer empty.

A unit document's author is the `created` of the unit's current revision.

`document` is the document's id.

### document_ids

```python
def document_ids(model: Model) -> tuple[Id[Document], ...]
```

Every document id, in table order.

### document_page_kinds

```python
def document_page_kinds(model: Model, document: Id[Document]) -> tuple[PageKind, ...]
```

The pages one document will contain, in order.

`page_kinds` of the document record's preset, additions and removals, with NOTES dropped
when the record has no notes text. `fransys_pdf.source` assembles exactly these pages.

### document_row

```python
def document_row(model: Model, document: Id[Document]) -> DocumentRow
```

The row of `document`; raises `KeyError` when the id names no document of `model`.

### document_rows

```python
def document_rows(model: Model) -> tuple[DocumentRow, ...]
```

One row per document, in `documents(model)` order.

### document_scope

```python
def document_scope(model: Model, document: Id[Document]) -> DocumentScope
```

What the document `document` (its id) selects from `model`: see `_document_scope`.

### document_sheet

```python
def document_sheet(model: Model, document: Id[Document], pages: tuple[PageKind, ...]) -> SheetRow
```

The paper of every page of `document`: `document_sheet_format` as a `SheetRow`.

### document_sheet_format

```python
def document_sheet_format(model: Model, document: Id[Document], pages: tuple[PageKind, ...]) -> SheetFormat
```

The paper of every page: the first drawing-set page's format, else the top profile's sheet.

A system document has none, so it takes the top profile's sheet, else the house one.

`document` is the document's id.

### document_sheets

```python
def document_sheets(model: Model, document: Id[Document]) -> DocumentSheets
```

Every page background of `document`, in page order, with its paper and sizes.

### document_sheets_of

```python
def document_sheets_of(model: Model) -> frozendict[Id[Document], DocumentSheets]
```

`document_sheets` of every `Document`, by id: the values render's sheets take.

### document_stems

```python
def document_stems(model: Model) -> tuple[tuple[Id[Document], str], ...]
```

Each document id with its name (the second part of its key), in table order.

### document_unit

```python
def document_unit(model: Model, document_id: Id[Document]) -> Id[Unit] | None
```

The unit of the document `document_id`: its `unit` when set, else its resolved `unit_name`.

The document's `unit` wins when set. Else, for a `unit_name`, the one id `units_named` finds;
`None` for zero or several matches (silently: a pure reader, never a validator) and `None`
when the document has neither field set. Never re-derives the match: `derive.facts.unit_names`
is its only home.

Example: `document_unit(model, document_id)` for a `Document(unit_name="relay-board", ...)`
returns the id of the one `Unit` instance of a release named `"relay-board"`, or `None` if
that name matches zero or several units.

### drawing_set_is_replica_only

```python
def drawing_set_is_replica_only(model: Model, drawing_set: Id[DrawingSet]) -> bool
```

Whether every function placed in `drawing_set` is black-box content, or none are placed.

`fransys_pdf`'s own question: a drawing set holding nothing but replicated black-box
boundaries has no home content of its own. Reads `is_black_box_item` for the item of every
function placed on one of `drawing_set`'s own pages, `drawing_set.unit` the comparison
unit; an empty drawing set gives `True`, since it has no placement that is not black-box
content.

Raises:
    SchemaError: `drawing_set` is not a `layout.drawing_set` of `model`.

### drawn_pages

```python
def drawn_pages(model: Model, document: Id[Document]) -> tuple[Page, ...]
```

The drawn pages of `document` in set then page order, replica-only sets skipped.

`document` is the document's id.

### draws_as_line

```python
def draws_as_line(model: Model, item: Id[Item]) -> bool
```

Whether `item`, a cable or a harness, draws as a harness line.

True when its line carries two or more conductors, cores and single wires together; a cable
on a harness answers for its harness. Layout, `connector_at_line_end` and `off_stub_text`
read it and never count again. Any other item, or an id that is no item, gives `False`.

### effective_placement

```python
def effective_placement(model: Model, item: Id[Item], aspect: Aspect) -> Id[AspectNode] | None
```

`item`'s own placement in `aspect`, else its nearest placed ancestor's, else `None`.

Walks `Item.parent`, cycle-safe; a tie in one aspect resolves to the smallest placement id.

Args:
    model: The model to read.
    item: The item whose effective placement is looked up.
    aspect: The aspect the placement is read in.

Returns:
    The `AspectNode` id of the own or inherited placement, or `None` when there is none.

Raises:
    SchemaError: `item` is not an item of `model`.

### enclosing_boards

```python
def enclosing_boards(model: Model, item: Id[Item]) -> tuple[Id[Item], ...]
```

`item` and its ancestors by `Item.parent` that carry a `pcb` facet, outermost first.

`item` itself is included when it is one. Cycle-safe: a `parent` cycle ends the walk.
The board parts come from the per-model unit index. The one predicate every board-membership
question in this repo answers: `derive.designation.designating_ancestors` (item
designations, excluding `item` itself; it walks boards and harnesses alike),
`checks.connectivity`'s board-realised rule (DESIGN
8: a net needs no conductors when one board is common to every port's item, intersecting
`frozenset(enclosing_boards(...))` over the net's ports), `derive.structure.
schematic_functions` (a function on or under a board item, board-relative walk), and
layout's board-internal connection rule -- one walk, so a drawn
connector can never fail to count as its own board's by one copy drifting from another.

### ends_without_jumpers

```python
def ends_without_jumpers(model: Model, row: TerminalRow) -> tuple[tuple[str, ...], tuple[str, ...]]
```

`row`'s (internal, external) ends without jumper partners, which the Bridge shows.

### error_count

```python
def error_count(findings: Iterable[Finding]) -> int
```

How many of `findings` are `ERROR`.

### errors_of

```python
def errors_of(findings: Iterable[Finding]) -> tuple[Finding, ...]
```

The `ERROR` findings of `findings`, in their own order.

### export_fragment

```python
def export_fragment(designation: str) -> str
```

`designation` as an export-name fragment: leading sign dropped, each `+`, `=`, `-` a `-`.

### export_name

```python
def export_name(model: Model, unit: Id[Unit] | None, extension: str, *, kind: str | None=None, fragment: str | None=None) -> str
```

`<prefix>[-<kind>][-<fragment>].<extension>`; an empty part is left out.

The one place prefix, kind and fragment are joined; the prefix is `export_prefix`.

### export_prefix

```python
def export_prefix(model: Model, unit: Id[Unit] | None) -> str
```

`unit`'s export name prefix, `<set name>-v<V>.<R>`.

A unit's prefix never depends on the Project; its version and revision come from its release.
The system's come from the Project; empty when `export_set_name` is.

### export_ref

```python
def export_ref(model: Model, item: Id[Item], unit: Id[Unit] | None) -> str
```

The name fragment of `item`'s per-item export in the folder of `unit`.

Unit-relative `printed_designation` through `export_fragment` (`-X2` gives `X2`): no parent
path. The unit's own root gives "" (bare `connectors.csv`): its own tag is never printed in
its set.

### export_set

```python
def export_set(model: Model, unit: Id[Unit] | None) -> tuple[ExportRow, ...]
```

Every export a write of `unit` makes (the whole model with `unit=None`), in write order.

The reports (and the overview for the whole model), one terminal CSV per strip, one connector
CSV per board, one WAGO XML per rack, then one PDF per document. Names are unplaced: the
caller puts CSV and XML into `data/`. Two rows may share a name; the caller refuses that.

### export_set_name

```python
def export_set_name(model: Model, unit: Id[Unit] | None) -> str
```

The name of `unit`'s export set.

A unit's set is its release's name, the same for every instance; a system write with no Project
has no prefix, which keeps today's names.

### ext_usage

```python
def ext_usage(model: Model) -> tuple[ExtUsage, ...]
```

One `ExtUsage` per `(record kind, top-level ext key)` over every namespace.

`subjects` are the record ids in id order, `count` their number, sorted by `(kind, key)`;
nested keys inside an `ext` value are not walked. It keeps `ext` a tracked escape hatch
rather than a silent second schema (design/kernel-records.md 5.3).

Args:
    model: The model to read.

Returns:
    One `ExtUsage` per `(record kind, top-level ext key)` found, sorted.

### external

```python
def external(model: Model, item: Id[Item]) -> bool
```

Whether `item` is external: it, or any item on its `parent` chain, has `external=True`.

The terminals of an external strip and the modules of an external rack are therefore
external without each carrying the flag. `installed` is a separate fact and is not read.
A `parent` cycle ends the walk (`validators.structure` reports it as `CONTAINMENT_CYCLE`).
Reads the per-model unit index.

Raises:
    SchemaError: `item` is not an item of `model`.

### field_devices

```python
def field_devices(model: Model) -> dict[Id[Item], Id[Unit]]
```

Each field device with the one unit all its connections land in.

The item is in no unit, stands as a box of its own at the system level, is not by others, and
has at least one connection; every far end sits in the same top-level unit. Nothing is authored.

### field_fold

```python
def field_fold(model: Model) -> tuple[FieldFold, ...]
```

The field devices of each unit as one box, "Field devices (n)", in unit box order.

`devices` are in box text order; `cables` are the cables joining them to the unit.

### field_printed

```python
def field_printed(text: str, *, room_mm: float, size_mm: float, bold: bool=False, shorter: tuple[str, ...]=()) -> tuple[str, bool, str]
```

`(base, fits, printed)` of a one-line cell: `printed` is the base, cut if it misses.

### finding_marks

```python
def finding_marks(model: Model, rows: ViewRows, findings: Sequence[Finding]) -> tuple[FindingMark, ...]
```

One `FindingMark` per box, then per line, of the view `rows` that `findings` name.

A subject not drawn on the view counts on its nearest drawn ancestor box; one with none is
left out. A finding holds its index in `findings` and counts once per box or line.

### first_fit_lanes

```python
def first_fit_lanes(spans: Sequence[tuple[int, int]]) -> tuple[int, ...]
```

Each `(first, last)` span's lane in the given order: the lowest lane free before `first`.

### first_leg

```python
def first_leg(model: Model, net: Id[Net], *, from_item: Id[Item]) -> Id[Port] | None
```

The port of `net` that is the first leg out of `from_item`.

The smallest port joined by one `Conductor` to `from_item`'s port on `net`, else the smallest.

Args:
    model: The model to read.
    net: The net whose first leg out of `from_item` is found.
    from_item: The item the leg starts from, keyword-only.

Returns:
    The port id, or `None` when `from_item` has no port on `net` or no candidate exists.

Raises:
    SchemaError: `net` is not a net, or `from_item` not an item, of `model`.

### fits

```python
def fits(text: str, *, size_mm: float, bold: bool=False, width_mm: float) -> bool
```

Whether `text` set at `size_mm` (bold or not) is no wider than `width_mm`.

### fold_level

```python
def fold_level(model: Model, unit: Id[Unit], opened: OverviewRef | None=None, *, fold: bool=True, strip: Id[Item] | None=None) -> FoldLevel
```

`unit`'s level folded to its function groups, or one group or the strips box opened.

With no `opened`: one box per group (its item, nested-unit and strip counts, and the
connections inside it), the strips with no group as "Terminal strips (n)", every other item and
nested unit as itself; one line per pair of boxes and kind with the connections lifted into it;
stubs folded by far end. A unit with fewer than two groups opens straight: its devices, as an
opened group is drawn, `folded` false. With a `GROUP`, its devices with a terminal that passes
wires through drawn as a line labelled with its strip, the rest as `strips` or boxes. With
`STRIPS`, the strips with no group as boxes, their wires to other boxes ending at stubs.
With `fold` false and no `opened`, a unit of several groups opens straight too: all its
devices, strips see-through (the all-devices view, O16). A `strip` of the level opened in it
stands as its terminals; the groups view opens none.
Raises `SchemaError` for a group or strips box the unit does not hold, or a `strip` it lacks.

### footprints

```python
def footprints(model: Model, function: Id[Function], *, body: Extent, slots: Mapping[str, Extent], tag_side: Side, text_height: int, step: int, pad: int, tiers: int=2, place_text: str='/99.99') -> Footprints
```

A function's footprint alone and in a strip row, in G, in the frame of its symbol's body.

Alone: body and slots, the tag slot as wide as the tag text, plus a coil's contact table
tiers below. In a strip row: body and the slots but the tag, which the strip prints once.

### frame_labels

```python
def frame_labels(columns: int, rows: int) -> FrameLabels
```

Column numbers `1..columns` and row letters `A..` for a frame of that many of each.

### function_designation

```python
def function_designation(model: Model, function: Id[Function], *, unit: Id[Unit] | None=None) -> str
```

Render `function` as its item's designation and its name (`JB1:J1`).

Args:
    model: The frozen model to read.
    function: The function to render.
    unit: The unit whose own document is being printed; `None` renders the whole-model form.

Returns:
    The function's printed label.

Raises:
    SchemaError: `function` is not a function of `model`, or its item has no designation.

### function_is_loose

```python
def function_is_loose(model: Model, function: Id[Function]) -> bool
```

Whether nothing is connected to `function`: it is drawn on no page.

A port is connected by a conductor or a net of two or more ports (a header join draws no
line); a mated function counts its mate's ports. One connected pole keeps its item's
same-kind functions.

### function_is_reached

```python
def function_is_reached(model: Model, function: Id[Function]) -> bool
```

Whether a wire inside `function`'s drawing, or a net, reaches one of its ports.

The drawing is its item's unit: a wire counts when its far end lies in that unit's subtree,
and at once for a top-level unit, whose leaving wire draws a stub. A bridge is no wire. A
function whose item is in no unit counts any wire. Layout draws a terminal only where this
holds, or a parent's black box needs it.

### function_is_unused

```python
def function_is_unused(model: Model, function: Id[Function]) -> bool
```

Whether `function` is hidden as unused: every one of its ports is unused (`port_is_unused`).

`hide_unused_pins` leaves such a function off the page, and a contact among them is listed as
a spare in its coil's contact table.

### function_item

```python
def function_item(model: Model, function: Id[Function]) -> Id[Item]
```

The item `function` belongs to.

### function_operating

```python
def function_operating(model: Model, function: Id[Function]) -> Operating | None
```

The operating envelope of `function`'s template; `None` with no template or no facet.

Use this on a built model; before a build use d.rating.

There is no fallback to the part: operating characteristics are per template.

Args:
    model: The model to read.
    function: The function whose operating envelope is looked up.

Returns:
    `function`'s template `Operating`, or `None` when it has no template or no facet.

### function_ports

```python
def function_ports(model: Model, function: Id[Function]) -> tuple[Id[Port], ...]
```

The ports of `function`, in table order.

### function_rating

```python
def function_rating(model: Model, function: Id[Function]) -> Rating | None
```

The rating of `function`: its template's, else its part's; `None` when neither has one.

Use this on a built model; before a build use d.rating.

The part is the function template's part when the function has a template, else its item's
part. The template's `Rating` replaces the part's whole (`effective_rating`). A function
with no template and no part, or an id that is not a function of `model`, gives `None`.

Args:
    model: The model to read.
    function: The function whose rating is looked up.

Returns:
    `function`'s template `Rating` when it has one, else its part's, else `None`.

### function_role

```python
def function_role(model: Model, function: Id[Function]) -> FunctionRole
```

The role of `function`: its kind's row refined by its template, rating and holder.

A template's energy, a channel facet, a breaking rating and an operating holder apply.

Example: `function_role(model, fn).contact` is true for a normally open, a normally closed or
a changeover contact and for a switch, and false for a coil.

### functions

```python
def functions(model: Model) -> frozendict[Id[Function], Function]
```

Return every `Function` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `Function` in `model`, keyed by id; the model's own table, so nothing is
    copied. Empty when the model holds none.

### gives_energy

```python
def gives_energy(model: Model, function: Id[Function]) -> bool
```

Whether `function` gives energy out: its role's `energy` (a supply, or `energy = out`).

A power function takes energy in or gives it out.

### gone_or_moved

```python
def gone_or_moved(source: NumberingPins, current: Iterable[NumberingItem | PinPosition]) -> tuple[NumberingRetired, ...]
```

Every `source` pin no longer matched by a current item of the same (key, scope, code).

Gone or moved (group/class code), carried forward at `source`'s position, plus `source.retired`.
It seeds the reserved facets and serves `release()`: decided once.

### harness_cables

```python
def harness_cables(model: Model, harness: Id[Item]) -> tuple[HarnessCable, ...]
```

One `HarnessCable` per child of `harness` that is a cable (`is_cable`).

Cores are `cable_rows`' own. Ends are one per item a core lands on, in `cable_end_rank` order
(a unit member first); a terminal's end is its strip. A non-cable child is left out.

Args:
    model: The frozen model to read.
    harness: The item whose cable children to list.

Returns:
    The cable children's `HarnessCable`s, sorted by `(designation, id)`.

Raises:
    SchemaError: `harness` is not an item, or a cable or core end has no designation.

### harness_cables_for

```python
def harness_cables_for(model: Model, document: Id[Document], pages: tuple[PageKind, ...]) -> tuple[HarnessCable, ...]
```

The subject's cables: SYSTEM all top-level, a unit its own only.

`document` is the document's id.

### harness_line_ends

```python
def harness_line_ends(model: Model, subject: Id[Item]) -> tuple[HarnessLineEnd, ...]
```

The ends of `subject`'s line: a harness's cables and wires, or one cable on no harness.

The one home of branch numbering: the line-text function reads `-W13.n` from `branch` and never
numbers on its own. A plug is an end whose item is a direct child of `subject` or of one of
its cables and which a core or wire lands on a connector function of. Cable and wire ends
merge by end item into one order. Plugs come first, by the natural
order of the connector's designation, then fan-out ends by their first pin's designation;
an end item's id breaks a tie. So `-W13.k` ends at `-W13-Pk` in the common case.

Raises:
    SchemaError: `subject` is neither a harness nor a cable.

### harness_wires

```python
def harness_wires(model: Model, harness: Id[Item]) -> tuple[WireRow, ...]
```

One `WireRow` per wire whose ends sit on the plugs of `harness`.

The rows are the wire list's own: ends, colour, cross-section and printed label.
A wire on no harness, or on two, is left out.

Args:
    model: The frozen model to read.
    harness: The item whose wires to list.

Returns:
    The harness's wires, sorted by `(from_, to, conductor)`.

Raises:
    SchemaError: `harness` is not an item.

### has_documents

```python
def has_documents(model: Model) -> bool
```

Whether the model holds a document.

### has_function

```python
def has_function(model: Model, function: Id[Function]) -> bool
```

Whether `function` is a function of the model.

### has_project

```python
def has_project(model: Model) -> bool
```

Whether the model holds a project.

### has_schematic_subject

```python
def has_schematic_subject(model: Model, document: Id[Document]) -> bool
```

True for a location or unit document; an item or SYSTEM document draws no schematic.

`document` is the document's id.

### is_bar_port

```python
def is_bar_port(model: Model, port: Id[Port]) -> bool
```

Whether `port` belongs to a bar function: the one rule a bar's port follows.

### is_black_box_item

```python
def is_black_box_item(model: Model, item: Id[Item], drawing_set_unit: Id[Unit] | None) -> bool
```

Whether an item at a drawing set of the given unit is that set's black-box content.

True when the item's own unit is set and differs from `drawing_set_unit`
-- the same comparison `fransys_layout`'s `replicate_boundaries` already encodes on
the layout side, and `fransys_render`'s outline already reads on the render side;
this is the one place both may share it (outputs never import each other).

Raises:
    SchemaError: `item` is not an item of `model`.

### is_cable

```python
def is_cable(model: Model, item: Id[Item]) -> bool
```

Whether `item` is a cable: `item in cable_items(model)`.

The one fact that decides it is whether `item`'s `Part` carries a `cable_product` facet.
Reads nothing else: not `category`, not the item's own `CableFacet`, which records only the
as-installed length of a cable and stays that way.

Args:
    model: The model to read.
    item: The item to check.

Returns:
    `True` when `item`'s part carries a `cable_product` facet.

### is_own_unit_root

```python
def is_own_unit_root(model: Model, item: Id[Item], unit: Id[Unit] | None) -> bool
```

Whether `item` is the sole root of `unit`, the unit whose set is being listed.

True when `item.unit == unit` and `item` is its sole root: a unit's own list omits that tag.

Args:
    model: The frozen model to read.
    item: The item to test.
    unit: The unit whose set is being listed; `None` always answers `False`.

Returns:
    `True` if `item` is the sole root of `unit`.

Raises:
    SchemaError: `unit` is set and `item` is not an item of `model`.

### is_plc_module

```python
def is_plc_module(model: Model, item: Item) -> bool
```

Whether `item`'s part has category `PLC_MODULE`: the one test of what a rack holds.

A rack is an item with at least one such child; `plc_rack_modules` lists them.

### is_rail_terminal

```python
def is_rail_terminal(model: Model, terminal: Id[Item]) -> bool
```

Whether `terminal` is a rail terminal: on a DC rail or a PE net, bridged within its strip.

A rail terminal draws no symbol: its pins show the rail's power symbol. An AC rail,
an unbridged terminal, a terminal whose part has a protective link and any
item that is not a terminal are `False`.

### is_replica_only_undrawn

```python
def is_replica_only_undrawn(model: Model, drawing_set: DrawingSet) -> bool
```

Whether the set has placements, all replicas, and no conductor route or `LinkMarker`.

A replica of the page unit's own boundary counts as drawn.

### is_sole_unit_root

```python
def is_sole_unit_root(model: Model, item: Id[Item]) -> bool
```

Whether `item` is the only own-root item of its own unit.

`False` when `item.unit` is `None`. Otherwise `True` only when `unit_own_roots` of that
unit is exactly `(item,)` (external items are not roots): a board
that is the *whole* content of its own `Unit` is a nested unit, not a
board sitting inside a larger one -- and a board sitting inside a larger unit still carries
that larger unit on itself and on everything nested under it via `parent=`, so "shares a
unit with an ancestor board" cannot tell the two cases apart; only "is the sole root of its
unit" can. `enclosing_boards` above answers "which board (if any) encloses this item";
this answers "is that board a whole unit on its own, or merely furniture inside one".

Raises:
    SchemaError: `item` is not an item of `model`.

### is_unit_owned_kind

```python
def is_unit_owned_kind(subject: Id[Record]) -> bool
```

Whether `subject` names an item, function, port, unit or document: what a unit owns.

### item_description

```python
def item_description(model: Model, item: Id[Item]) -> str
```

The text a list shows for `item`: its own `description`, else its part's, else `""`.

An item stores only the description its author wrote; the part's
is never copied onto it. A part-less item with none authored has no text.

Args:
    model: The model to read.
    item: The item whose list text is looked up.

Returns:
    `item`'s own `description`, else its part's, else `""`.

Raises:
    SchemaError: `item` is not an item of `model`.

### item_designation

```python
def item_designation(model: Model, item: Id[Item], *, relative_to: Id[Item] | None=None, unit: Id[Unit] | None=None, held_switches: bool=True) -> str
```

Render `item`'s label: a terminal's `group:index`, else its text, behind its chain (`A1-K1`).

Args:
    model: The frozen model to read.
    item: The item to render.
    relative_to: An enclosing board: drops it and every ancestor outside it; `None` keeps all.
    unit: The unit whose own document is printed; drops its root's tag. `None`: whole model.
    held_switches: as `takes_parents_designation`.

Returns:
    `item`'s printed label; an accessory's is its holder's.

Raises:
    SchemaError: `designation_refusal` of the same arguments is not `None`.

### item_functions

```python
def item_functions(model: Model) -> frozendict[Id[Item], frozenset[Id[Function]]]
```

Each item that has functions, with the set of its functions.

### item_installed

```python
def item_installed(model: Model, item: Id[Item]) -> bool
```

Whether `item` is installed; a drawing greys an item that is not (`installed=False`).

### item_kind

```python
def item_kind(model: Model, item: Id[Item]) -> ItemKind
```

What `item` is: harness, cable, terminal, strip, PLC module, board, bar, connector or device.

The first that holds, in that order. Each test is the one predicate that already decides it:
`is_harness`, `is_cable`, `terminal_items`, `strip_set`, `is_plc_module`, a part with a `pcb`
facet, `bar_items`, and an item whose functions are all connectors. `DEVICE` is the rest.

Raises:
    SchemaError: `item` is not an item of `model`.

### item_label

```python
def item_label(model: Model, item: Id[Item]) -> str
```

What an item is called in a message: its own text, else its authoring key joined by `/`.

Reads no holder and no numbering, and never raises, so it serves an item that has no
designation (`item_designation` raises).

### item_location

```python
def item_location(model: Model, item: Id[Item]) -> Id[AspectNode] | None
```

The `LOCATION` node `item` is placed at, own or inherited; `None` if it has none.

`effective_placement` in the `LOCATION` aspect. A unit's list document with no location of its
own reads its strip's or board's here.

Args:
    model: The model to read.
    item: The item whose location is looked up.

Returns:
    The `LOCATION` `AspectNode` id, own or inherited, or `None` when there is none.

Raises:
    SchemaError: `item` is not an item of `model`.

### item_of_port

```python
def item_of_port(model: Model, port: Id[Port]) -> Id[Item]
```

The item whose function owns `port`.

### item_pages

```python
def item_pages(model: Model) -> dict[Id[Item], tuple[ItemPage, ...]]
```

Every item with each drawing page of a whole-system write that draws one of its functions.

The file is the one `write` names the document's PDF; the text is `position_text` of the
page and the frame cell of the first placement on it. Empty when the model has no document.

### item_parents

```python
def item_parents(model: Model) -> frozendict[Id[Item], Id[Item]]
```

Each child item's parent item, in the order the items table gives the parents.

### item_role

```python
def item_role(model: Model, item: Id[Item]) -> ItemRole
```

The role of `item`: its `item_kind` row plus the rack, external, accessory, root flags.

Lives beside `item_kind` so `facts/roles` never imports it back.

### item_tag_text

```python
def item_tag_text(model: Model, item: Id[Item], *, unit: Id[Unit] | None=None) -> str
```

A component's tag on a drawing: its item designation only, "-Q11".

The page states the location, unit and groups, so a tag never carries them, in a unit's
own set (`unit`, unit-relative) and at top level alike. The one
function every component and strip tag on a drawing is built from.

### item_unit

```python
def item_unit(model: Model, item: Id[Item]) -> Id[Unit] | None
```

The unit `item` is recorded in by `Item.unit`; `None` for the integrating script's own.

### items

```python
def items(model: Model) -> frozendict[Id[Item], Item]
```

Return every `Item` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `Item` in `model`, keyed by id; the model's own table, so nothing is
    copied. Empty when the model holds none.

### items_at

```python
def items_at(model: Model, node: Id[AspectNode]) -> tuple[Id[Item], ...]
```

Every item at `node` or at a node in `subtree(model, node)`, once each, sorted by id.

An item counts by its own `Placement`, else by its nearest placed ancestor's
(`effective_placement`): a board's own component is listed at the board's location or group.

Args:
    model: The model to read.
    node: The aspect node (and its subtree) to list items at.

Returns:
    Every item's id found at `node` or its subtree, once each, sorted.

Raises:
    SchemaError: `node` is not an aspect node of `model`.

### jumper_lane_count

```python
def jumper_lane_count(lanes: JumperLanes) -> int
```

The distinct lanes `lanes` uses (the highest lane plus one), not one per group.

### jumper_lanes

```python
def jumper_lanes(groups: tuple[int | None, ...]) -> JumperLanes
```

Each jumper group's lane, from `groups` (each row's `jumper_group`), by group number.

### keep_whole_sets

```python
def keep_whole_sets(model: Model) -> KeepWhole
```

The `KeepWhole` sets of `model`: add-on item boxes, pole groups and units with a line.

An item box is today approximated by "an item with children": the generic-box test lives in
layout (`read/views.box_drawn`, needs the symbol rules) until EL-2 gives `function_role.box`.

### kind_sheet

```python
def kind_sheet(model: Model, kind: PageKind, unit: Id[Unit] | None=None) -> SheetRow
```

The sheet a page of `kind` of `unit` is on (`layout.sheet_for`) as a `SheetRow`.

### lane_head

```python
def lane_head(model: Model, node: Id[AspectNode]) -> str
```

The text a lane prints: its group's folded-box text, on one line.

### lead_switch

```python
def lead_switch(model: Model, function: Id[Function]) -> Id[Function] | None
```

The first switch of `function`'s group that is wired, else the group's first; else None.

### line_conductors

```python
def line_conductors(model: Model) -> frozendict[Id[Item], tuple[Id[Conductor], ...]]
```

Each line's owner with the conductors its line carries, for owners with two or more.

The owner is a harness, or a cable on no harness. Cores count for their cable's owner and a
single wire for its harness (`harness_of_wire`). Conductors are sorted by id.

### line_designation

```python
def line_designation(model: Model, harness: Id[Item], branch: int, *, unit: Id[Unit] | None=None) -> str
```

`-W13` for a line between two ends, `-W13.n` on each branch of three or more, else `""`.

`branch` is the `HarnessLineEnd.branch` of the end; this never numbers on its own.
Raises `SchemaError` when `branch` is no branch of the line.

### line_stub_line

```python
def line_stub_line(line: str, *, north: bool, far: Sequence[tuple[str, str]]) -> str
```

A leaving line's single stub, `-W3 → +EXT-M1 p2:4A, +EXT-M2 p2:5C`: line, arrow, far devices.

`far` is each far device with where it is drawn in the stub's drawing set, `position_text`'s
form, or "" for none. No place at all keeps the first device alone, the text without places.
The arrow points up (`←`) for a stub facing north, else `→`.

### line_tabs

```python
def line_tabs(model: Model, unit: Id[Unit] | None) -> tuple[LineTab, ...]
```

The end tabs of `unit`'s cable lines (`None`: the system), one row per diagram line.

`ref` is the line's `LineRef` on `overview_level`; `tab_a` stands at its `a` box and `tab_b`
at its `b` box, each the text the block diagram prints there, `None` for no tab. A line of
another kind, or a cable line the diagram lifts differently, has no row.

### link_role

```python
def link_role(model: Model, link: Id[InternalLink]) -> LinkRole
```

The role of an internal link: its kind's row, with the pole and rest the function adds.

A protection's conductive link is a pole; a switched link rests as declared, else as its
function's kind implies.

### link_state

```python
def link_state(model: Model, function: Id[Function], link: Id[InternalLink]) -> LinkState
```

The state in which the internal link `link` of the contact `function` is closed.

A switched link's declared `rest` decides first (`CLOSED` is `"rest"`, `OPEN` `"operated"`).
Otherwise `CONTACT_NO` implies `"operated"`, `CONTACT_NC` `"rest"`, and `CONTACT_CO` the roles
of the link's ends through `_pole` (common to `BREAK` `"rest"`, to `MAKE` `"operated"`).
Anything else is `"both"`, an unknown id too; it never raises.

Args:
    model: The model to read.
    function: The contact function the link belongs to.
    link: The internal link whose closed state is found.

Returns:
    `"rest"`, `"operated"`, or `"both"`.

### link_throw

```python
def link_throw(link: InternalLink, templates: Mapping[Id[PortTemplate], PortTemplate]) -> tuple[Id[PortTemplate], PortRole, Id[PortTemplate]] | None
```

`(common, BREAK or MAKE, throw)` when `link` is a switched link joining a common to a throw.

The template-level reading `changeover_throws` builds on; authoring reads it before a model.

### list_context

```python
def list_context(model: Model, subject: Id[Item], *, location: Id[AspectNode] | None=None) -> Id[AspectNode] | None
```

The location a list's ends print short against: the document's, else `subject`'s own.

`None` means no context: the list queries print full paths.

Args:
    model: The model to read.
    subject: The strip or board item the list is of.
    location: The location document's own node, keyword-only; `None` falls back to `subject`'s.

Returns:
    `location` when given, else `item_location` of `subject`; `None` when neither exists.

Raises:
    SchemaError: `location` is `None` and `subject` is not an item of `model`.

### listing_interface

```python
def listing_interface(listing: Listing) -> str
```

The interface text of the unit a baseline listing lists.

### listing_revision_text

```python
def listing_revision_text(listing: Listing) -> str
```

The `v.r` text of the version and revision of the unit a baseline listing lists.

### load_limits

```python
def load_limits(model: Model) -> tuple[LoadLimit, ...]
```

The draw of each load edge and the limit that bounds it, per current kind.

A load with no stated draw, no current kind or fewer than two conductive ports has no entry.
One load at a time is added to the graph, so the loads never bound each other.

### location_fold

```python
def location_fold(model: Model) -> LocationFold | None
```

The system level folded by top place, or `None` when the model has under two top places.

A box in no place stands in a "No location" box, last. A line joins two boxes with the number
of distinct cables between their members; cables inside one place are no line.

### location_node_designation

```python
def location_node_designation(model: Model, node: Id[AspectNode]) -> str
```

Render an aspect node's signed path, root to leaf (`+C1`, nested `+ER+C1`, a group `=G1`).

The node's own aspect gives the sign, repeated at every level: for a location, exactly the
segment `location_designation` renders for an item placed at `node`. `scope_path` calls it too,
so a title block's scope cell prints the same full path (`+R+S1`).

### location_place_title

```python
def location_place_title(model: Model, place: Id[AspectNode]) -> str
```

A place's printed title, its designation then its text on one line (`+ER Engine room`).

The box prints these as two lines; the overview's panel prints the title. One spelling.

### manifest_rows

```python
def manifest_rows(model: Model, unit: Id[Unit] | None) -> ManifestRows
```

The identity, history, part libraries and nested releases of `unit`'s manifest.

`unit=None` is the system. Each nested row carries the sha256 of the nested listing's
canonical text, hashed once here. Warning texts and package versions stay with the facade.

### mate_port_of

```python
def mate_port_of(model: Model, port: Id[Port], function: Id[Function]) -> Id[Port] | None
```

The port of `function` mated to `port` by name (the lowest id of that name), else `None`.

### mate_ports

```python
def mate_ports(model: Model) -> tuple[tuple[Id[Port], Id[Port]], ...]
```

Each mate's `(a port, b port)` pairs, ports of equal name paired once, sorted by id.

A name held by several ports of one side pairs each with the first port of that name
on the other side, so equal-named ports stay one chain.

### mates

```python
def mates(model: Model) -> tuple[MateRow, ...]
```

One `MateRow` per mate in `model`, sorted by `(a_designation, b_designation)`.

A mate joins two connector or terminal functions, kept in the authored order of `d.mate`. A
mate on a board and one between a plug and a unit's interface connector both appear, where
`connector_rows` covers board connectors only. Each designation is the text the connector list
prints at system level. Reach an item through the function.

Raises:
    SchemaError: a mated function is not of `model`, or its item has no designation.

### mixed_sheet_groups

```python
def mixed_sheet_groups(model: Model, document: Id[Document], pages: tuple[PageKind, ...]) -> tuple[SheetGroup, ...]
```

Each sheet format the drawn pages name with its page numbers; empty unless more than one.

### moved_findings

```python
def moved_findings(model: Model, unit: Id[Unit], source: NumberingPins, path: Path) -> list[Finding]
```

`DESIGNATION_MOVED`: a pinned item or instance now prints a different own text.

### natural_key

```python
def natural_key(text: str) -> NaturalKey
```

Sort key of a printed text: digit runs by value, so `-W2` sorts before `-W10`.

Text runs compare as strings and sort after numbers; the whole text breaks a tie.

### nested_units

```python
def nested_units(model: Model, unit: Id[Unit] | None) -> tuple[Id[Unit], ...]
```

Every unit nested in `unit`'s subtree, sorted; `None` is every unit of the model.

### net_class_role

```python
def net_class_role(model: Model, net: Id[Net]) -> NetClassRole
```

The role of a declared net: its class's row.

### net_of

```python
def net_of(model: Model, port: Id[Port]) -> PhysicalNet | None
```

The `PhysicalNet` containing `port`, or `None` if `port` is not a port of `model`.

Args:
    model: The model to read.
    port: The port whose physical net is looked up.

Returns:
    `port`'s `PhysicalNet`, or `None` when `port` is not a port of `model`.

### nets

```python
def nets(model: Model) -> frozendict[Id[Net], Net]
```

Return every `Net` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `Net` in `model`, keyed by id; the model's own table, so nothing is
    copied. Empty when the model holds none.

### new_in_revision_findings

```python
def new_in_revision_findings(model: Model, unit: Id[Unit], source: NumberingPins) -> list[Finding]
```

`DESIGNATION_NEW_IN_REVISION`: a floating item or instance no pin matches, numbered.

### no_conductor_at

```python
def no_conductor_at(model: Model, port: Id[Port]) -> bool
```

Whether no conductor (wire, jumper, cable core or link) ends at `port`.

Unlike `unconnected_ports`, a mate or a declared net does not count.

### node_label

```python
def node_label(model: Model, node: Id[AspectNode]) -> str
```

The label of aspect node `node`.

### notice_line_count

```python
def notice_line_count(height_mm: float, *, font_mm: float) -> int
```

How many notice lines at `font_mm` a cell `height_mm` high holds.

### notice_lines

```python
def notice_lines(text: str, *, width_mm: float, font_mm: float) -> tuple[str, ...]
```

Greedy word-wrap at `font_mm`: an approximation of Typst's wrap; `()` for no words.

### notice_pitch_mm

```python
def notice_pitch_mm(font_mm: float) -> float
```

The distance from one notice line to the next at `font_mm`.

### notice_room_chars

```python
def notice_room_chars(width_mm: float, *, font_mm: float, capacity: int) -> int
```

About how many characters of running text `capacity` lines hold, to the nearest ten below.

### notice_unfit

```python
def notice_unfit(text: str, *, width_mm: float, font_mm: float, capacity: int) -> bool
```

Whether `text` wrapped at `font_mm` needs more than `capacity` lines.

### number

```python
def number(model: Model) -> tuple[Model, tuple[Finding, ...]]
```

Number every item that has no own designation from its `Part.class_code`.

Each such item gets a `facet.assigned_designation` of class code plus a counter, one
counter per sibling group (unit, nearest designating ancestor, class code).
A tag or existing facet is kept; terminals, partless items and accessories are skipped.
Also reports the `*_DUPLICATE` and `HARNESS_END_AMBIGUOUS` findings (all `ERROR`).

Args:
    model: The model to number.

Returns:
    `model` itself if nothing was numbered, else evolved with the new facets; and the
    findings, sorted by `(code, subjects, message)`.

### one_line_field

```python
def one_line_field(preferred: str, *, size_mm: float, bold: bool=False, width_mm: float, shorter: tuple[str, ...]=()) -> tuple[str, bool]
```

`(text, fits)`: the first of `preferred` and `shorter` that fits, else the last, cut.

The one rule for which text a one-line cell prints and whether it needs the cut; `shorter`
follows `preferred` in decreasing length.

### open_core_rows

```python
def open_core_rows(model: Model, cable: Id[Item], *, unit: Id[Unit] | None=None) -> tuple[OpenCoreRow, ...]
```

One `OpenCoreRow` per open core of `cable`, by core number.

Args:
    model: The frozen model to read.
    cable: The cable item whose spares and one-ended screens to list.
    unit: The unit whose own document draws the cable, keyword-only; `None` is the whole model.

Returns:
    The rows, sorted by core number; `()` for a cable with none.

Raises:
    SchemaError: `cable` is no item, or `unit` is no unit of `model`.

### open_strips

```python
def open_strips(level: OverviewLevel) -> tuple[Id[Item], ...]
```

The strips of `level` that open: those holding at least one terminal, in box order.

### operated_by

```python
def operated_by(model: Model, function: Id[Function]) -> OperatedBy | None
```

What operates a `switch` function: its own part's `operated_by`, else its nearest holder's.

None for any other kind, or when no part on the way up states one.

### operating_item

```python
def operating_item(model: Model, function: Id[Function]) -> Id[Item] | None
```

The item whose part states what operates a `switch` function.

Its own item when its part states one, else the nearest holder that does; None for any other
kind, or when none states one.

### ordered_pages

```python
def ordered_pages(model: Model, *, include_replica_only: bool=True) -> tuple[Page, ...]
```

Every `layout.page` in set then page order; replica-only sets drop out when asked.

### overview_end_text

```python
def overview_end_text(model: Model, unit: Id[Unit], kind: OverviewLinkKind, via: Id[Item] | None, count: int) -> str
```

The text of a line to a stub: its carrier relative to `unit`, else the count text.

### overview_field_join_text

```python
def overview_field_join_text(model: Model, join: FieldJoin) -> str
```

The text of a field box's lifted line: its cables as `overview_lifted_text` prints them.

### overview_fold_line_text

```python
def overview_fold_line_text(line: FoldLine) -> str
```

The text of a folded level's line: its label (cables or `-X3 x 3`), else the count text.

### overview_fold_stub_lines

```python
def overview_fold_stub_lines(stub: FoldStub) -> tuple[str, ...]
```

The text lines of a folded stub's box: its far name; a closed fold prints no member list.

A fold of several members prints its name and count (`Field devices (2)`); any other stub also
prints the port tails of its members.

### overview_fold_stub_text

```python
def overview_fold_stub_text(model: Model, unit: Id[Unit], stub: FoldStub) -> str
```

The text of the line to a folded stub: its carrier relative to `unit`, else the count.

### overview_graph

```python
def overview_graph(model: Model) -> OverviewGraph
```

The overview: one node per item, the aggregated links between items, the multi-item signals.

This query does not raise for an item with no designation yet: `OverviewNode.designation` (and a
link's `via_designation`) is `None` there, so a half-finished design still draws. Other
designations are `printed_designation` (`"-K1"`, `"-X1:L1:1"`). Nodes sort by `(designation with
None last, id)`. A link joins two items by one kind and one `via`: `wire` for a conductor with
no carrier, `cable` for the conductors of one cable item, `mate` for `Mate`s between functions
of the two items (`count` is the number of mates, `conductors` empty). `a` is the smaller id;
links sort by `(a, b, kind value, via)`, no `via` first. A signal is a physical net
(`physical_nets`) that reaches at least two items, its ports sorted by `(item id, pin order,
port id)`; signals sort by their first port.

### overview_lane_nodes

```python
def overview_lane_nodes(model: Model, unit: Id[Unit]) -> dict[BoxKey, Id[AspectNode] | None]
```

Each box of `unit`'s level: its function group node, `None` for a strip or no group.

### overview_lane_strips

```python
def overview_lane_strips(model: Model, unit: Id[Unit]) -> frozenset[BoxKey]
```

The boxes of `unit`'s level that are terminal strips, which stand in the shared lane.

### overview_level

```python
def overview_level(model: Model, unit: Id[Unit] | None) -> OverviewLevel
```

One level of the overview: the system (`unit=None`) or `unit` opened.

The system level is `diagram_lines` of the block diagram: unit boxes with tabs, by-others items
dashed, one line per cable. An opened unit has one box per nested unit (with its boundary
tabs), per terminal strip (folded, with its terminal count) and per other root item, with
connectors on a box as its tabs. A line joins two boxes per kind and carrier; a connection
between items inside one box is dropped, and `count` is the connections lifted into the line.
A connection to an item outside `unit` is a stub at the inside box, named by `stub_far_end`.
Designations are relative to `unit`. Boxes and lines are in box text order.

### overview_lifted_text

```python
def overview_lifted_text(kind: OverviewLinkKind, carriers: Sequence[str], count: int) -> str
```

The one text of a line for `count` connections carried by cables printed `carriers`.

One carrier prints its designation, several print `x N` for N carriers, none print the count
text (`x 3` for a wire or mate line of three, else empty). Every level's lifted lines use it.

### overview_line_text

```python
def overview_line_text(line: OverviewLine) -> str
```

The text of a line: its carrier's designation, else the count text.

### overview_location_line_text

```python
def overview_location_line_text(model: Model, line: LocationLine) -> str
```

The text of a location line: its cables as `overview_lifted_text` prints them.

### overview_power_lines

```python
def overview_power_lines(model: Model, unit: Id[Unit]) -> frozenset[tuple[BoxKey, BoxKey]]
```

The ends of each line of `unit`'s level that carries a conductor on an AC potential.

### overview_strip_joins

```python
def overview_strip_joins(model: Model, unit: Id[Unit]) -> dict[BoxKey, int]
```

Each box joined to a terminal strip: the place of the first terminal it joins.

Strips run in box text order, each strip's terminals in the strip's own order; the place counts
terminals over all strips. A box that joins no strip is absent. A stub box counts as joined:
its far end is the box that joins the terminal.

### overview_stub_lines

```python
def overview_stub_lines(stub: OverviewStub) -> tuple[str, ...]
```

The text lines of a stub's box: the far device, then its port tails when it has any.

### overview_stub_text

```python
def overview_stub_text(model: Model, unit: Id[Unit], stub: OverviewStub) -> str
```

The text of the line to a stub: its carrier relative to `unit`, else the count text.

### overview_stub_west

```python
def overview_stub_west(model: Model, unit: Id[Unit], end: OverviewRef) -> bool
```

Whether the lanes stub for `end` stands west of the level of `unit`; else east.

West: an item that is a terminal strip, or one held by a unit that encloses `unit`.

### overview_tree

```python
def overview_tree(model: Model) -> tuple[TreeRow, ...]
```

The rows of the parts tree in display order, each naming its parent row by index.

### overview_units

```python
def overview_units(model: Model) -> tuple[Id[Unit] | None, ...]
```

`None` for the system, then every unit instance by the natural order of its designation.

### overview_view_rows

```python
def overview_view_rows(model: Model, unit: Id[Unit] | None) -> tuple[ViewRows, ...]
```

The views of `unit`'s level (`None`: the system), each with its boxes and lines.

The plain level, each of its strips opened, and for a unit its folded levels: the groups, the
all-devices level and each group. A fold is never a view of its own. A level with no box has
no view.

### own_drawing_line

```python
def own_drawing_line(model: Model, unit: Id[Unit]) -> str
```

The panel line naming the drawing set `unit` has: its printed label and its release.

### own_nodes

```python
def own_nodes(model: Model, unit: Id[Unit]) -> frozenset[Id[AspectNode]]
```

The aspect nodes that are `unit`'s own.

Location node: every item at or below it is in `unit`'s subtree (cables and harnesses ignored).
Function node: a unit item sits at or below it and no item of another unit does.

Args:
    model: The frozen model to read.
    unit: The unit whose own nodes to find.

Returns:
    The set of aspect node ids that are `unit`'s own.

Raises:
    SchemaError: `unit` is not a unit of `model`.

### owned_contacts

```python
def owned_contacts(model: Model, device: Id[Item]) -> tuple[Id[Function], ...]
```

The contact functions `device` owns, sorted by id: its own and its add-on blocks'.

An add-on block prints `device`'s designation, so its contacts are the
device's. Layout's contact table and the contacts' home references read it.

### page_destination

```python
def page_destination(model: Model, sheet: Page | DiagramSheet) -> str
```

`p<k>.<page>`: the destination label of a page, `k` its set's rank; `b<n>` for a diagram.

### page_kinds

```python
def page_kinds(preset: DocumentPreset, *, add: tuple[PageKind, ...]=(), remove: tuple[PageKind, ...]=()) -> tuple[PageKind, ...]
```

The pages of a document: the preset's pages plus `add`, minus `remove`, in canonical order.

`remove` wins over `add`. Whether a NOTES page is actually produced also depends on the
document having notes text; that is decided when the document is assembled.

### page_order_key

```python
def page_order_key(set_number: int, page: Page) -> tuple[int, int]
```

The one page order: the page's drawing-set number, then its own number.

### page_reference_text

```python
def page_reference_text(model: Model, page: Page, *, with_location: bool=False) -> str
```

`p3`, `p2.3` for page 3 of the unit's second set; `+CAB p3` with the set's location path.

### page_title

```python
def page_title(model: Model, page: Page) -> str
```

The page's title: the first, longest candidate text of `page_title_forms`.

### page_title_forms

```python
def page_title_forms(model: Model, page: Page) -> tuple[str, ...]
```

The candidate texts of `page`'s title, each shorter than the one before.

The joined entries; then "first to last", only when every entry names one unit; then
the lead entry and "and n more". The frame prints the first that fits.
A page with no entry keeps the unit's title in a unit's set, else the empty text.

### page_wires

```python
def page_wires(model: Model, lead_grids: Mapping[Id[Page], int]) -> dict[Id[Page], PageWires]
```

The bends and the length in mm of the conductor lines of each page of `model` with one.

`lead_grids` is the total length in grid units of each page's straight power leads, which
only layout knows; they add length and no bend.

### part_function_pins

```python
def part_function_pins(model: Model) -> dict[Id[Part], list[tuple[str, list[str]]]]
```

Each part's function templates and their pin names, both sorted by marking.

### part_function_rows

```python
def part_function_rows(model: Model) -> tuple[PartFunctionRow, ...]
```

One row per function template of each part, a part with none gets one row; sorted.

Reads the parts a model holds, built or not: no item is needed. The rating is
`effective_rating`, the one fallback rule: the template's, else the part's.

### part_rating

```python
def part_rating(model: Model, part: Id[Part]) -> Rating | None
```

The rating of `part` itself, for a part with no function to ask about (a fuse link).

Use this on a built model; before a build use d.rating.

Args:
    model: The model to read.
    part: The part whose own rating is looked up.

Returns:
    `part`'s `Rating`, or `None` when it has no rating facet or `part` is not a part of
    `model`.

### part_records

```python
def part_records(model: Model) -> tuple[Part, ...]
```

Every part record, in table order.

### physical_nets

```python
def physical_nets(model: Model) -> tuple[PhysicalNet, ...]
```

Union-find `model`'s ports into physical nets.

Ports join through `Conductor`s, `conductive` `InternalLink`s (per item, through each port's
`PortTemplate`) and `Mate`s (equal port names). `switched` links never join, so a relay's coil
and contact stay separate nets. A port with no connectivity or no template is its own singleton
`PhysicalNet`. Sorted by each net's `ports`, so record order never matters; cached on
`model.digest`.

Args:
    model: The model to read.

Returns:
    Every physical net, sorted by its own `ports` tuple.

### pin_lines

```python
def pin_lines(rows: Iterable[ConnectorRow]) -> list[tuple[object, ...]]
```

One line per pin of each connector row: the connector's fields, then the pin's.

Args:
    rows: The connector rows to print, in the order to print them.

Returns:
    One tuple per pin: `CONNECTOR_COLUMNS` of its row, then `PIN_COLUMNS` of the pin.

### pin_order

```python
def pin_order(marking: str, port: Id[Port]) -> tuple[tuple[tuple[int, int, str], ...], str, Id[Port]]
```

The sort key of a pin: `marking_key` (digit runs by value, `A2` before `A10`), then the port.

The marking text and the port id break ties; no designation is parsed. Shared by
`connector_rows`, `harness_cables`, `overview_graph` and `fn.pins`.

### pin_positions

```python
def pin_positions(model: Model, unit: Id[Unit]) -> tuple[PinPosition, ...]
```

`unit`'s non-terminal items and direct instances as `(key, scope, code)`, by key.

### pin_source

```python
def pin_source(stored: StoredReleases, identity: ReleaseIdentity) -> StoredRelease | None
```

The stored release of the same version at or below `identity`'s revision, with numbering.

Same name and version only, unlike `previous_release`; a re-release may be its own source.

### pin_source_pins

```python
def pin_source_pins(stored: StoredReleases, identity: ReleaseIdentity) -> tuple[str, NumberingPins] | None
```

The folder name and numbering of `pin_source`, or `None` when it has no numbering.

### pin_text

```python
def pin_text(pin: NetlistPin) -> str
```

The one spelling of a pin for a netlist output: `ref:pad`.

Args:
    pin: A resolved pin.

Returns:
    The component reference, a colon and the pad name.

### place_members

```python
def place_members(model: Model, box: ViewBox) -> tuple[Id[Item] | Id[Unit], ...] | None
```

The units and items a place box of the location fold holds, else `None`.

### placements

```python
def placements(model: Model) -> frozendict[Id[Placement], Placement]
```

Return every `Placement` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `Placement` in `model`, keyed by id; the model's own table, so nothing is
    copied. Empty when the model holds none.

### plc_channel_rows

```python
def plc_channel_rows(model: Model, *, unit: Id[Unit] | None=None, context: Id[AspectNode] | None=None) -> tuple[PlcChannelRow, ...]
```

One `PlcChannelRow` per pin of each PLC channel `Function`, in the PLC list's table order.

The order is `plc_channel_key`: controllers by designation, each one's own channels
then its modules in rack order, last the channels on items in no rack. `wired_to` is the far
end of every conductor at that pin's port. `unit` keeps only channels of that unit;
`context` is the location node the list is printed for, ignored once `unit` has one.

Raises:
    SchemaError: a module or device has no designation, or `unit` is no unit of `model`.

### plc_list_rows

```python
def plc_list_rows(rows: Iterable[PlcChannelRow]) -> tuple[tuple[str | None, ...], ...]
```

One `PLC_COLUMNS` line per row for a printed list: the signal as its word.

A channel bound to no field device and wired to nothing prints `spare` for its signal name.
The cells follow `PLC_COLUMNS`' order, so a column change edits that tuple alone.

### plc_rack_modules

```python
def plc_rack_modules(model: Model, rack: Id[Item], *, unit: Id[Unit] | None=None) -> tuple[PlcRackModule, ...]
```

One `PlcRackModule` per PLC module of `rack`, in physical rack order.

The modules are the children of `rack` by `parent` whose `Part` has category `PLC_MODULE`; a
module with no channel (a coupler, an end module) has `channels=()`. They order by `position`
(integers ascending, `None` last), then the module's own tag in natural order
(`plc_module_key`), the order `allocate_plc` serves them in; `installed` is ignored. A module's
channels are the functions whose template carries a `plc_channel`, bound or spare, ordered by
`plc_channel_tie`. The field device is read as `plc_channel_rows` reads it; `scaling` is its
`scaling` facet, `None` for a spare channel or a device without one.

`unit` prints the designations as that unit's own document does; `None` the full form.

Raises:
    SchemaError: `rack` is not an item of `model`, or a module or device has no designation.

### plc_tables

```python
def plc_tables(model: Model, *, unit: Id[Unit] | None=None, context: Id[AspectNode] | None=None) -> tuple[PlcTable, ...]
```

The rows of `plc_channel_rows`, one `PlcTable` per carrying item, in the same order.

A controller's own channels form its table, then each module's follow in rack order; the
items in no rack come last, one table each. An item with no channel has no table.
`unit` and `context` are `plc_channel_rows`'s.

Raises:
    SchemaError: as `plc_channel_rows`.

### port_designation

```python
def port_designation(model: Model, port: Id[Port], *, unit: Id[Unit] | None=None) -> str
```

Render `port` as its item's designation and its name (`-K1:13`), always dash-prefixed.

A terminal's port drops its name (`terminal_designation`); a connector pin reads `-U2-X1:1`;
a bar's port drops it too (`-PE1`): the screw is no part of the wiring (PE-BAR B4).

Args:
    model: The frozen model to read.
    port: The port to render.
    unit: The unit whose own document is printed; `None` renders the whole-model form.

Raises:
    SchemaError: `port` is not of `model`, or its item (a terminal's parent too) has none.

### port_is_reached

```python
def port_is_reached(model: Model, port: Id[Port]) -> bool
```

Whether a wire inside the drawing of `port`'s unit, or a net, reaches `port` itself.

The same rule as `function_is_reached`, for one port: layout draws a connector pin only where
this holds for it or its mated pin, or a parent's black box needs it.

### port_is_unused

```python
def port_is_unused(model: Model, port: Id[Port]) -> bool
```

Whether no conductor (wire, jumper, cable core or link) ends at `port` and no net has it.

A mate does not count. This is the one test of an unused port; a function is unused when all
its ports are (`function_is_unused`).

### port_name

```python
def port_name(model: Model, port: Id[Port]) -> str
```

The raw name of `port` on its function, not the printed one (`printed_port_name`).

### port_potential_current

```python
def port_potential_current(model: Model, port: Id[Port]) -> Current | None
```

The current, AC or DC, of the supply behind `port_potential_rank`'s potential.

`None` when the port has no rank, and for protective earth, which belongs to no supply.

### port_potential_rank

```python
def port_potential_rank(model: Model, port: Id[Port]) -> int | None
```

The rank of the potential `port` carries in service: smaller is drawn higher up, else `None`.

The order comes from the supply's declared facts, never from a rail's name: AC rails with a
phase, by phase; DC rails above 0 V, highest first; the AC rail at 0 V; the DC rail at 0 V;
DC rails below 0 V, highest first; protective earth last. Equal facts tie by potential
text, since declaration order is no model fact (models differing only in it are equal).
A port takes its own declared net's potential, else what the rail closure reaches through
conductors, mates, conductive and switched links (`port_rails`), so a pin behind a contact
keeps its rank. Reached from two rails (a changeover between two sources), it takes the lower
rank. A net potential that no supply declares gives `None`. Power-symbol eligibility is a
separate question that keeps the physical net.

### port_power_kind

```python
def port_power_kind(model: Model, port: Id[Port]) -> PowerKind
```

The `PowerKind` of the physical net of `port`; `NONE` when `port` is not in `model`.

A load pin wired to a 24 V terminal gets the kind of that net though no `Net` lists it.
Cost: O(1) once per model digest, like `port_rails`.

### port_power_text

```python
def port_power_text(model: Model, port: Id[Port]) -> str | None
```

The text the power symbol at `port` prints: `power_text` of its physical net, else `None`.

A load pin wired to a 24 V terminal prints that net's text. Cost: O(1) once per model digest.

### port_rails

```python
def port_rails(model: Model, port: Id[Port]) -> frozenset[str]
```

The rails `port` carries: the empty set for a port that carries none or is not in `model`.

A rail is a potential some `SupplySystem` declares and a declared `Net` carries. Each spreads
from its nets' ports through conductors, mates, `conductive` and `switched` links (contacts
counted closed) but never enters a net carrying another rail. A changeover's common reached
from two rails carries both. Only structure is read, never a port name. Which rails stand at
once: `rail_pairs`. Cached on `model.digest`.

Args:
    model: The model to read.
    port: The port whose rails are looked up.

Returns:
    The names of the rails `port` carries.

### port_role

```python
def port_role(model: Model, port: Id[Port]) -> PortRole
```

The `PortRole` of `port`: the one reader of `Port.role`.

### ports

```python
def ports(model: Model) -> frozendict[Id[Port], Port]
```

Return every `Port` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `Port` in `model`, keyed by id; the model's own table, so nothing is
    copied. Empty when the model holds none.

### power_kind

```python
def power_kind(model: Model, net: Id[Net]) -> PowerKind
```

The `PowerKind` of declared `net`, read from its physical net, never from its name.

A net of class `PE` is `PE`, supplied or not. Otherwise the physical net's one potential is
looked up in the supplies: a DC rail above or below 0 V is `SUPPLY`, a DC rail at 0 V is
`GROUND`. An AC rail, a potential in no supply, no potential, or two potentials on one
physical net are `NONE`, as is a net whose ports fall in physical nets of different kinds.
A physical net of exactly two ports, bridges and links counted, is `NONE` whatever its
potential: a wire, not a rail; it keeps the potential.
A DC supply that declares no 0 V rail leaves its 0 V net `NONE`: declare it.

Raises:
    KeyError: `net` is not a declared `Net` of `model`.

### power_text

```python
def power_text(model: Model, net: Id[Net]) -> str | None
```

The text a power symbol of declared `net` prints, or `None` when it prints none.

Only `SUPPLY` prints: `Net.name`, else `Net.potential` (which carries the sign of a negative
rail, `-15V`). `GROUND`, `PE` and `NONE` print none.

### previous_release

```python
def previous_release(stored: StoredReleases, identity: ReleaseIdentity) -> StoredRelease | None
```

The stored release with the highest order strictly below `identity`'s, or `None`.

Across versions (they run in parallel); the folder of `identity` itself is never a candidate.

### previous_release_listing

```python
def previous_release_listing(stored: StoredReleases, identity: ReleaseIdentity) -> Listing | None
```

The listing of `previous_release`, or `None` when there is no previous release.

### printed_designation

```python
def printed_designation(model: Model, item: Id[Item], *, unit: Id[Unit] | None=None, held_switches: bool=True) -> str
```

Render `item` as a list prints it: behind its product-aspect sign (`-K1`, `-X1:L1:1`).

Args:
    model: The frozen model to read.
    item: The item to render.
    unit: The unit whose own document is printed; `None`: whole model.
    held_switches: as `item_designation`.

Returns:
    `item`'s printed designation, dash-prefixed.

Raises:
    SchemaError: as `item_designation`.

### printed_drawing_sets

```python
def printed_drawing_sets(model: Model) -> tuple[DrawingSet, ...]
```

The sets some document of `model` prints, by `number`; none that no document prints.

### profile_of

```python
def profile_of(model: Model, unit: Id[Unit] | None=None) -> Profile
```

The profile `unit` authors (`None`: the top design), or the house one (`default_profile()`).

The one reader of a profile. It matches `unit` exactly and never falls back to a containing
unit or to the top's: a unit with no profile of its own draws with the house numbers.

### project_facts

```python
def project_facts(model: Model) -> tuple[str, str, str, str, str, str]
```

(title, number, customer, revision, revision_date, author); all empty with no `Project`.

### prospective_fault

```python
def prospective_fault(model: Model) -> tuple[ProspectiveFault, ...]
```

The prospective fault current at each protective position, per current kind.

One entry per position whose function is a `protection` one and per kind its rails carry.
A bolted fault at either terminal joins it to every other rail of its supplies; the loads are
left out, every source and every declared supply that states a fault current counts. A
position no source reaches reads `0`.

### rack_modules_for_cdp

```python
def rack_modules_for_cdp(model: Model, rack: Id[Item], *, unit: Id[Unit] | None=None) -> tuple[CdpRackModule, ...]
```

The modules of `rack` that have channels, each with its `ordinal` and `single_signal`.

A module with no channel (a coupler, an end module) is left out. `ordinal` counts the kept
modules of one `mpn` in rack order from 0, so an output can letter them; `single_signal` is
the one signal type all channels share, `None` when they differ. `unit`: as `plc_rack_modules`.

Raises:
    SchemaError: as `plc_rack_modules` raises it.

### rail_pairs

```python
def rail_pairs(model: Model, function: Id[Function]) -> frozenset[tuple[str, str]]
```

The pairs `(low, high)` of rail names, `low < high`, that can stand across `function`.

Two rails at two different ports of the function, whose conditions agree (no item in two
states). A `rest` link needs its item at rest, an `operated` link operated, `both` nothing; a
link only adds a condition, never blocks. Two rails at one port are never a pair. Known limit:
all contacts of one item move together, so a pair may be missed (it errs towards silence).

Args:
    model: The model to read.
    function: The function whose standing rail pairs are found.

Returns:
    Every pair `(low, high)` of rail names that can stand across `function`; empty for a
    function with no pair, an unknown function, or no rail.

### readability_units

```python
def readability_units(pages: Iterable[ReadabilityPage], loose: Mapping[Id[Unit] | None, int]) -> tuple[ReadabilityUnit, ...]
```

One row per unit of `pages`, in the order its first page comes; `None` is the design.

`loose` is the count of loose symbols by unit; a unit with none has 0.

### reading_cables

```python
def reading_cables(model: Model, unit: Id[Unit] | None) -> tuple[HarnessCable, ...]
```

The cables one reading draws: `unit`'s own, or the top-level ones when `unit` is None.

The one home of that choice, so no output or layout step repeats it.

### rebaseline_subjects

```python
def rebaseline_subjects(model: Model, unit: Id[Unit] | None) -> tuple[Id[Unit] | None, ...]
```

`unit` and every unit below it, deepest first, then the system; `None` covers the model.

A deeper unit has a longer key, so a container never precedes a unit it nests. The system
(`None` in the tuple) is last and only when `unit` is `None` and the model holds a project.

### record_key_text

```python
def record_key_text(model: Model, subject: Id[Record]) -> str
```

The key text of the record `subject` names, looked up in the table of its kind.

### reference_designation

```python
def reference_designation(model: Model, item: Id[Item], *, unit: Id[Unit] | None=None) -> str
```

Render `item`'s full IEC 81346 reference: `=A1+C1-K1`, and `=A1-X1:L1:1` for a terminal.

Own placements give the `=`/`+` labels (`reference_leaves`), then the product part, as printed.

Args:
    model: The frozen model to read.
    item: The item to render.
    unit: The unit whose own document is printed: keeps its own nodes. `None`: whole model.

Returns:
    `item`'s full IEC 81346 reference.

Raises:
    SchemaError: as `item_designation`.

### reference_fragment

```python
def reference_fragment(model: Model, item: Id[Item]) -> str
```

The `<ref>` export-name fragment of `item`: a strip `+C1-X1` gives `C1-X1`.

Names a per-item export in `out/all/` (`unit=None`) and a netlist intermediate.

### references_off_document

```python
def references_off_document(model: Model) -> tuple[OffDocumentReference, ...]
```

The printed references whose target is off the document and whose text names no other.

A reference is a cross-reference label with partners, or a link marker with its partner. It
is off the document when no document prints both its page's drawing set and its target's.
Its text names the other document when it prints a location path (`location_prefix`).

### refuses

```python
def refuses(findings: Iterable[Finding]) -> bool
```

True when `findings` holds an `ERROR`: the build writes nothing, a library does not load.

### release_identity

```python
def release_identity(model: Model, unit: Id[Unit] | None) -> ReleaseIdentity
```

The name, version, revision and interface `unit` is released under.

A unit's come from its `UnitRelease`; `unit=None` reads the model's one `Project`, whose
interface is empty. A model with no `Project` and `unit=None` raises `StopIteration`.

### release_names

```python
def release_names(model: Model) -> tuple[str, ...]
```

The name of every unit release, in table order.

### release_order

```python
def release_order(version: int, revision: int) -> ReleaseOrder
```

`(version, revision)`: the ONE order of unit releases and of history entries.

The plain pair of two ints, never the printed text: `(1, 9) < (1, 10) < (2, 1)`, where the
text `"1.10"` would sort before `"1.9"`. Every later pin-source and previous-release
selection calls this function and never compares revisions again.

### replica_only_sets

```python
def replica_only_sets(model: Model, document: Id[Document], pages: tuple[PageKind, ...]) -> tuple[ReplicaOnlySet, ...]
```

The matched drawing sets of `document` that its SCHEMATIC skips as replica-only.

Empty on the same terms as `schematic_page_ids`.

### requests_harness_pages

```python
def requests_harness_pages(pages: tuple[PageKind, ...]) -> bool
```

Whether `pages` holds `CONTENTS` or `HARNESS_DRAWING`, the page kinds that show cables.

The one home of this test: `harness_cables_for` reads it, since the
`CONTENTS` table prints the cables' rows and `HARNESS_DRAWING` draws them.

### resolve_wire_rows

```python
def resolve_wire_rows(model: Model) -> tuple[Model, tuple[Finding, ...]]
```

Write the `WireFacet` of every hinted wire from its row; the rest are `ERROR` findings.

A wire that already has a facet is skipped, so a second run changes nothing and the model
comes back as the same object when nothing is hinted.

### revision_findings

```python
def revision_findings(model: Model, unit: Id[Unit], source: NumberingPins, path: Path) -> list[Finding]
```

What `source` says about `unit`'s revision: moved designations, then new floating ones.

### revision_history

```python
def revision_history(model: Model, release: Id[UnitRelease] | None=None) -> tuple[Revision, ...]
```

Every `Revision` of `release`, in date order, then version and revision order.

`release=None` selects the project's own history: every entry with `Revision.release is None`.
Every instance of a release shares the release's history. "Revision order" sorts by the ints
`(version, revision)`, so revision 2 sorts before revision 10.

Raises:
    SchemaError: `release` is not `None` and names no `UnitRelease` of `model`.

### revision_rows

```python
def revision_rows(model: Model, release: Id[UnitRelease] | None=None) -> tuple[RevisionRow, ...]
```

`revision_history` as rows: date order, then version and revision order.

### revision_text

```python
def revision_text(version: int, revision: int) -> str
```

The revision as printed: `f"{version}.{revision}"`, `1.1`, `2.1`, `1.10`.

The one home of the print form: a title block's Rev cell, a revision history row, a unit
line's BOM `Revision` column, a black box title and a message naming a revision all call it.
Nothing else formats the pair.

### run_point_text

```python
def run_point_text(model: Model, function: Id[Function]) -> str
```

A strip terminal's point text in a run, "L2:1".

The terminal's own `group:index`, the strip's designation left out (`strip_tag_text` prints it).
A terminal that is no part of a run prints `terminal_designation`, never this.

### same_version

```python
def same_version(previous: tuple[str, int], current: tuple[str, int]) -> bool
```

Whether two releases are the same name and version; `revision` is never compared.

`previous`/`current` are each `(name, version)`, read straight off whichever record the
caller has (`UnitRelease`, a stored listing's `unit`, a release target) -- never a new
record type of its own.

### schematic_functions

```python
def schematic_functions(model: Model) -> tuple[Id[Function], ...]
```

Every `Function` the schematic engine actually attempts to draw, in `Id` order.

Excludes a cable item's own function and every function on or under a board item
(`enclosing_boards`), with two exceptions. A `CONNECTOR` function on or under a board is always
drawn: the board is a black box on the cabinet page, its edge connectors are not. A
non-`CONNECTOR` function stays when the nearest enclosing board `is_sole_unit_root`: a board
that is the whole content of its `Unit` is drawn like any unit's set. One predicate for layout
and render, since neither package may import the other.

Args:
    model: The model to read.

Returns:
    Every drawn function's id, sorted.

### schematic_page_ids

```python
def schematic_page_ids(model: Model, document: Id[Document], pages: tuple[PageKind, ...]) -> tuple[Id[Page], ...]
```

The ids of the SCHEMATIC pages of `document` in set then page order.

Empty when `pages` has no SCHEMATIC or `document` has no location or unit subject.

### scope_path

```python
def scope_path(model: Model, document: Id[Document]) -> str
```

The title block's Scope cell: a place's full `+R+S1` path, else the subject.

The path stands alone; the page title and the heading carry the place's description.

`document` is the document's id.

### seed_pins

```python
def seed_pins(model: Model, unit: Id[Unit], source: NumberingPins) -> SeedRows
```

The assigned items, assigned instances and reserved texts `source` seeds into `unit`.

A pin seeds only a thing it still matches in key, scope and code that carries no written tag.
Reserved texts are every pin gone or moved, plus the source's own `retired`.

### series_pairs

```python
def series_pairs(model: Model, function: Id[Function], sides: Mapping[Id[Port], Side]) -> tuple[SeriesPair, ...]
```

Each pole of `function` with one wired N pin and one wired S pin, in pole order.

### set_page_text

```python
def set_page_text(set_number: int, page_number: int) -> str
```

`<set>.<page>`, `"2.3"`: a page named with its drawing set (a reference prints `p` first).

### sheet_counter_text

```python
def sheet_counter_text(sheet: Page | DiagramSheet, total: int) -> str
```

`<number> / <total>`: the title block's sheet cell; `B1 / 2` for a block diagram sheet.

### sheet_frame

```python
def sheet_frame(sheet: SheetFormat) -> SheetFrame
```

The frame of `sheet`: the border keeps the content box's margin on every side.

The band is the border's bottom part under the content box; the square logo cell ends it.

### sheet_index_rows

```python
def sheet_index_rows(model: Model, document: Id[Document], kinds: tuple[PageKind, ...]) -> tuple[SheetIndexRow, ...]
```

One row per sheet of `sheets`; empty for fewer than two sheets (empty-list rule).

`document` is the document's id.

### sheet_key_text

```python
def sheet_key_text(key: SheetKey) -> str
```

The printed form of a `SheetKey`, for a message: `<document>#<KIND>#<ordinal or none>`.

### sheet_text

```python
def sheet_text(model: Model, sheet: Page | DiagramSheet) -> str
```

The sheet number a sheet prints: `3`, `2.3` in a set past its unit's first, `B1`.

The destination label and a reference keep the set-and-page form `p1.3` (`set_page_text`).

### sheet_title_text

```python
def sheet_title_text(model: Model, sheet: Page | DiagramSheet, title: str) -> str
```

`Sheet 3: Pump 1`: a sheet's outline entry text; with no title, `Sheet 3`.

### sheets

```python
def sheets(model: Model, document: Id[Document], kinds: tuple[PageKind, ...]) -> tuple[DiagramSheet | Page, ...]
```

Block diagram sheets in number order, then schematic pages in set then page order.

`kinds` is the document's page kinds: a dropped kind contributes no sheet.

### short_title

```python
def short_title(entries: tuple[str, ...]) -> str | None
```

`first to last` with their shared leading words printed once; `None` for one entry.

"Relay 1" and "Relay 3" give "Relay 1 to 3"; with no shared word, or none left after it,
"Supply to Pump 2". A first and last entry that are the same text have no short form.

### sideless_pins

```python
def sideless_pins(one: str, first: tuple[PortTemplate, ...], two: str, second: tuple[PortTemplate, ...]) -> SidelessPins
```

Order each end by `port_order_key`; `problem` names `one` and `two` when they do not pair.

A pin with no printed marking sorts by its name. The ends do not pair when they have a
different number of pins, or the same names in another order.

### signal_kind

```python
def signal_kind(signal: SignalType) -> SignalKind
```

The form and direction of a PLC signal type, for a channel's facet or a field request's.

`DI` is digital in, `DO` and `RELAY` digital out; the two analogue inputs and `RTD` analogue in;
the two analogue outputs analogue out. A channel and the request it serves give one kind.

### signal_lens

```python
def signal_lens(model: Model) -> tuple[LensModule, ...]
```

The PLC modules with their channels and field devices.

Racks in `plc_rack_key` order, then `plc_rack_modules`' physical order within each, so the lens
reads the rack as the PLC list does. Each channel carries `signal_kind` of its signal type.
A module with no channel is not listed. Raises `SchemaError`, as `plc_rack_modules` does,
for a module or device with no designation.

### signal_word

```python
def signal_word(signal: SignalType) -> str
```

The datasheet word for `signal`: `DI`, `DO`, `AI (V)`, `AI (mA)`, `AO (V)`, `AO (mA)`, `RTD`.

A relay output prints `DO (relay)`.

### sizes_of

```python
def sizes_of(model: Model, document: Id[Document]) -> Sizes
```

The font sizes of a document's pages: its unit's profile (the top's) sets the smallest.

`document` is the document's id.

### stale_patterns

```python
def stale_patterns() -> tuple[str, ...]
```

The top-level file patterns a write owns and sweeps: every kind of `export_set`.

Per-item kinds give `<kind>-*.<ext>` and the bare `<kind>.<ext>`; PDFs are `*.pdf`.

### standalone

```python
def standalone(model: Model, unit: Id[Unit]) -> bool
```

Whether every item of `model` belongs to `unit`'s subtree.

A unit is standalone when nothing in `model` sits outside it: no item with `unit=None`
and no item of another unit that is not in `unit`'s own subtree.

Raises:
    SchemaError: `unit` is not a unit of `model`.

### stands

```python
def stands(model: Model) -> frozendict[Id[Port], PowerKind]
```

Each port of a rail net, mapped to the net's `PowerKind`; a wire or a signal is absent.

Built on `power.port_power_kind`, the one rail rule, so a two-port net is never a stand.

### strip_of

```python
def strip_of(model: Model, item: Id[Item]) -> Id[Item] | None
```

`item`'s strip when it is a terminal: its `Item.parent`; `None` for anything else.

### strip_side_headings

```python
def strip_side_headings(model: Model, strip: Id[Item]) -> tuple[str, str]
```

Ends headings: the strip's shared non-empty markings, else `TERMINAL_LABELS`.

### strip_stubs

```python
def strip_stubs(model: Model, strip: Id[Item], unit: Id[Unit]) -> tuple[TerminalStubs, ...]
```

The stubs of each terminal of `strip` opened on `unit`'s level, in strip order.

A terminal wired to an item outside `unit` has one stub per far end, as the level's stubs are
named (`stub_far_end`), standing at the terminal. A terminal with none has an empty tuple.

### strip_view

```python
def strip_view(model: Model, strip: Id[Item], unit: Id[Unit]) -> StripView
```

`strip` opened on `unit`'s level: its terminals in strip order, each with its lines.

Strip order is the terminal's group (natural order) then its index. A line runs from the
terminal to the box on the other end, left out when that end is the strip itself or lies
outside `unit`.

### stub_ends

```python
def stub_ends(model: Model, unit: Id[Unit], placed: Sequence[tuple[OverviewRef, OverviewStub | FoldStub]]) -> tuple[tuple[StubBox, ...], tuple[StubLine, ...]]
```

The stub boxes and lines of `placed`, each stub with the box `at` it hangs on.

A box holds the first stub's far text, then the port tails of all its stubs once each, in order.
Counts add per kind and carrier; a line's text is `overview_end_text`, or `x N` to a closed
fold (N its distinct cables when it is a cable fold). Both keep first-seen order.

### subject_kind

```python
def subject_kind(subject: Id[Record]) -> SubjectKind
```

What `subject` names: an item, port, function, conductor, unit or location node, else other.

Example: the id of an item gives `SubjectKind.ITEM`; the id of a net gives `OTHER`.

### subject_kind_text

```python
def subject_kind_text(subject: Id[Record]) -> str
```

The kind text of `subject`'s handle (`"net"`, `"item"`, ...), as an error names it.

### subject_label

```python
def subject_label(model: Model, document: Id[Document]) -> str
```

The heading's subject: location, unit or item label; "" for SYSTEM.

`document` is the document's id.

### subject_marks

```python
def subject_marks(model: Model, rows: ViewRows, lookup: dict[RefKey, int], subject: Subject) -> tuple[tuple[int, ...], tuple[int, ...]]
```

`(boxes, lines)` indexes of `rows` the subject counts on; the lines when it has any.

`lookup` is `view_lookup(model, rows)`. A cable item counts on its own lines, a conductor on
the line between its two boxes; else the subject counts on each distinct box of its ends.

### subject_part_mpn

```python
def subject_part_mpn(model: Model, subject: Id[Record]) -> str | None
```

The mpn of the part of an item, or of a function's item; `None` when it has no part.

### subtree

```python
def subtree(model: Model, node: Id[AspectNode]) -> tuple[Id[AspectNode], ...]
```

Every descendant of `node` by `AspectNode.parent`, `node` excluded, sorted by id.

Follows `parent` whatever the aspect (`ASPECT_CROSS_PARENT` is the validator's) and is
cycle-safe.

Args:
    model: The model to read.
    node: The aspect node whose descendants are listed.

Returns:
    Every descendant's id, sorted.

Raises:
    SchemaError: `node` is not an aspect node of `model`.

### supply_share

```python
def supply_share(model: Model, function: Id[Function]) -> Fraction
```

The share of `function`'s connected pins that carry a supply potential, 0 with none.

A pin carries a supply when `port_potential_rank` gives it a rank: a rail, 24 V or GND. It is
a rank, not a direction, since a potential cannot tell "fed by" from "feeds". Layout calls
it to split a unit's interfaces between its two edges and never asks again.

### supply_systems

```python
def supply_systems(model: Model) -> frozendict[Id[SupplySystem], SupplySystem]
```

Return every `SupplySystem` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `SupplySystem` in `model`, keyed by id; the model's own table, so nothing
    is copied. Empty when the model holds none.

### symbol_port_subject

```python
def symbol_port_subject(model: Model, function: Id[Function] | Id[Item], port_name: str) -> Id[PortTemplate] | Id[Part] | Id[Function] | Id[Item]
```

The `PortTemplate` of `function`'s template named `port_name`, else its `Part`, else itself.

`function` is a Function of the model, or the whole Item of a one-view draw (no template).

### system_has_no_top_level_cables

```python
def system_has_no_top_level_cables(model: Model, document: Id[Document], cables_found: tuple[HarnessCable, ...]) -> bool
```

A SYSTEM document whose model has no top-level cable at all.

`document` is the document's id.

### tag_text

```python
def tag_text(model: Model, function: Id[Function]) -> str
```

A TAG label's text: the designation the layout engine used.

A terminal function's tag is the designation of its lowest-handle port; every other
function's tag is its item's `item_tag_text`.

### takes_energy

```python
def takes_energy(model: Model, function: Id[Function]) -> bool
```

Whether `function` takes energy in: its role's `energy` (a load, actuator, coil or `in`).

An energy-in function (a load, a motor, a coil, or a supply declared `energy = in`) sits above
an energy-out one.

### takes_parents_designation

```python
def takes_parents_designation(model: Model, item: Id[Item], *, held_switches: bool=True) -> bool
```

Whether `item` is an accessory: it prints its parent's designation, having none of its own.

True for a part-bearing item with no own text, terminal facet, board or harness role, whose
`parent` is a designated part-bearing item (an own text, or a part class code), not a
terminal, enclosing board or harness. A footprint part, or a function in the subtree (a
device, but not an add-on contact block), makes `item` a part of its own. Unknown: `False`.

Args:
    model: The frozen model to read.
    item: The item to classify.
    held_switches: `False`: no contact block of held switches (before 0.18.2).

Returns:
    `True` if `item` is an accessory that prints its parent's designation.

### terminal_items

```python
def terminal_items(model: Model) -> frozenset[Id[Item]]
```

Every item that carries a `terminal` facet, built once per model digest.

### terminal_rows

```python
def terminal_rows(model: Model, strip: Id[Item], *, unit: Id[Unit] | None=None, context: Id[AspectNode] | None=None) -> tuple[TerminalRow, ...]
```

One `TerminalRow` per `strip` terminal, by `(natural_key(group), index, id)`.

Args:
    model: The model to read.
    strip: The terminal strip item whose rows are built.
    unit: The unit whose own document prints the list, keyword-only; `None` for none.
    context: The location node the list prints for, keyword-only; ignored once `unit` has one.

Returns:
    One `TerminalRow` per terminal child of `strip`, sorted.

Raises:
    SchemaError: `strip` is not an item of `model`, or a far end's item has no designation.

### terminal_strips

```python
def terminal_strips(model: Model) -> tuple[Id[Item], ...]
```

Every item that at least one `terminal` facet names as its strip, in designation order.

A terminal's strip is its parent item: `TerminalFacet` carries no strip field of its
own. Shared by `fransys`'s export enumeration and the
pdf document contents, so the two never disagree about what a
strip is.

Args:
    model: The model to read.

Returns:
    Every strip item's id, by natural designation, then id.

### text_room

```python
def text_room(model: Model, unit: Id[Unit] | None=None) -> int
```

The grid units a text line gets under `unit`'s profile (`None`: the top) and its sheet.

The one reader of the profile and sheet for the text room; sizes come from `text_room_g`.

### text_room_g

```python
def text_room_g(text_height_mm: Decimal, module_mm: Decimal) -> int
```

The grid units a text of capital height `text_height_mm` gets: font size over one G, up.

### text_under_floor

```python
def text_under_floor(profile: Profile) -> Decimal | None
```

The capital height of `profile`'s text when it is under `min_text_height_mm`.

### text_width_mm

```python
def text_width_mm(text: str, *, size_mm: float, bold: bool=False) -> float
```

The width of `text` in DejaVu Sans Condensed at `size_mm`, from the one table.

### title_block_overflows

```python
def title_block_overflows(model: Model, document: Id[Document], sheets: DocumentSheets, rooms: Mapping[str, float]) -> tuple[TitleBlockOverflow, ...]
```

The fields that miss their cell: the six document-level ones, then each checked page's.

### title_block_strings

```python
def title_block_strings(fields: TitleBlockFields, rooms: Mapping[str, float], sizes: Sizes, *, notice_width_mm: float, notice_capacity: int) -> TitleBlockStrings
```

What the title block prints: each field cut to its slot's room, the notice wrapped.

### top_level_cables

```python
def top_level_cables(model: Model) -> tuple[HarnessCable, ...]
```

Every cable item with no unit, harness cables included, as `HarnessCable`.

Selected as `cable_list_rows` selects (`_top_level_cable_ids`): every cable item
(`is_cable`) with `unit=None`, a cable inside a harness included. Built by
`_cable_facts`, as in `harness_cables`. Sorted by `(designation, id)`.

Args:
    model: The frozen model to read.

Returns:
    Every top-level cable (`unit=None`), sorted by `(designation, id)`.

Raises:
    SchemaError: a cable, or an item one of its cores lands on, has no designation.

### unconnected_ports

```python
def unconnected_ports(model: Model) -> tuple[Id[Port], ...]
```

Every port whose physical net is a singleton, in id order (`physical_nets` is sorted).

A conductor, a `conductive` link or a `Mate` reaching a port connects it; a declared
`Net` does not, deliberately unlike `FUNCTION_HALF_CONNECTED`, which is about authoring intent.

Args:
    model: The model to read.

Returns:
    Every port with no other port on its physical net, sorted.

### unit_boards

```python
def unit_boards(model: Model, unit: Id[Unit]) -> tuple[Id[Item], ...]
```

The boards `unit` owns directly, in designation order, never a nested unit's.

The boards of `boards` whose `item.unit` is `unit`; the one test of a unit's own boards.

### unit_boundary_pins

```python
def unit_boundary_pins(model: Model, unit: Id[Unit] | None) -> tuple[Id[Port], ...]
```

The ports of `unit`'s boundary functions: functions in `Id` order, pins in pin order.

### unit_cables

```python
def unit_cables(model: Model, unit: Id[Unit]) -> tuple[HarnessCable, ...]
```

Every cable item that belongs to `unit` itself, as `HarnessCable`.

Cables whose own `Item.unit` is `unit`, not a nested unit's, read unit-relative:
an end outside a NESTED `unit` has `designation == ""`.

Args:
    model: The frozen model to read.
    unit: The unit whose own cables to list.

Returns:
    Every cable whose `Item.unit` is `unit`, sorted by `(designation, id)`.

Raises:
    SchemaError: `unit` is not a unit, or a cable or core end has no designation.

### unit_chain

```python
def unit_chain(model: Model, unit: Id[Unit]) -> list[Id[Unit]]
```

`unit`, its parent, its parent's parent, ... up to the top-level ancestor.

Cycle-safe: a repeat ends the walk (`UNIT_CYCLE` is the validator's, not this query's).

### unit_chain_below

```python
def unit_chain_below(model: Model, unit: Id[Unit] | None, subject: Id[Unit]) -> list[Id[Unit]]
```

`subject` and its parents up to, not including, `unit`; `None` goes to the top.

### unit_connector_items

```python
def unit_connector_items(model: Model, unit: Id[Unit]) -> tuple[Id[Item], ...]
```

The `connector_items` `unit` owns directly, never a nested unit's (as `unit_boards`).

### unit_ids

```python
def unit_ids(model: Model) -> tuple[Id[Unit], ...]
```

Every unit id, sorted.

### unit_index

```python
def unit_index(model: Model) -> UnitIndex
```

The `UnitIndex` of `model`, built once per digest and kept for the last few models.

Every field holds ids only and is immutable, so a caller may keep or share it freely.

### unit_items

```python
def unit_items(model: Model, unit: Id[Unit]) -> frozenset[Id[Item]]
```

Every item of `model` whose `unit` is in `unit_subtree(model, unit)`.

Reads the per-model unit index.

Raises:
    SchemaError: `unit` is not a unit of `model`.

### unit_key

```python
def unit_key(model: Model, unit: Id[Unit]) -> tuple[str, ...]
```

The authoring key of `unit`.

### unit_location

```python
def unit_location(model: Model, unit: Id[Unit]) -> Id[AspectNode] | None
```

The location node `unit` is placed at: its root items' location, else their common ancestor.

The roots are `unit_own_roots` (external items left out), each
read at its `effective_placement` in the location aspect. One
location for all of them is that node; several are their nearest common ancestor in the
location tree; `None` when no root is placed or the roots' locations share no ancestor.
The context every list of a unit document prints its ends against.

### unit_matrix

```python
def unit_matrix(model: Model) -> UnitMatrix
```

Every system-level box against every other, with the cables.

The axis is the system level's boxes in box text order, less every unit's field devices
(`field_devices`). A cell has `row < col` and counts the
distinct cables whose lines join those two boxes; a pair with no cable has no cell. The
counts come from the same lines the system level draws, so the matrix cannot disagree.

### unit_name_unresolved

```python
def unit_name_unresolved(model: Model, name: str) -> str
```

The one sentence for a `unit_name` that does not resolve to exactly one unit.

Called only when `units_named(model, name)` is not exactly one match. Three cases, each
ending with the same advice: no release has `name` (says so and names the release names
the model does have, or that it has none); releases of `name` exist but no instance is in
the model (names their versions and revisions); several instances match (names each, with
its release's version and revision and, if it has a parent, where it sits).

Example: `unit_name_unresolved(model, "relay-board")` with no such release returns
`"no unit release is named 'relay-board'; the model has 'io-board'. Build the unit alone,
or pass the instance's scope."`

Raises:
    ValueError: `name` has exactly one matching unit; there is nothing to report.

### unit_own_drawing

```python
def unit_own_drawing(model: Model, unit: Id[Unit]) -> str
```

The drawing set of a unit's own panel line: its box text, then "in" and its release.

### unit_owned_ids

```python
def unit_owned_ids(model: Model, unit: Id[Unit]) -> frozenset[Id[Record]]
```

Every id `unit` owns: its subtree's items, functions, ports, units and its documents.

### unit_racks

```python
def unit_racks(model: Model, unit: Id[Unit] | None) -> tuple[Id[Item], ...]
```

The racks (`plc_racks`) of `unit`, id-sorted; every rack for `unit=None`.

### unit_release

```python
def unit_release(model: Model, unit: Id[Unit]) -> UnitRelease
```

The `UnitRelease` record `unit` is an instance of, the one reader of its release facts.

Raises:
    SchemaError: `unit` names no `Unit` of `model`.

### unit_releases

```python
def unit_releases(model: Model) -> frozendict[Id[UnitRelease], UnitRelease]
```

Return every `UnitRelease` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `UnitRelease` in `model`, keyed by id; the model's own table, so nothing is
    copied. Empty when the model holds none.

### unit_strips

```python
def unit_strips(model: Model, unit: Id[Unit]) -> tuple[Id[Item], ...]
```

The terminal strips `unit` owns directly, in designation order, never a nested unit's.

The strips of `terminal_strips` whose `item.unit` is `unit`; one test of a unit's own strips.

### unit_subtree

```python
def unit_subtree(model: Model, unit: Id[Unit]) -> frozenset[Id[Unit]]
```

`unit` and every unit whose `parent` chain reaches it.

Cycle-safe, like `derive.structure.subtree`. Reads the per-model unit index.

Raises:
    SchemaError: `unit` is not a unit of `model`.

### unit_system_designation

```python
def unit_system_designation(model: Model, unit: Id[Unit]) -> str | None
```

The unit named from the system level, tags joined (`-R1-A2`); `None` when untagged.

### units

```python
def units(model: Model) -> frozendict[Id[Unit], Unit]
```

Return every `Unit` in `model`, by id.

Args:
    model: The model to read.

Returns:
    Every `Unit` in `model`, keyed by id; the model's own table, so nothing is
    copied. Empty when the model holds none.

### units_named

```python
def units_named(model: Model, name: str) -> tuple[Id[Unit], ...]
```

The ids of every `Unit` instance of a release named `name`, in id order.

Every version and revision of that name counts; an id order that does not depend on
hash order (the tie-break).

Example: two `UnitRelease`s named `"relay-board"` (`1.1` and `1.2`), one `Unit`
instance of each: `units_named(model, "relay-board")` returns both ids, sorted.

### unused_terminals

```python
def unused_terminals(model: Model, strip: Id[Item]) -> tuple[Id[Item], ...]
```

Terminal children of `strip` with no conductor on any port, sorted by id.

Args:
    model: The model to read.
    strip: The terminal strip item whose unused terminals are listed.

Returns:
    Every unused terminal child's id, sorted.

Raises:
    SchemaError: `strip` is not an item of `model`.

### view_lookup

```python
def view_lookup(model: Model, rows: ViewRows) -> dict[RefKey, int]
```

Each drawn box's index by its reference; a place box also by each member it holds.

### wire_rows

```python
def wire_rows(model: Model, *, unit: Id[Unit] | None=None, context: Id[AspectNode] | None=None) -> tuple[WireRow, ...]
```

One `WireRow` per `wire`-faceted `WIRE` conductor no harness carries, by `(from, to, id)`.

A jumper, a cable core, a link and a harness wire never get a row. `from`/`to` are
the ends as the list prints them (`unit` and `context` act the same); `label` is `wire_text`.

## Classes

### Aspect

```python
class Aspect
```

One of the three IEC 81346 views of the same objects.

Example: `-K1` is a `PRODUCT` designation; `+C1` is a `LOCATION` node.

### AspectNode

```python
class AspectNode
```

A node in one IEC 81346 aspect tree.

Example: `+C1` is a `LOCATION` node with `label="C1"`; a `PRODUCT` tree node
`-K1` groups the relay example under an enclosure. Guarded by
`validators.structure` (`ASPECT_CYCLE`, `ASPECT_CROSS_PARENT`).

### AssignedSeed

```python
class AssignedSeed
```

An unauthored item a pin still matches and the pin's text for it; `key` is the item's.

### BoardNetlist

```python
class BoardNetlist
```

A board's parts, footprints and nets: one more Fransys output.

`without_footprint` are the board's descendants with a part whose part carries no
`footprint`: the parts a netlist cannot place, which the query omits from `parts`. An accessory,
which prints its holder's designation, is no part of its own and is never listed.

### BoardPins

```python
class BoardPins
```

A board's nets with every pin resolved, and the pins of its parts that are in no net.

### BomLine

```python
class BomLine
```

One BOM line, by `Part`, `installed` non-external items only; or one nested unit.

`mpn`/`manufacturer`/`description` are `Part`'s own fields, projected here
so a formatter never looks the part back up. A unit line has `part=None`,
the unit's name in `mpn`, an empty `manufacturer`, and its own `revision`, printed as
`revision_text` (`"1.1"`); `revision` is `""` on every part line. A unit line's
`designations` are per instance: its one root item's designation, else its location
(`"+C1"`), else its root items' (`bom_lines`).
Every designation a line prints carries its sign (`"-K1"`, `"-U2"`, `"-X1:L1:1"`,
`"+C1"`).

### Boundary

```python
class Boundary
```

A function that is part of a unit's interface.

Example: `u.boundary(x1)` in `io_board` makes connector `X1` the board's
interface. One function may be the boundary of several units, for a board
connector that is also its cabinet's external connector.

`name` is the NamedTuple field name the unit's interface gave this function, or None; it is
for the box's name line.

### BoxPair

```python
class BoxPair
```

One function and the one function of another item it is wired to, pin to pin.

Attributes:
    function: The function the pairing is read for.
    partner: The function of another item that every port of `function` reaches.
    port_pairs: `(port of function, port of partner)`, in the order of `function`'s ports.

### BridgePiece

```python
class BridgePiece
```

One drawn Bridge mark piece (`bridge_piece_key`): its SVG and its size in mm.

The SVG is `width_mm` by `height_mm`; pdf places it in a row's cell and, for a lane's `line`
only, stretches it on y to the rows the lane covers.

### CableBlockRef

```python
class CableBlockRef
```

One cable block of a run: its `svgs` key, its run's part number and that run's part line.

### CableBlockSize

```python
class CableBlockSize
```

A laid-out cable block's `width` and `height` in G, and the `module_mm` of its sheet.

### CableListRow

```python
class CableListRow
```

One top-level cable of the system document's cable list.

`mpn`, `description`, `core_count`, `gauge_mm2` and `length_mm` are `HarnessCable`'s own
facts, `None` where the part or facet is absent. `designation` is the cable's
`printed_designation` (`"-W1"`). Ends are ordered by `cable_end_rank` (a unit member first),
so a cable authored either way round reads the same way round. `from_label` is the first end's
`HarnessEnd.designation`, the text the drawing prints. `to_label` lists every other end's
designation in that order, joined by `", "`. With one end `to_label` is `""`, with none
both are. `pairs` is the number of twisted pairs of the product, `None` for a product with none.

### CableRow

```python
class CableRow
```

One core of one cable, both ends.

### CableRun

```python
class CableRun
```

One part run: its heading (the part number, or `NO_PART`) and its blocks in their order.

### CdpRackModule

```python
class CdpRackModule
```

A channel-bearing rack module with what CDP's module name is made of.

`ordinal` counts the channel-bearing modules of the same `mpn`, in rack order, from 0.
`single_signal` is the one `SignalType` all its channels share, `None` when they differ.

### ChannelScaling

```python
class ChannelScaling
```

The `scaling` facet of a field device, projected so a formatter never looks it up.

### Conductor

```python
class Conductor
```

Realisation: an exactly-two-ended physical connection.

Example: one core of the invented cable `W012` example is
a `Conductor(kind=CORE, carrier=<the cable item>)` between a transmitter's port and
a terminal's `EXTERNAL` port. `a`/`b` are stored in id order; direction is not a
fact.

Net membership lives only in `Net.ports`: a conductor carries
no net of its own. Guarded by `validators.connectivity` and `validators.cables`.

### ConductorKind

```python
class ConductorKind
```

What physical realisation a `Conductor` is.

Example: a panel wire is `WIRE`; one core of the invented cable `W012` example
is `CORE`; a bridge between two terminals is `JUMPER`.
`JUMPER`, `MOUNT`, `BUSBAR`, `RAIL` and `LEAD` are links: a bridge between terminals,
plug-on contacts, a rack's power jumper, terminals bonded through their rail, a device's own
lead ending in a pin of a fitted connector. A link joins its net and is never a wire: it has
no `WireFacet`.

### ConnectorPin

```python
class ConnectorPin
```

One pin of a board connector, the net on it and the pin it mates with.

`marking` is the port's name. `net` is the name of the declared net that lists the port,
named as `board_netlist` names its nets; `None` when no declared net lists it. The mate's
pin is the port of equal name on the mated function (a `Mate` carries no pin map).
`ends` are the far ends of every conductor on the pin or its mate, as `far_ends` prints them.

### ConnectorRow

```python
class ConnectorRow
```

One connector of a board, as listed by `connector_rows`.

`designation` and `mate_designation` are `connector_designation`: the connector's own item's
designation, plus `-<label>` when that item carries two or more labelled connector functions
(`-JB1-J1`; a device's connectors print as sub-parts); an item with one never shows it.
`style`, `pincount` and `gender` are
the `connector` facet of the function's template, projected here so a formatter never looks
them up; `gender` is `None` when the part file states none. `mate` is
the connector plugged into this one, `None` when unmated.

### ContentsRow

```python
class ContentsRow
```

One cable of a document's CONTENTS page.

`mpn`, `description`, `core_count`, `gauge_mm2` and `length_mm` are `HarnessCable`'s own
facts, as in `CableListRow`. `designation` is the cable's `printed_designation` (`"-W1"`).
`ends` is every end's `designation` in the cable's end order, joined by an en dash, a blank
end (outside a nested unit) dropped with its dash; unlike `CableListRow` it keeps
every end. It is text, not a tuple, so `cell_text` cannot join it with `CELL_SEPARATOR`.

### CoreListRow

```python
class CoreListRow
```

One line of the core list: a core with its ends, its pair word and its spare mark.

Every text is a field of a `CableRow` or an `OpenCoreRow` or `core_pair_word`; `""` is none.

### CurrentBound

```python
class CurrentBound
```

The most continuous current of `kind` that reaches a position: `value`, set by `by`.

`states` names the items the bound depends on: among the item assignments that give this
same bound (value, setter and role), the (item, `rest` or `operated`) of each enumerated
item that is in the same state in ALL of them (`current_states`), sorted by item id. An item
that varies between such assignments does not matter and is not named; empty when none does.
`ports` are the two end ports of the position whose limit set the bound.

### CurrentChain

```python
class CurrentChain
```

The positions of one block of the current graph, in the order `derive.current_chains` gives.

The graph has every switched link closed. A position it shorts, but that exists in some
state, is a chain alone.

### CurrentPosition

```python
class CurrentPosition
```

One rated current path: the functions it passes through, sorted, and its bounds.

`bounds` holds at most one `CurrentBound` per current kind, AC before DC: the highest, over
the item states in which the position exists and has one, of the smallest limit the law lets
reach it, with the function that set it and the item states that give it. `ports` are the
position's two end ports, its identity when equal `functions` repeat (one per pole).

### DesignationMove

```python
class DesignationMove
```

One pin source entry still matched by a current item: its OLD and CURRENT own label.

### DesignationRow

```python
class DesignationRow
```

One line of the tag/designation list (`designation_list`).

### DiffMark

```python
class DiffMark
```

One box or line of a view that a `ListingDiff` marks, with the status the page prints.

`at` indexes the view's `boxes`, or its `lines` when `on_line`. `status` is `added` or
`changed`.

### DiffRest

```python
class DiffRest
```

One row no box or line of any view carries: its `status` and the subject text.

### DiffViewMarks

```python
class DiffViewMarks
```

The marks one view takes from a diff: boxes then lines by index, and the rows that marked.

`shown` holds the indexes in `ListingDiff.changes` of the rows that marked a box or line.

### DocumentRow

```python
class DocumentRow
```

The fields of one `Document` an output reads.

`location` and `item` are the subject's ids (the `SYSTEM` preset has neither), `cover` and
`notes` the Markdown texts (`notes` is `None` when dropped) and `logo` the title block's SVG.

### DocumentScope

```python
class DocumentScope
```

The selections one `Document` makes, each read once from its subject.

- `unit`: `document_unit`, the unit every reading uses; the `SYSTEM` preset has none.
- `cables`: the `HarnessCable`s the drawings show (`SYSTEM`: the top-level ones, a unit: its
  own, an item: its cable children, a location: none); `harnesses`: the harness items with
  single wires the drawings add.
- `bom_location`, `bom_item` and `bom_top_level` make `bom_scope`, the scope `bom_lines` takes:
  the unit, else `TOP_LEVEL` for the system, else the location, else the item.
- `bom_without`: the harness items a location document does not draw, with all they own;
  `bom_lines` leaves them out (`without=`) and `connector_items` omits them.
- `strips`: the terminal strips a terminal list covers; `connector_items`: the items a
  connector list covers for a unit or a location; `boards`: a board document's board.

### DocumentSheets

```python
class DocumentSheets
```

A document's paper, its sizes, its pages' title blocks in page order, each paper's frame.

### ExportRow

```python
class ExportRow
```

One file a write makes, before it is placed in `data/`.

- `export_kind`: `"bom"`, `"plc"`, `"wires"`, `"designations"`, `"cables"`, `"cores"`,
  `"overview"`, `"terminals"`, `"connectors"`, `"wago"` or `"pdf"`; `extension` ends the name.
- `subject`: the strip, board, rack or document id; `None` for a whole-model report.
- `name`: `export_name` or `document_export_name`; `hint` the unit-set name a clash of two
  units of one release should keep one document of, else `None`.

### ExtUsage

```python
class ExtUsage
```

One `(kind, key)` pair still stored in some record's escape-hatch `ext` field.

Not a Fransys output format: read by whoever maintains this repo to decide what
to promote to a real field next, keeping `ext` honest (kernel-records.md 5.3 and
derive-queries-structure.md).

### Extent

```python
class Extent
```

A box in G, in the frame of the symbol's body: top-left `x`, `y` and its size.

### FieldFold

```python
class FieldFold
```

One unit's field devices folded into a box beside it: its text, members and cables.

`unit` is the top-level unit box all their connections land in; `cables` join them to it, and
`joins` are the lifted lines of the fold to it, one per kind.

### FieldJoin

```python
class FieldJoin
```

One lifted line of a field box to its unit: a kind, its cables and its count.

### FieldOverflow

```python
class FieldOverflow
```

One field whose text missed its cell: the field name and the base text that did not fit.

### FindingHold

```python
class FindingHold
```

One finding that counts on a mark: its index in the findings given, and its severity.

### FindingMark

```python
class FindingMark
```

One box or line of a view that findings name.

`at` indexes the view's `boxes`, or its `lines` when `on_line`. `held` lists each finding
that counts there, in the order the findings reached it.

### FoldBox

```python
class FoldBox
```

One box of a folded level.

`lines` is its text. A `GROUP` counts its `items`, nested `units` and `strips`, and
`inner_lines`, the connections between its own boxes. `STRIPS` counts the `strips` it holds.
`item_kind` is an item box's kind, `terminals` a strip box's or `STRIPS`' terminal count.

### FoldLevel

```python
class FoldLevel
```

A unit level folded to function groups, or one group or the strips box opened.

`opened` is the `GROUP` or `STRIPS` box opened as the level, `None` for the folded level and
for a unit with fewer than two groups, which opens straight (`folded` false) with all its
boxes. `strips` lists each strip the level holds or passes through, in designation order.
`wires` is, for the strip opened in it, each terminal's share of the stubs its terminals hold
together; empty with no strip open.

### FoldLine

```python
class FoldLine
```

One line of a folded level, per pair of boxes and kind, or per strip passed through.

`count` is the connections it stands for, `vias` the cable items of a cable line. A line
drawn through a strip has `strip` set, `terminals` the terminals it stands for and `label` as
`-X3 x 3`; otherwise `label` joins the cable designations, "" for none.

### FoldStub

```python
class FoldStub
```

The outside end of connections at a box, folded by far end.

`far` names the group, box, unit or location, or for `END` the far device as `stub_far_end`
prints it; `end` is the same far end as a reference (a group, a box's own, a unit, a place or
the far item). `kind` and `via` are the line's: a stub folds per kind, and `via` is set only
for `END`. `count` is the connections. `members` are the single stubs it opens to:
those of an outside fold, the stub itself for `END`, empty inside the unit.

### Footprints

```python
class Footprints
```

The room a symbol takes: `standalone`, and `in_strip_row` without the strip's shared tag.

### FrameLabels

```python
class FrameLabels
```

The reference labels of a frame: column numbers left to right, row letters top down.

### FrameStrip

```python
class FrameStrip
```

One reference strip of a sheet frame in mm: its corner, one cell's size and its labels.

`side` is `top`, `bottom`, `left` or `right`; the cells run along `axis`, one per label.

### Function

```python
class Function
```

One electrical function of one item: the unit Fransys draws as a symbol.

Example: the relay `-K1` example has a `coil` `Function` drawn on the control
page and a `co_1` `Function` drawn on the power page; both reference the same
`item`. Guarded by `part_conformance` when `template` is set.

### FunctionKind

```python
class FunctionKind
```

What kind of `Function` an item exposes.

Example: the relay `-K1` example has one `COIL` function and `CONTACT_NO`/
`CONTACT_CO` functions for its contacts. A `BAR` is a conductor bar sold as one product.

### HarnessCable

```python
class HarnessCable
```

One cable of a harness with its product facts, cores and ends.

`mpn` and `description` are the cable `Part`'s; `core_count`, `gauge_mm2` and `shielded` are
its `cable_product` facet; `length_mm` is the item's `cable` facet. Each is `None` where the
part or the facet is absent. `designation` is the cable's `printed_designation` (`"-W1"`),
the text the drawing's cable node title prints. `open_cores` are the cable's spares and
one-ended screens (`open_core_rows`), which have no conductor and so are not in `cores`.

### HarnessCore

```python
class HarnessCore
```

One core of a harness cable: the facts of a `CableRow`, plus the label its wire carries.

`label` is the label of the `wire` facet of the core's conductor, `None` when it has none.
`end_a`/`end_b` are `CableRow`'s own -- `cable_rows` itself orients every core of one cable
to run from its one lower-ranked end to its one higher-ranked end
(`cable_end_rank`, a unit member first; `cable_end_owner`), not `Conductor.a`/`.b`'s raw
port-id order, so `end_a` is always the same physical end for every core that lands on it.

### HarnessEnd

```python
class HarnessEnd
```

One item a core lands on: a connector housing, a plain device, or a strip of terminals.

A core that lands on a terminal with a parent lands on that terminal's strip instead:
`item` is the strip and `pins` holds one `HarnessPin` per landed
terminal port, marked by the terminal's own bare designation (`"L1:1"`,
not dashed or strip-prefixed here) rather than a raw port name. `designation` is the item's
`product_designation` for every end: a strip, a connector plug
or a plain device alike, e.g. `"-X1"` unplaced, `"+C1-X1"` or `"+EXT-M1"` placed, never with
a function segment; the same text the terminal list prints and the cable list's
`from_label`/`to_label` repeat. The connector fields (`connector`, `style`, `pincount`,
`gender`) are filled from the `connector` facet of a connector function of the item that a
core lands on, and are `None` for a plain device or a strip alike (a strip is never itself a
`connector`-kind function). Any other end -- a connector or a plain device -- has `item` the
device itself and `pins` one per landed port, marked by the port's own name.

### HarnessLineEnd

```python
class HarnessLineEnd
```

One end of a harness or cable line: `plug` is its connector function, else `ports` fan out.

`branch` is the 1-based n of `-W13.n`. `mates` is the function `d.mate` joins `plug` to, or
`None` for a fan-out or an unmated plug.

### HarnessPin

```python
class HarnessPin
```

One port of a harness cable's end that a core of that cable lands on.

`marking` is the port's own name, except for a port of a terminal with a parent (its end
is grouped by strip): there it is the terminal's own bare `group:index`
designation (`"L1:1"`), never dashed or strip-prefixed -- the end's
own `designation` already names the strip, dashed (`product_designation`), and every
consumer that draws a pin next to its end joins the two itself, so a dashed, strip-prefixed
marking here would print the strip twice.

### Indexes

```python
class Indexes
```

Every lookup table `derive` needs more than once, built together off one `Model`.

Each maps a record to the ids that refer to it, in `Id` order; a record nothing refers to
has no entry, so read one with `.get(key, ())`. `facets_by_subject` holds facets of every
kind, found through the `subject` field their kind declared.

Not a `@value`: it is never nested in a record, and its tables are keyed by `Id`,
outside the closed set `@value` enforces.

Never stored in the model: call `build_indexes` again, or rely on
its per-digest cache, rather than threading an `Indexes` value through a pass.

### Item

```python
class Item
```

One physical thing.

Example: the invented relay `-K1` example is one `Item` with `part` set to the
relay `Part`; terminal strip `X03` is an `Item` whose four terminals are child
`Item`s via `parent`. `position` is the physical order within the parent (PLC
slot, place on the rail); it is a fact about the build, not a drawing coordinate.
`tag` is the engineer's authored tag; `tag=None` means "number me". The numbered text
lives in `facet.assigned_designation`, never here. `installed=False` keeps it in drawings and
reservations but drops it from the BOM. `unit` is the unit this item belongs to by
membership, not by key or location; `None` is the integrating
script's own wiring. `external=True`: someone else supplies and owns it; an item is
external if it or any parent-chain ancestor is, see `derive.external`. Guarded by
`part_conformance` (when `part` is set) and `validators.structure` (`CONTAINMENT_CYCLE`).

### ItemKind

```python
class ItemKind
```

What an item is, as the overview colours and filters it.

One value per item. `TERMINAL` is a strip's terminal, `STRIP` the item holding terminals.
`DEVICE` is everything the other eight do not name.

### ItemPage

```python
class ItemPage
```

One drawing page that shows an item: the PDF, the page's destination and its text.

### JumperLane

```python
class JumperLane
```

One jumper group's row span and its lane; `first` and `last` are 0-based row indexes.

### JumperLanes

```python
class JumperLanes
```

Every jumper group's lane, in group-number order.

### KeepWhole

```python
class KeepWhole
```

Each set is drawn together; sets are sorted, so the order is stable.

### LensChannel

```python
class LensChannel
```

One channel of a PLC module for the Signals lens: its signal kind and field device.

The device fields are `None` for a spare channel.

### LensModule

```python
class LensModule
```

One PLC module of the Signals lens with its channels in channel order.

### LimitRole

```python
class LimitRole
```

What set a bound: a source's continuous limit, or a full-range protective device.

### LineRef

```python
class LineRef
```

The identity of a line on a level: its two boxes in text order, its kind and its carrier.

A box is a unit instance or an item id. `via` is the cable item of a cable line, else `None`.

### LineTab

```python
class LineTab
```

The tab text at each end of one cable line, on the box border; `None` for none.

### LoadLimit

```python
class LoadLimit
```

One load edge's draw and the limit that bounds it.

`port` is the star edge's port, `None` for a two-port load or a load that is already a position.

### LocationBox

```python
class LocationBox
```

One top place of the location fold: its text and the system boxes in it.

`place` is the top location node, `None` for the boxes in no place.

### LocationFold

```python
class LocationFold
```

The system level folded by top place; present only with two or more top places.

### LocationLine

```python
class LocationLine
```

The cables between two places: `count` distinct cables, `a` before `b` in box order.

### MateRow

```python
class MateRow
```

One `Mate` of the model, at any level: its two CONNECTOR or TERMINAL functions, with texts.

`a` and `b` keep the authored order of `d.mate`. A designation is the text the connector list
prints for that connector at system level (`connector_designation`).

### MatrixCell

```python
class MatrixCell
```

The cables between two boxes of the matrix: `row` before `col` on the axis.

`row` and `col` index `UnitMatrix.axis`; `count` is the number of distinct cables.

### Net

```python
class Net
```

Declared intent: a set of ports that are one potential or one signal.

Example: a 24V supply net names the PSU `+` port and every load's supply port.
N-ary; `ports` is a set, stored sorted by id. `potential` names the rail this net
is (`"L1"`, `"24V"`, `"0V"`, `"PE"`); `None` is an ordinary net. It is a fact about
the plant, read by wire-colour rules and ladder discovery.

Guarded by `validators.connectivity` (`NET_UNREALISED`, `NET_SHORTED`,
`NET_POTENTIAL_CONFLICT`).

### NetClass

```python
class NetClass
```

What kind of potential or signal a `Net` carries.

Example: a 24V supply rail is `POWER`; a 4-20mA transmitter loop is `SIGNAL`.

### NetlistNet

```python
class NetlistNet
```

One net of a `board_netlist`, by the pins it joins.

### NetlistPart

```python
class NetlistPart
```

One placed part on a `board_netlist` (connectivity.md: the board's netlist replaces SKiDL).

`installed` is the item's own flag: a part not installed stays listed, and the output
decides what to do with it.

### NetlistPin

```python
class NetlistPin
```

One pin: its port and item by id, the component reference and the pad name.

### OffDocumentReference

```python
class OffDocumentReference
```

A printed reference to a page of another document that its text does not name.

`subject` is the label or link marker, `page` the page it stands on, `target` the page it names.

### OpenCoreRow

```python
class OpenCoreRow
```

One open core of one cable: the facts of a `CableRow`, with at most one end.

`at` is the port the one end lands on, `None` when it lands nowhere; `at_designation` is its
printed designation, `""` for none. `spare` is false for a screen (an `SH` core), true for
any other open core.

### Operating

```python
class Operating
```

What a function needs to run and what it is allowed to see; a field is `None` if unknown.

Example: `Operating(nominal_voltage_v=Decimal("24"), min_voltage_v=Decimal("18"),
max_voltage_v=Decimal("30"))` is a 24 V DC input that works from 18 V to 30 V;
`capacity_ah` is set on a battery only. `voltage_ac_v` and `voltage_dc_v` are the supply
the function is built for, `nominal_voltage_v` the value it is specified at, and
`min_voltage_v`/`max_voltage_v` the window it operates in. The model guarantees the types
only. `max_current_ac_a` and `max_current_dc_a` are a source's
continuous current limit, the most that flows through it in either direction, charging
included; they bound the branch the source sits on.
`resistance_ohm`, `nominal_power_w` and `nominal_current_a` are each stated at
`nominal_voltage_v`; only `nominal_current_a`, a load's draw, is read. `fault_current_ac_a`
and `fault_current_dc_a` are a source's prospective current into a bolted fault,
`fault_time_constant_ms` the DC time constant.

### OverviewBox

```python
class OverviewBox
```

One box of a level: a nested unit, a folded strip or an item.

`box` is a unit instance or an item id; `kind` is the item's kind, `None` for a unit.
`lines` is the box text as the block diagram prints it, `tabs` the boundary or connector
designations that stand on its border. `terminals` is a strip's terminal count, else 0.
`group` and `location` are the item's effective function and location nodes.

### OverviewGraph

```python
class OverviewGraph
```

Everything the overview output draws: the items, how they connect, the signals.

### OverviewLevel

```python
class OverviewLevel
```

One level of the overview: the system (`unit=None`) or an opened unit.

### OverviewLine

```python
class OverviewLine
```

One line of a level, lifted from the connections it stands for.

`count` is those connections: conductors, or mates for a mate line. `label` is the carrier's
designation, "" for none. `conductors` is empty for a mate line.

### OverviewLink

```python
class OverviewLink
```

The connections between two items of one kind and one carrier, aggregated.

`a` and `b` are the two items, the smaller id first. `via` is the cable item of a `CABLE`
link, `None` otherwise; `via_designation` is that cable's `printed_designation` (`"-W1"`),
`None` when there is no `via` or the cable has no designation yet. `count` is the number of
conductors, or of mates for a `MATE` link; `conductors` are those conductors in id order,
empty for a `MATE` link.

### OverviewLinkKind

```python
class OverviewLinkKind
```

How two items are connected in the overview: the closed set of kinds.

`WIRE` is a conductor with no carrier, `CABLE` a conductor carried by a cable item, `MATE`
a `Mate` between functions of the two items.

### OverviewNode

```python
class OverviewNode
```

One item of the overview graph.

`designation` is `None` for an item that has none yet: `overview_graph` is the one query that
tolerates it, so an overview of a half-finished design still draws. Otherwise it is
`printed_designation`, behind its sign (`"-K1"`, `"-X1:L1:1"`), as a list prints it.

### OverviewPort

```python
class OverviewPort
```

One port of a signal: its item, the port and its marking (the port's name).

### OverviewSignal

```python
class OverviewSignal
```

One physical net that spans at least two items, for tracing a signal through the overview.

### OverviewStub

```python
class OverviewStub
```

The outside end of connections leaving an opened unit, read as the schematic's stub is.

`box` is the visible box inside the level. `far` is the far device's designation and `ports`
its port tails (`stub_far_end`); `end` is its root item, `count` the connections it stands for.

### PageWires

```python
class PageWires
```

The routes of one page: their `bends` and their total `length_mm`.

### PartFunctionRow

```python
class PartFunctionRow
```

One function a part declares, with the rating it has.

A part with no function template has one row: `template` is `None`, `name` is `""`, `kind` is
`None`, and `rating` is the part's own. Otherwise `rating` is `effective_rating`: the
template's, else the part's.

### PhysicalNet

```python
class PhysicalNet
```

One physical net: a maximal set of ports joined by real connectivity.

Distinct from `vocab.connectivity.Net`, which is declared intent. `ports` is sorted
by id, so two closures over the same physical wiring compare equal regardless of
which port the union-find happened to visit first.

Attributes:
    ports: The net's ports, sorted by id.

### PinNet

```python
class PinNet
```

One net of a board, by the resolved pins it joins.

### PinPosition

```python
class PinPosition
```

A unit's item or instance by structure alone: `(key, scope, code)`, no text yet.

### Placement

```python
class Placement
```

An item occupying an aspect node; at most one per item per aspect.

Example: the relay example's `Item` is placed at product node `-K1` and location
node `+C1` (two `Placement`s, different aspects). Guarded by
`validators.structure` (`PLACEMENT_DUPLICATE`).

### PlcChannelRow

```python
class PlcChannelRow
```

One pin of a PLC channel.

`pin` is its printed designation (`-A2:5`), `channel_name` the
channel's own number, `wired_to` the printed far ends at that port joined with `CELL_SEPARATOR`
(`None` for none). The device fields and `signal_name` are `None` for an unbound channel.

### PlcRackChannel

```python
class PlcRackChannel
```

One channel of a rack module, bound or spare.

The field fields are `None` for a spare channel, as in `PlcChannelRow`; `scaling` is also
`None` for a bound device that carries no `scaling` facet. `name_stem` is the text an output
names the channel after, before its own character set: the field device and its signal name,
else the module's designation and the channel's index in the module.

### PlcRackModule

```python
class PlcRackModule
```

One PLC module of a rack with its channels, for an output that walks the rack in order.

`mpn` and `description` are the `Part`'s, projected as `BomLine` does. `position` is the
item's own `position`, `None` when it was never authored.

### PlcTable

```python
class PlcTable
```

One table of the PLC list: the channels of one controller or module.

`item` carries the channels, `designation` is its printed designation, the table's heading;
`rows` are its `PlcChannelRow`s in list order, never empty.

### Port

```python
class Port
```

A connection point on a `Function`.

Example: the coil `Function` of the relay example has ports `A1` and `A2`.
Guarded by `part_conformance` when `template` is set. `marking` is the part's own
pin marking: `None` means "print the port's name", `""`
means "print nothing", any other string is printed as given. `source_row` is the
part's stated wiring row for the pin, copied from its template, or `None`.

### PortRole

```python
class PortRole
```

What a `Port` is for.

Example: a terminal's two ports are `INTERNAL` (panel wiring side) and `EXTERNAL`
(field cable side); which side a wire lands on is this role, not a drawing side. A
`CONTACT_CO` function's ports are `COMMON`, `BREAK` (the throw it closes at rest) or `MAKE`
(the throw it closes operated), whatever the part's pin names.

### PowerKind

```python
class PowerKind
```

What a physical net is on the drawing: a supply, ground, protective earth or none.

Example: a declared 24 V DC rail is `SUPPLY`, its 0 V rail `GROUND`, a net of class `PE`
is `PE`, an AC rail or a net in no supply is `NONE`.

### ProspectiveFault

```python
class ProspectiveFault
```

The prospective fault current of `kind` at one protective position.

`current_a` is the largest current a bolted fault at either terminal drives through it, over
the item states: `None` when a source counted states none, `0` when no source is counted.
Cable resistance is ignored and parallel runs add, so it errs high; an undeclared feed counts
as no source. `time_constant_ms` is the largest DC time constant of the sources counted, over
the states: `None` for AC, or when a counted source states none. `functions` and `supplies`
are the source functions and the declared supplies counted, sorted.

### Rating

```python
class Rating
```

What a function or a part is rated for; a field is `None` when the datasheet says nothing.

Example: `Rating(voltage_ac_v=Decimal("250"), current_ac_a=Decimal("0.5"))` is a contact
rated 250 V AC and 0.5 A AC, with no DC rating. Voltages are RMS for AC and the highest
permissible potential for DC; currents are the continuous rating, except
`min_breaking_current_a`, the lowest current a partial-range fuse breaks. The model
guarantees the types only; comparing a rating with what the plant does is a check's job.

### ReadabilityPage

```python
class ReadabilityPage
```

What `fr.readability` measures of one schematic page.

`drawing_set` and `number` are as printed. `text_height_mm` is the profile's capital height of
text and `min_text_height_mm` its floor. `fill_percent` is the share of the content box the
drawn content covers, in whole percent. The four counts are the lint findings' own:
`wire_crossings` (two wires of different conductors crossing), `struck_labels`
(`WIRE_OVER_LABEL`), `text_overlaps` (`TEXT_OVERLAP`) and `lone_cells` (`LONE_CELL`).
The references drawn on the page: contact images with the contacts they list, stars with the
branches they name, and page cuts, which name one other page each. `single_*` counts the
images with one contact and the stars with one branch; `single_contact_images_other_page` counts
the single images whose contact is on another page.
`wire_bends` and `wire_length_mm` read the page's routes. A loose symbol has no page.
`contacts_not_drawn` counts image entries that print N/A; `references_off_document`
counts references to another document that name none.

### ReadabilityReport

```python
class ReadabilityReport
```

What `fr.readability` returns: a row for each schematic page, and for each unit.

`loose_symbols` counts the symbols of the whole build that no page draws.

### ReadabilityUnit

```python
class ReadabilityUnit
```

One unit's pages together: counts add up, `text_height_mm` and `fill_percent` are the lowest.

`unit` is `None` for the design's own pages. `min_text_height_mm` is the highest floor of them.
`loose_symbols` is the count of the unit's own loose symbols.

### ReplicaOnlySet

```python
class ReplicaOnlySet
```

A drawing set dropped as holding only black-box replicas: its id and its `location`.

### RevisionRow

```python
class RevisionRow
```

One revision-history entry, as the revision table prints it.

### SeedRows

```python
class SeedRows
```

What a pin source seeds into one unit: assigned items, assigned instances, reserved texts.

`reserved` holds every pin gone or moved, plus the source's own `retired`.

### SheetBackground

```python
class SheetBackground
```

One page background and the two boxes pdf fills, in mm from the page corner.

`svg` is the frame, grid and title block; `counter_box` and `logo_box` are x, y, width and
height of the Page cell's value and of the logo cell, `None` when the band holds no title
block; `title_room_mm` is the width a page title is cut to.

### SheetFrame

```python
class SheetFrame
```

A sheet's frame in mm from the page corner: border, reference strips and title-block band.

`border` is x, y, width and height. The band is `band` high from `band_top`; the title block
is `title_width` wide from the border's left, and the square logo cell starts at `logo_x`.

### SheetGroup

```python
class SheetGroup
```

One sheet format a document's drawn pages name: its `name` and its pages' `numbers`.

### SheetIndexRow

```python
class SheetIndexRow
```

One index row: the sheet text (`3`, `2.3`, `B1`), its title forms and its destination label.

`title` is the longest form and `shorter` the others (`page_title_forms`): the PDF prints
the first that fits, as the title block does. The page cell is not here: Typst reads the
physical page at `destination`.

### SheetKey

```python
class SheetKey
```

One page background's place: the document, the page kind and the page's ordinal in it.

`ordinal` is `None` for a document's no-drawings fallback page.

### SheetPage

```python
class SheetPage
```

One page background: its key, paper and title-block fields (render draws it, pdf places it).

`group` and `where` name the page in a `TITLE_BLOCK_TEXT_OVERFLOW` message; `group` is `""`
for a page whose page-level fields are not checked (a diagram sheet, a no-drawings page).

### SheetRow

```python
class SheetRow
```

A sheet's paper and content box in mm, and its grid `module_mm`: what a page is set on.

### SidelessPins

```python
class SidelessPins
```

Both ends' pins in pin order, and `problem`, the text of why they cannot pair, else `None`.

Does not pick a port: the caller maps each template back to its own port.

### SignalKind

```python
class SignalKind
```

The form and direction of a PLC signal.

### Sizes

```python
class Sizes
```

The four roles' font sizes in mm, for one document's profile `text_height_mm`.

`title_band_mm` is the title-block band at which a label and its value clear each other.

### StripNote

```python
class StripNote
```

A strip beside a level: `terminals` of it held (a box) or passed through (lines).

### StripTerminal

```python
class StripTerminal
```

One terminal of an open strip, with its lines to the level's visible boxes.

### StripView

```python
class StripView
```

An open strip: its terminals in strip order (group, then index).

### StubBox

```python
class StubBox
```

The stub box of one far end `end` at the box `at`: its text lines.

`by_others` is set when `end` is an item that is by others: the box is dashed and its first
line ends `(by others)`, as the system level prints it.

### StubLine

```python
class StubLine
```

The line from `at` to the stub box of `end`, for one kind and carrier, with its text.

### StubPlace

```python
class StubPlace
```

Where a stub's far end lies: a group or box of the unit, a far unit, a location, one end.

### StubWire

```python
class StubWire
```

A terminal's share of a stub it holds with the other terminals of the open strip.

`stub` is the shared stub, hung on the first terminal wired to its far end; `part` is the
connections of one terminal to it, with `box` that terminal. Both name the same far end.

### SupplySystem

```python
class SupplySystem
```

A named supply with its rails, a plant fact beside `Net`.

Example: `SupplySystem(name="400V", current=Current.AC, rails=...)` holds rails `L1`,
`L2`, `L3` and `N`, each named as `Net.potential` names it. Protective earth is not a
supplied rail: a rail carried by a `PE`-class net is earth, at 0 V to earth in every supply.
`earthing` says how the source is earthed. `fault_current_a` is the supply's prospective
current into a bolted fault, `fault_time_constant_ms` its DC time constant (RATINGS-3 R3).
`unit` is the unit that declares it, as `Item.unit` is; `pins` are the ports its call puts
its rails on, sorted by id (RATINGS-3 R6).
Not a `Part`, not an `Item`: it has no designation and no place.

### TerminalRow

```python
class TerminalRow
```

One terminal of a strip's connection list.

An unused terminal has empty `internal`/`external` tuples; bridged terminals share one
`jumper_group` number. `internal_ends` and `external_ends`
are the rendered far-end port designations of those conductors, aligned index for index
with `internal` and `external`: `internal_ends[i]` is where `internal[i]` goes. After those come
the open cores landing there (`-W1 GY spare`), which have no conductor. Given a
`context` location, `terminal_rows` prints an end outside it with its location path in
front (`+EXT-M1:U1`) and one inside it short (`-B12:2/T1`).

### TerminalStubs

```python
class TerminalStubs
```

The stubs of one terminal of an open strip: its connections that leave the unit.

### Throws

```python
class Throws
```

One pole of a changeover: its common port and the throws a switched link joins to it.

`breaks` are the ports the common closes to at rest, `makes` those it closes to when
operated; both sorted by id, so two computations over the same model compare equal.
Example: the invented relay's `co_1` with `11` common, `12` break and `14` make gives
`Throws(common=<11>, breaks=(<12>,), makes=(<14>,))`.

Attributes:
    common: The pole's common port.
    breaks: The ports the common closes to at rest, sorted by id.
    makes: The ports the common closes to when operated, sorted by id.

### TitleBlockFields

```python
class TitleBlockFields
```

One page's title-block content; `sheet_counter` `""` off `SCHEMATIC`.

### TitleBlockOverflow

```python
class TitleBlockOverflow
```

One one-line field whose text missed its cell: the field, where it sits and its base text.

### TitleBlockStrings

```python
class TitleBlockStrings
```

What a title block prints, after the cut.

- `printed`: slot id (`title`, `number`, `revision`, `revision_date`, `customer`, `author`,
  `page_title`, `scope`, `sheet`) to the shown text, cut with `…` when it missed.
- `notice`: the notice's wrapped lines, no more than the cell holds.
- `unfit`: each field that missed its cell; `notice_unfit`: the notice needs more lines.

### TopLevelScope

```python
class TopLevelScope
```

The type of `TOP_LEVEL`: a `bom_lines` scope distinct from `None` and every `Id[...]`.

### TreeRow

```python
class TreeRow
```

One row of the parts tree: a `unit` or an `item` (the other `None`), its `label`.

`parent` is the index of the row it hangs under, `None` for a top row. Rows come in display
order: units first, then items, strips last.

### Unit

```python
class Unit
```

One instance of a released, independently-built component.

Example: `io_board` instantiates one `Unit` per call, all pointing at the one
`UnitRelease` for `demo-io-board`, so a cabinet holding two boards has two `Unit`
records and one release. `release` carries the name, version, revision, interface,
title and number. `parent` is the unit this instance sits in; a subtree is the
unit and every unit whose `parent` chain reaches it. Guarded by `validators.structure`
(`UNIT_CYCLE`). `release`'s own `interface` is now checked at release
(`INTERFACE_NOT_BUMPED`). `tag` is the instance's written tag (`U1`),
`None` to be numbered; `derive.unit_tag` reads the tag.

### UnitMatrix

```python
class UnitMatrix
```

The system-level boxes against each other: the axis in text order, the pairs with cables.

### UnitRelease

```python
class UnitRelease
```

A released, independently-built component: a product as a part is.

Example: `UnitRelease(name="demo-io-board", version=1, revision=3, interface="7",
title="Relay interface board", number="SKX-RIB-2")` is one record however many `Unit`s
instantiate it; its instances are placements, as items are. Its key is `("unit_release",
name, str(version), str(revision))`, so two releases that differ in another field conflict.
`version` and `revision` are ints of 1 or more (`release_version`), printed as
`derive.revision_text` (`1.3`). `interface` is the boundary's version, bumped by hand and
checked at release against every other revision of the name (`INTERFACE_NOT_BUMPED`).
`title` and `number` are the unit's own; `class_code` is the letter its floating instances
number from (`U`); all default to `""`. Read through `derive.unit_release`.

### UnitTagSeed

```python
class UnitTagSeed
```

An untagged instance a pin still matches and the pin's text; `key` is the instance's.

### ViewBox

```python
class ViewBox
```

One box of a view: its key, its text lines and its dash.

`members` are a fold's member rows, which the page lists when the fold is open; empty
for any other box.

### ViewLine

```python
class ViewLine
```

One line of a view: its ends, kind, cable, strip and text; `tab_a`, `tab_b` end tabs.

`tab_a` and `tab_b` are the texts of the tabs the line ends on at its `a` and `b` box, else
`None`.

### ViewMember

```python
class ViewMember
```

One member of a fold: the far end, its text lines and its row text.

It has no position. `text` is the whole row as a stub label, carrier first
(`overview_member_text`): `-W11 → +EXT-M1:PE`.

### ViewRows

```python
class ViewRows
```

One view: its level (`unit`, `level`), `mode`, the one open strip, boxes and lines.

Boxes come in the level's text order, then the stub boxes; lines likewise.

### WireRow

```python
class WireRow
```

One wire of the wire list: its two ends, colour, cross-section and printed label.

## Constants

### ALL_VALIDATORS

```python
ALL_VALIDATORS: tuple
```

### AspectNodeId

```python
AspectNodeId: TypeAliasType
```

### BOM_COLUMNS

```python
BOM_COLUMNS: tuple
```

### BRIDGE_PIECES

```python
BRIDGE_PIECES: tuple
```

### BRIDGE_PIECE_KEYS

```python
BRIDGE_PIECE_KEYS: frozendict
```

### CABLE_LIST_COLUMNS

```python
CABLE_LIST_COLUMNS: tuple
```

### CELL_SEPARATOR

```python
CELL_SEPARATOR: str
```

### CONNECTOR_COLUMNS

```python
CONNECTOR_COLUMNS: tuple
```

### CONNECTOR_LABELS

```python
CONNECTOR_LABELS: dict
```

### CONTENTS_COLUMNS

```python
CONTENTS_COLUMNS: tuple
```

### CONTENTS_LABELS

```python
CONTENTS_LABELS: tuple
```

### CORE_LIST_COLUMNS

```python
CORE_LIST_COLUMNS: tuple
```

### ConductorId

```python
ConductorId: TypeAliasType
```

### DESIGNATION_COLUMNS

```python
DESIGNATION_COLUMNS: tuple
```

### DIAGRAM_TITLE

```python
DIAGRAM_TITLE: str
```

### DocumentId

```python
DocumentId: TypeAliasType
```

### FunctionId

```python
FunctionId: TypeAliasType
```

### HARNESS_DRAWING_TITLE

```python
HARNESS_DRAWING_TITLE: str
```

### ItemId

```python
ItemId: TypeAliasType
```

### LinkState

```python
LinkState: _LiteralGenericAlias
```

### NO_PART

```python
NO_PART: str
```

### NO_PLACE

```python
NO_PLACE: str
```

### NetId

```python
NetId: TypeAliasType
```

### PAGE_HEADINGS

```python
PAGE_HEADINGS: dict
```

### PIN_COLUMNS

```python
PIN_COLUMNS: tuple
```

### PLC_COLUMNS

```python
PLC_COLUMNS: tuple
```

### PRESET_HEADINGS

```python
PRESET_HEADINGS: dict
```

### PRESET_PAGES

```python
PRESET_PAGES: frozendict
```

### PageId

```python
PageId: TypeAliasType
```

### PortId

```python
PortId: TypeAliasType
```

### SCHEMATIC_TITLE

```python
SCHEMATIC_TITLE: str
```

### TERMINAL_COLUMNS

```python
TERMINAL_COLUMNS: tuple
```

### TERMINAL_LABELS

```python
TERMINAL_LABELS: dict
```

### TITLE_BLOCK_LABELS

```python
TITLE_BLOCK_LABELS: frozendict
```

### TOP_LEVEL

```python
TOP_LEVEL: TopLevelScope
```

### UnitId

```python
UnitId: TypeAliasType
```

### UnitReleaseId

```python
UnitReleaseId: TypeAliasType
```

### WIRE_COLUMNS

```python
WIRE_COLUMNS: tuple
```

### WIRE_LABELS

```python
WIRE_LABELS: dict
```
