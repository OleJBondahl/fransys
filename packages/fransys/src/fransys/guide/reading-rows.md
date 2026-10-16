# Reading: rows, columns and printed texts

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page covers `fr.derive`, the facade's read-only layer. It holds the column orders and labels of the list outputs and the row types they are built from. It also holds the row functions, and the texts and order keys every list shares. Use these to read a model yourself and get the same numbers, text and order the outputs print.

## Column and label constants

Each constant is a tuple or a dict of field names. The list outputs read them in order, so a column appears where its name appears here.

- `BOM_COLUMNS` is `('mpn', 'revision', 'manufacturer', 'description', 'count', 'designations')`. It orders the columns of the bill of materials list.
- `CABLE_LIST_COLUMNS` is `('designation', 'mpn', 'description', 'core_count', 'gauge_mm2', 'length_mm', 'from_label', 'to_label', 'pairs')`. It orders the columns of the cable list. The two `*_label` columns are the far-end texts of the cable.
- `CORE_LIST_COLUMNS` is `('cable', 'core', 'colour', 'pair', 'end_a', 'end_b', 'note')`. It orders the columns of the core list. `pair` is the core's pair word, `note` is `spare` for a spare core.
- `DESIGNATION_COLUMNS` is `('designation', 'reference', 'description')`. It orders the columns of the designation list: the printed designation, the full reference and the description.
- `CONNECTOR_COLUMNS` is `('designation', 'style', 'pincount', 'gender', 'mate_designation')`. It orders the connector part of the connector list. Each pin line repeats these fields.
- `PIN_COLUMNS` is `('marking', 'net', 'mate_port_designation', 'ends')`. It orders the pin part of the connector list, after `CONNECTOR_COLUMNS`. One line per pin.
- `CONNECTOR_LABELS` is `{'marking': 'Pin', 'mate_port_designation': 'Mate'}`. It gives the headings of those two columns in the connector table of a PDF.
- `PLC_COLUMNS` is `('pin', 'channel_name', 'signal', 'signal_name', 'wired_to')`. It orders the PLC list, which has one row per pin. The field device is not printed in this list, although the row carries it.
- `TERMINAL_COLUMNS` is `('designation', 'group', 'index', 'internal_ends', 'external_ends', 'jumper_group')`. It orders the terminal list of a strip.
- `TERMINAL_LABELS` is `{'internal_ends': 'Side A', 'external_ends': 'Side B'}`. It gives the headings of the two far-end columns of a terminal list. The CSV file writes them in snake case, as `side_a` and `side_b`.
- `WIRE_COLUMNS` is `('from_', 'to', 'colour', 'cross_section_mm2', 'label')`. It orders the wire list.
- `WIRE_LABELS` is `{'from_': 'from'}`. It changes only the heading of the `from_` column, which the field name cannot hold, so the wire list prints `from`.
- `CELL_SEPARATOR` is `'; '`. It joins the parts of one list cell that holds more than one value, such as several far ends of a terminal. Empty parts are left out.

## Row types

Every row is a frozen record. A row is the one shape an output reads, so the layout and the renderers never look up the model for these facts.

