# Moving to 0.16 and 0.17

This page covers a move from 0.15 to 0.16, to 0.17, or across both. If you are on 0.16, read the 0.17 section only.
Nothing in `fr.__all__` is removed or renamed. A stored model written by 0.15 or 0.16 no longer loads.

## Moving from 0.16 to 0.17

Each change below has the old spelling, the new one and the fix.

| where | 0.16 | 0.17 | what to change |
|---|---|---|---|
| Stored models | Schema 17. | Schema 18: facing is stored on every link marker. An older model raises `SchemaVersionError`. | Rebuild with `fr.build`. A layout golden or digest you keep moves by the schema stamp. |
| `PlcChannelRow` (PLC-PIN-ROWS, model-0209) | One row per channel, with `channel_designation`. | One row per pin, with `port`, `pin` and `channel_name`, and no `channel_designation`. `wired_to` holds the far ends of that pin alone. | Read `pin` and `channel_name` where you read `channel_designation`. |
| `PLC_COLUMNS` and `plc_list_rows` | Built on `channel_designation`. | `pin`, `channel_name`, `signal`, `signal_name`, `wired_to`. | Update code that picks a column by name or position. |
| `UNIT_CONNECTOR_DANGLING` (DANGLING-RETIRE, model-0219) | A `WARNING` for a spare terminal or port of a unit. | Retired: the code no longer exists. | A filter that names it now matches nothing; remove it. |
| `PLC_BINDING_WIRING_MISMATCH` message | Names each channel by its module. | Names each channel by its pins, such as `-A1:1`. | Code that matches the old text must match the pin form. |

Other 0.17 changes need no code change:

- The PLC list prints one row per pin, spare pins included.
- A PLC request binds the channel it is wired to even when that channel's net holds other devices. A request of the wrong kind yields the channel to one of the right kind (model-0211).
- Several requests wired to one channel give `PLC_BINDING_WIRING_MISMATCH`. Request that channel once, on one of the devices. 0.18 gives one clear finding.
- A finding message names an untagged unit by its name and revision, as its title block prints it. `unit unit` no longer appears (overview-0003).
- A coil switched by a channel pin stands under that channel (layout-0208).
- A beside branch under a host pin no longer fails with `ROUTE_FAILED`. That was a 0.16.0 regression (layout-0174).
- A terminal whose part has a protective link, such as a fuse terminal, is no longer a rail terminal (model-0215).
- PDF navigation: link markers and sheet-index rows link, viewer page labels show the sheet text, and the outline lists sheets and devices (pdf-0029, pdf-0034).
- A new package, `fransys-el`, comes in with `fransys`. A lock file gains one package (layout-0192).
- Cable page texts come out in reading order (render-0011).

## Moving from 0.15 to 0.16

### What may newly stop your build

| change | what you see | the fix |
|---|---|---|
| Stored models use schema 17 (0.15: 15) | `SchemaVersionError`: "this build reads schema version 17" | Rebuild the model with `fr.build`. A layout golden or digest you keep moves by the schema stamp. |
| `PLC_REQUEST_AMBIGUOUS` is a new `ERROR` | A PLC request whose wiring ties several channels of its signal kind, none on a direct conductor, used to take the first one silently. Now it binds none. | Wire the request to one channel. The message names the request and every tied channel (model-0211). |
| `PLC_BINDING_SIGNAL_MISMATCH` message | It now names the asked kind, the channel, the channel's kind and both fixes. The severity is unchanged. | Ask for the channel's kind, or rewire to a channel of the asked kind. |
| `CABLE_PAIR_INVALID` is a new part-file `ERROR` | A `[cable_product] pairs` entry names a core out of range, a core in two pairs, a screen that is not `SH`, or an `SH` core as a pair core. | Correct the pair list in the part file. |
| `CABLE_CORE_COUNT` counts open cores | A cable with `spare` or one-ended screen cores now counts them toward its part's core count, so a warning can clear or appear. | The message names the remedy. |
| `HintError` for a group with no column | It names the group that took the devices, the loop and the `d.layout.chain` fix. It is still an error. | Apply the `d.layout.chain(...)` it prints (layout-0195). |
| `TITLE_BLOCK_TEXT_OVERFLOW` names `d.layout.page_title` | The `=F1 =F2` group-label fallback is gone. A title that fits no form is cut with "…". It stays a `WARNING`. | Give the page a short title with `d.layout.page_title`. |

