Fransys output: KiCad netlist. Dev tool: KiCad symbol to part-file skeleton.

Output contract: pure function of a Model returning str, bytes or a tuple of pages. No file I/O, no clock, no randomness. Same model digest, same bytes.

- `netlist(model, board) -> str`: the KiCad 9.0 s-expression netlist of one board, formatted from `board_netlist`: one net per connected group of the board's own conductors and board-only declared nets (decision model-0042). Format and what it leaves out: decision kicad-0001.
- `check(model, board) -> tuple[Finding, ...]`: what the importer would otherwise leave to chance, as findings. The rules read the rows `netlist` writes and repeat nothing the model's validators report (`NET_SHORTED`, `PORT_UNCONNECTED`, `DESIGNATION_DUPLICATE`). The codes:
  - `PART_WITHOUT_FOOTPRINT` (warning): a part of the board with no footprint; the netlist omits it.
  - `NET_SINGLE_PIN` (warning): a net of one pin.
  - `NODE_WITHOUT_COMPONENT` (warning): a net pin of an item with no footprint, or of the board itself; KiCad drops the node.
  - `REFERENCE_DUPLICATE` (error): two parts of the board with one designation.
  - `NET_NAME_DUPLICATE` (error): two nets with one name; KiCad merges them.
  - `PAD_ON_MULTIPLE_NETS` (error): one component and pad name in more than one net.
  - `UNCONNECTED_PIN` (info): a pin of a part of the board that is in no net.

  Not checked: output conflicts from `PortRole` and explicit no-connects, since the model has neither an input or output role nor a no-connect record.
- How an engineer imports the netlist into a board, with the standard import settings: the guide's KiCad page, `fransys/guide/kicad.md`.
- `part_file_skeleton(kicad_sym, symbol) -> str`: reads one symbol's pins out of a `.kicad_sym`
  library's text and writes a part-file skeleton (decision kicad-0002): one `[[function]]` of kind
  `generic`, one port per pin, and the fields a human must fill in (`mpn`, `manufacturer`,
  `description`, `category`, `class_code`) as empty strings marked `# TODO`. Pure: text in,
  TOML text out, no file I/O. The KiCad subset parsed, pin ordering and what did not make it
  in: decision kicad-0002.

```
$ uv run python -m fransys_kicad path/to/library.kicad_sym DEMO-RLY-2U > new-part.toml
```

writes the skeleton to `new-part.toml`, ready to drop under a part library's `parts/` and fill
in by hand.

Status: `netlist`, `check` and `part_file_skeleton` implemented (seven `check` rules; a part
that is not installed is marked do-not-populate). The manual KiCad import check (design
section 8) passed on 2026-09-21 with KiCad 9.0.6.

## Rules moved from docstrings

- `pin_of`: the reference is the designation `board_netlist` holds for the port's item, and the pad is `Port.name`. An item with no part row still names its item, board-relative (model-0040). A board-internal net's own item is `K1`, not `A1-K1`, since a board's netlist is read on its own terms.
- `_pin`: `marking` is the pin's own KiCad name, carried over as the printed marking (F2). It is `None` when KiCad records no name (`"~"`), which leaves the part-file default of printing the port's name.
- `parse_sexpr` and the `_sexpr` module: `.kicad_sym` files and netlist exports share one lexer. Parentheses nest lists, a quoted string may escape `\\` and `"`, and anything else is a bare atom. A quoted string and a bare atom both become a `str`. `bootstrap.py` gives the tree meaning.
- `part_file_skeleton`: the skeleton is ready to be filled in and committed to a part library. `ValueError` is raised for text that does not parse as a `kicad_symbol_lib` or has no such symbol.
- `check`: each pin is resolved as `netlist` resolves it. These are the rules KiCad's importer would otherwise leave to chance.
- `check`: `SchemaError` covers an unknown `board` or an item with no designation (as `board_netlist`). An engineering problem is a finding, never this error.
- `netlist`: the format is `(export (version "E") ...)`, as `kicad-cli sch export netlist` writes it and the PCB editor's Import Netlist reads it. Timestamps derive from item ids, so KiCad keeps footprints matched.