- `CableRow` is one core of one cable, both ends. Fields: `cable`, `cable_designation`, `index`, `colour`, `conductor`, `end_a`, `end_a_designation`, `end_b`, `end_b_designation`. The ends are ports; the designations are their printed text.
- `ChannelScaling` is the scaling of a field device, projected so a formatter never looks it up. Fields: `unit`, `raw_min`, `raw_max` (integers), and `eng_min`, `eng_max` (decimals).
- `ConnectorPin` is one pin of a board connector. Fields: `port`, `marking`, `net`, `mate_port`, `mate_port_designation`, `ends`. The `marking` is the port's name. The `net` is the declared net that lists the port, or `None` when none does. The mate's pin is the port of the same name on the mated function. The `ends` are the far ends of every conductor on the pin or on its mate, as a terminal row prints them; empty when there is none.
- `ConnectorRow` is one connector of a board, as `connector_rows` lists it. Fields: `connector`, `designation`, `style`, `pincount`, `gender`, `mate`, `mate_designation`, `pins`. The `gender` is `None` when the part file states none. The `mate` is `None` when the connector is unmated. The `pins` is a tuple of `ConnectorPin`.
- `DesignationRow` is one line of the designation list. Fields: `item`, `designation`, `reference`, `description`. The `designation` is the printed designation, and `reference` is the reference designation.
- `HarnessCore` is one core of a harness cable, with the label its wire carries. Fields: `conductor`, `index`, `colour`, `label`, `end_a`, `end_a_designation`, `end_b`, `end_b_designation`. The `label` is `None` when the wire has none. Every core of one cable runs from the same physical end to the same other end.
- `HarnessEnd` is one item that a core lands on: a connector housing, a plain device, or a strip of terminals. Fields: `item`, `designation`, `connector`, `style`, `pincount`, `gender`, `mpn`, `pins`. The `designation` is the item's product designation for every end. The connector fields are `None` for a plain device or a strip. When a core lands on a terminal with a parent, `item` is the strip, and `pins` holds one `HarnessPin` per landed terminal.
- `HarnessPin` is one port of a harness end that a core lands on. Fields: `port`, `marking`. The `marking` is the port's own name. For a terminal in a strip it is the bare `group:index` text, such as `L1:1`, without the strip's designation, because the end already prints the strip.
- `PlcChannelRow` is one pin of a PLC channel. Fields: `channel`, `port`, `pin`, `channel_name`, `signal`, `wired_to`, `field_device`, `field_device_designation`, `signal_name`. The `pin` is the pin's printed designation (`-A2:5`) and `channel_name` the channel's own number. The `wired_to` joins the far ends of that pin's conductors with `CELL_SEPARATOR`, or is `None` when nothing is printed. The three field fields are `None` for a channel with no bound device.
- `PlcRackChannel` is one channel of a rack module, bound or spare. Fields: `channel`, `number`, `signal`, `field_device`, `field_device_designation`, `signal_name`, `scaling`, `name_stem`. The field fields are `None` for a spare channel. The `scaling` is `None` when the bound device has no scaling facet. The `name_stem` is the text an output names the channel after: the field device and its signal name, else the module's designation and the channel's index in the module.
- `PlcRackModule` is one PLC module of a rack, with its channels in order. Modules go by `position`, else by their own tag. Channels with one number go by the function names in the part file, in natural order. A block tag never changes the order of racks, modules or channels (model-0259). Fields: `module`, `designation`, `mpn`, `description`, `position`, `channels`. The `mpn` and `description` come from the part. The `position` is `None` when the author never gave one.
- `PlcTable` is one table of the PLC list: the channels of one controller or module. Fields: `item`, `designation` and `rows`. `item` carries the channels, `designation` is its printed designation and the table's heading, and `rows` are its `PlcChannelRow`s in list order, never empty.
- `BoardNetlist` is a board's parts, footprints and nets. Fields: `board`, `board_designation`, `parts`, `nets` and `without_footprint`. `without_footprint` lists the board's parts whose part carries no footprint; a netlist cannot place them, so `parts` omits them. An accessory prints its holder's designation, so it is never listed.
- `NetlistPart` is one placed part of a `BoardNetlist`. Fields: `item`, `designation` (relative to the board), `mpn`, `footprint_library`, `footprint_name` and `installed`. `installed` is the item's own flag: a part not installed stays listed, and the output decides what to do with it.
- `NetlistNet` is one net of a `BoardNetlist`. Fields: `name` and `pins`, the ports it joins.
- `TerminalRow` is one terminal of a strip's connection list. Fields: `terminal`, `designation`, `group`, `index`, `internal`, `external`, `internal_ends`, `external_ends`, `jumper_group`. An unused terminal has empty `internal` and `external` tuples. Bridged terminals share one `jumper_group` number. The `internal_ends[i]` is the far end of `internal[i]`, and the same for `external`.

## Row functions

Each function takes a frozen model and returns rows. None of them writes a file or reads a clock. Most raise a schema error when a named item, function or unit is not in the model, or when an item has no designation. `boards` takes no such check.