These findings no longer fire, so a script that expects them changes:

- `DOCUMENT_NO_DRAWINGS` is an `ERROR` for a `SCHEMATIC` page only when the document has no other content page. A list with rows, a `HARNESS_DRAWING` with a cable or a `BLOCK_DIAGRAM` with a sheet is enough (pdf-0033). Harness and diagram errors are unchanged.
- `UNUSED_CONTRADICTED` is checked at the unit that declares `unused=`. Declaring a passed-up interface unused on the outer unit no longer warns (model-0210).
- `LONE_CELL` skips an item box over a unit's open boundary functions (layout-0202).

### Output changes

Drawings and PDFs change byte for byte. Re-check any golden you keep.

- **Page pad.** Schematic ink keeps two wiring lanes (`PAGE_PAD`) inside the frame line, so every page moves (layout-0187).
- **Idle pins and terminals.** A connector pin or terminal that no wire inside the unit reaches is not drawn on the unit's own pages. The parent's black box keeps it, and its table still lists it (layout-0197, layout-0202). A unit with nothing left to draw adds no schematic page.
- **Connector tables.** `CONNECTOR_LIST` prints one table per connector with Pin, Net, Mate and Ends. Style, pin count and gender leave the PDF table. `connectors.csv` keeps them and gains an `ends` column (pdf-0030).
- **Boundary boxes.** A boundary box prints its landed pins, not the interface field name (model-0206).
- **Cable names.** A cable end that is a connector names it (`+C1-A1-X1`) on the cable page and in the cable list.
- **Spare cores and pairs.** `Cable.spare(...)` and a one-ended screen from `Cable.core` draw as open rows with a blank stub. A part file's `pairs` draw pair brackets. The cable list shows pairs (model-0213, layout-0207).
- **Beside chains.** `d.layout.chain(beside=...)` joins its host by one or two end nets, a one-pin box or a box head, with no marker. A box-pin run stands a grid off the pin.
- **Titles.** The title block prints the first form of `derive.page_title_forms` that fits. A strip terminal reads as its strip once ("-X1") (pdf-0028, pdf-0032).
- **Sheets page.** `PageKind.SHEET_INDEX` is in every preset, after the notes. It lists Sheet, Title and Page. Block diagram sheets read `B1`, `B2` (pdf-0031). `remove=(fr.PageKind.SHEET_INDEX,)` drops it.
- **cores.csv.** It lists every cable core with both ends, its pair and its spare mark (CORES-CSV).
- **PLC list.** Signals print in datasheet words (`DI`, `AI (mA)`, `DO (relay)`). A channel with no device and no wire prints `spare`. The CSV keeps the enum values.
- **A bridged run outside a block** takes no terminals, so its terminals join the block of their first circuit wire (author-0037).

### API names

`fr.__all__` gains no name and loses none. `fr.__version__` is new, read from `importlib.metadata`. It is not in `__all__`, so `from fransys import *` skips it.

| where | new |
|---|---|
| authoring | `d.layout.page_title(thing, text)`; `Cable.spare(*cores, at=...)`; `Cable.core` for an `SH` core earthed at one end |
| part file | `[cable_product] pairs`, and the demo part `DEMO-CBL-2X2X0.75-SP` |
| `fr.PageKind` | `SHEET_INDEX` |
| `fr.derive` rows | `OpenCoreRow`, `SheetIndexRow`, `open_core_rows`, `sheet_index_rows`, `plc_list_rows`, `connector_rows_of`, `CONNECTOR_LABELS` |
| `fr.derive` facts | `function_is_reached`, `port_is_reached`, `connector_items`, `unit_connector_items`, `signal_word`, `cores_text` |
| `fr.derive` titles | `page_title`, `page_title_forms`, `short_title`, `sheets`, `diagram_sheets`, `sheet_text`, `set_page_text`, `sheet_counter_text`, `sheet_title_text` |
| records | `layout.page_title`, `layout.open_core_wire`, `facet.open_core`, and `CableProductFacet.pairs` with `CorePair` |

`d.layout.chain(beside=)` now accepts one end net on the host and a one-pin box at the chain's end.
