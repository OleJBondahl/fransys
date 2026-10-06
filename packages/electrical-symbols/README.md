# electrical-symbols

Electrical graphical symbols as data. Every symbol is drawn from scratch in our own geometry, after
the conventions of IEC 60617. They are not IEC's drawings, and this repo is not affiliated with or
endorsed by IEC. The geometry is our own and has not been checked against the standard's drawings,
so every symbol carries `status = "unverified"`.

Status: alpha, under construction, a package of the Fransys workspace
(`packages/electrical-symbols`). Nothing is released.

## What is here

- `symbols/`: one TOML file per symbol. The file stem is the symbol's slug, which is also its
  `reference.number` and the name other symbols use to compose it.
- `library.toml`: the library's settings.
- `src/electrical_symbols/`: a thin Python package exposing `LIBRARY`, loaded from the bundled
  `bundle.json`; `generic_box(port_names)` and `GENERIC_BOX_KEY`, the labelled-box placeholder
  layout draws for a function with no symbol (D41); and `library_version()` /
  `LIBRARY_VERSION`, the one home of the version string placements record and
  `fransys_render.check` compares (D40).
- `build/` and `src/electrical_symbols/bundle.json`: the generated output, tracked in git so a
  symbol change shows up as a reviewable diff.

The toolkit `graphical-symbols` validates, resolves, lints and renders the files. It is its own
repository again, pinned by an exact git tag in the root `pyproject.toml` (root decision 0015). Later data packages for other
standards follow the same pattern.

## The design

The toolkit's packaged design guide (`graphical_symbols`' `docs/SYMBOL_INTERFACE.html`, read
through `importlib.resources`, root decision 0015 -- the one copy, shipped in its wheel) is the
binding, final spec and file format. Open it in a browser from the toolkit's own repository.
Symbols are definitions with role-named ports (`in`, `out`,
`anode`), explicit connectivity (nodes and paths), text slots for tags and terminal markings, and
composition by anchor instead of copied geometry. Units are modules (M = 2.5 mm).
Every symbol is drawn in our own geometry, after the conventions of IEC 60617; no drawing is
copied from the standard.

## The symbols

| Slug | Name | Kind |
|---|---|---|
| `actuator-mushroom` | Actuator (mushroom head, operated by pushing) | qualifier |
| `actuator-push` | Actuator (operated by pushing) | qualifier |
| `break-contact` | Break contact | symbol |
| `capacitor` | Capacitor, general symbol | symbol |
| `change-over-contact` | Change-over break before make contact | symbol |
| `circuit-breaker-function` | Circuit breaker function | qualifier |
| `circuit-breaker` | Circuit breaker | symbol |
| `coil` | Coil, general symbol | symbol |
| `connection-point` | Connection point | symbol |
| `connector-fixed` | Connector, fixed portion of an assembly | symbol |
| `contact` | Connector contact, no stated gender | symbol |
| `contact-female` | Connector contact, female (socket) | symbol |
| `contact-male` | Connector contact, male (plug) | symbol |
| `converter-dc-dc` | DC/DC converter | symbol |
| `current-transformer` | Current transformer, general symbol | symbol |
| `diode` | Semiconductor diode, general symbol | symbol |
| `earth` | Earth, general symbol | symbol |
| `emergency-stop` | Emergency stop, mushroom push-button with latching break contact | symbol |
| `fuse` | Fuse | symbol |
| `ground` | Ground, reference (0 V) symbol | symbol |
| `lamp` | Lamp, general symbol | symbol |
| `make-contact` | Make contact, general symbol | symbol |
| `motor-1ph-pe` | Induction motor, single-phase, squirrel-cage, with protective earth terminal | symbol |
| `motor-1ph` | Induction motor, single-phase, squirrel-cage | symbol |
| `motor-3ph-pe` | Induction motor, three-phase, squirrel cage, with protective earth terminal | symbol |
| `motor-3ph` | Induction motor, three-phase, squirrel cage | symbol |
| `operating-device` | Operating device, general symbol; relay coil, general symbol | symbol |
| `plc-channel` | PLC channel (column end) | symbol |
| `power-supply` | Power supply, rail symbol | symbol |
| `protective-earth` | Protective earth | symbol |
| `psu` | Power supply unit (a.c./d.c. in, d.c. out) | symbol |
| `push-button` | Switch, manually operated, push-button, automatic return | symbol |
| `rcd` | Residual current operated circuit breaker | symbol |
| `rectifier-pe` | Rectifier, with protective earth terminal | symbol |
| `rectifier` | Rectifier | symbol |
| `residual-current-core` | Residual current sensing core | qualifier |
| `resistor` | Resistor, general symbol | symbol |
| `terminal` | Terminal | symbol |
| `thermal-overload` | Thermal overload relay, thermally operated release | symbol |
| `transformer` | Transformer with two windings, general symbol | symbol |

The `-pe` files are our own variants with a protective earth terminal. The two qualifiers are composed
into `push-button` and `circuit-breaker`.

`terminal`'s four stub leads are bound to their ports (`n`/`e`/`s`/`w`); an unwired one is
left out at render, never drawn as a bridge to a neighbour.

## Development

Run from the repository root:

```
uv sync
just ci                         # workspace gates, incl. this package's pytest gates
just build-electrical-symbols   # regenerate the tracked output
```

## Rules moved from docstrings

- `library_version`: `fransys_layout.geometry.symbols` re-uses it and keeps no copy. `fransys_render.check` compares it with `SymbolPlacement.library_version`.
- `generic_box` module: layout's `resolve` stage calls it (layout-0042, D41). The placeholder is a real toolkit symbol, converted through the ordinary D6 recipe, not a private struct.
- `_pitch`: a marking shows the model port name, the part after the last `"."` (an item view names a port `<function>.<port>`). Width is about 0.65 M per character at the house text height. Add the 0.25 M wire offset and a gap, then round up to whole M so ports stay on the grid.