- `boards` returns the ids of every item whose part carries a board facet. It sorts them by natural designation, then by id. The export enumeration and the PDF document contents use this same function, so they agree on what a board is.
- `cable_rows` returns one `CableRow` per core of a cable. Cores sort by their index, then by conductor id. Its `unit` keyword keeps the cores drawn by one unit's document.
- `designation_list` returns one `DesignationRow` per item, terminals included, sorted by designation, then id. An accessory that takes its parent's designation has no row. Its `unit` keyword keeps the rows of one unit only; the unit's sole root has no row.
- `board_netlist` takes a model and a board item. It returns the `BoardNetlist` of that board. Its parts are the footprinted descendants of the board. Its nets join the board's internal conductors and its declared nets, never `Mate`s. It raises a schema error when the board is not an item of the model, or when it or a listed item has no designation. Use it to check a board's connectivity yourself; the KiCad export builds the same netlist.
- `plc_channel_rows` returns one `PlcChannelRow` per pin of each PLC channel function, in list order: channels as the PLC list orders them, the pins of a channel by name. Its `unit` keyword keeps one unit's channels. Its `context` keyword sets the location the list prints for, and it has no effect once `unit` is given.
- `plc_tables` returns the rows of `plc_channel_rows`, grouped into one `PlcTable` per carrying item, in the same order. A controller's own channels form its table, the modules' tables follow in rack order, and items in no rack come last, one table each. An item with no channel has no table. Its `unit` and `context` keywords are those of `plc_channel_rows`. Use it when you print one table per controller or module, as the PLC list does.
- `signal_word` returns the word a printed list uses for a `SignalType`: `DI`, `DO`, `AI (V)`, `AI (mA)`, `AO (V)`, `AO (mA)`, `RTD` or `DO (relay)`. The CSV keeps the enum value.
- `plc_list_rows` takes `PlcChannelRow`s and returns one `PLC_COLUMNS` tuple per row for a printed list. The signal is its `signal_word`. A channel with no device and no wire prints `spare` as its signal name.
- `terminal_rows` returns one `TerminalRow` per terminal of a strip. Terminals sort by the natural key of their group, then by index, then by id. A far end outside the given `context` prints with its location path in front, such as `+EXT-M1:U1`. A far end inside it prints short, such as `-B12:2/T1`.

- `open_core_rows(model, cable, *, unit=None)` returns one `OpenCoreRow` per open core of `cable`, by core number. An open core is a spare or a screen earthed at one end. A row holds the core's `index`, `colour`, the port it lands on (`at`, `at_designation`; `None` and `""` for none) and `spare`, false for an `SH` screen. `HarnessCable.open_cores` holds the same rows.
- `core_list_rows(model, *, unit=None)` returns one `CoreListRow` per core of every cable `cable_list_rows` lists. The order is the cable list's, then core number. The wired cores and the open ones are in it, and the ends print as the cable drawing prints them. A spare parked on a pin has it as `end_a`. `pair` is `P1` or `screen P1`, `""` outside a pair, and `note` is `spare` for a spare core. `CORE_LIST_COLUMNS` names the fields, in print order. `cores.csv` is this list.
- `contents_rows(cables)` reshapes a tuple of `HarnessCable`s into one `ContentsRow` per cable. The tuple comes from `harness_cables`, `top_level_cables` or `unit_cables`. The row keeps the cable's product facts and adds `ends`. That is every end's designation, in the cable's own order, joined by an en dash, and a blank end drops its dash. `CONTENTS_COLUMNS` names its columns, in print order.

## Printed texts and order keys

These functions give the one text and the one order that each list uses. A list that prints a label or sorts a column calls them rather than building its own.

- `cable_title` returns the cable's printed title. It is its designation, then a space and its MPN when the cable has one. Without an MPN it is the designation alone.
- `function_designation` renders a function as its item's designation, a colon and the function's name, such as `JB1:J1`. Its `unit` keyword sets whether the text is written for one unit's document or for the whole model.
- `item_description` returns the text a list shows for an item. It is the item's own description, else its part's description, else an empty string. The part's text is never copied onto the item.
- `release_order` returns the order key of a unit release or a history entry, from a version and a revision as two integers. The key is a pair of integers, so revision 10 sorts after revision 9. Compare releases with this key, never with printed text, because the text `"1.10"` sorts before `"1.9"`.
- `sideless_pins` gives the pins of two series ends that have no line side, each in pin order, as `SidelessPins(first, second, problem)`. It takes a label and a tuple of port templates for each end. The order is the marking by value, and the pin's name when it prints none. `problem` is the message that says why the ends cannot pair, or `None`. They cannot pair with a different number of pins, or the same names in another order. A series between two connectors pairs their pins with it.
