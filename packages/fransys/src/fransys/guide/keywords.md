# Keywords and handles

This page lists the public names of the facade's handles and signal types, then the keyword
arguments that a reader of the API may meet. Each keyword is listed under the call that owns it.
Where two calls share a keyword, each call has its own entry.

## Signal types and short names

A signal type says what kind of PLC channel or field signal a function asks for. The facade
gives the common ones short names. `fr.DI`, `fr.DO`, `fr.AI` and `fr.AO` are all members of
`SignalType`, and each is passed as the `signal` of `plc`.

- `DI`: a digital input, `SignalType.DI`.
- `DO`: a digital output, `SignalType.DO`. `DO` belongs with `DI`, `AI` and `AO` as one of the four short names.
- `AI`: an analog input, the 4-20 mA current loop, `SignalType.AI_CURRENT`. Analog voltage inputs have no short name.
- `AO`: an analog output, the 4-20 mA current loop, `SignalType.AO_CURRENT`. Analog voltage outputs have no short name.

The short names cover only the current loops and the
two digital kinds. Use the full member for the rest:

- `SignalType.AI_VOLTAGE` and `SignalType.AO_VOLTAGE`: analog voltage inputs and outputs.
- `SignalType.RTD`: a resistance temperature detector, such as a Pt100.
- `SignalType.RELAY`: a relay signal.

## Handle types

Handles are the objects a design returns and the reader holds. A consumer does not build them.

- `Device`: one device, such as `Q1`. It reaches a function by name (`Q1.coil`) and a pin by brackets (`Q1[2]`). An unknown function or pin raises and lists the candidates.
- `Fn`: one function of a device, such as `K1.coil`. It reaches a pin by brackets (`Q1.main[2]`) or by name (`K1.coil.A1`). An unknown pin raises and lists the pins it has. `Fn.plc` requests a PLC channel.
- `Pin`: one port of one `Fn`. It has an `id`, an authoring `key`, a `name` that brackets match, and a `role`, such as `INTERNAL` or `EXTERNAL`.
- `TypedDevice`: the base a generated parts module subclasses once for each part. Its `mpn` is its whole contract. It adds no behaviour: the subclass only declares functions and pins.
- `TypedFn`: the base a generated parts module subclasses for one function of one part. It adds no behaviour. Its subclass declares pins for the type checker.
- `BuildResult`: the result of `fr.build`. It holds `model`, the frozen and laid-out `Model`, and `findings`, every finding collected while building it.

## Severity

`Severity` says how much a `Finding` blocks a downstream output. The facade alone decides which
severities block which outputs.

- `ERROR`: blocks every export. `write` raises and writes nothing while any error finding remains. There is no escape hatch.
- `WARNING`: worth a look. It blocks nothing under the facade's policy.
- `INFO`: worth noting. It blocks nothing under the facade's policy.

## Model and Finding

The facade builds these records. A consumer reads them and does not construct them. `freeze`
builds a `Model`, and the domain validators and the facade build the `Finding` values.

### Model

`Model` is the immutable, validated result of `freeze`. Everything reachable from it is deeply immutable, and `freeze` checks that.

- `schema_version`: the model schema number. `freeze` stamps the number this build knows. Reading data with a number this build does not know raises an error.
- `aliases`: a map from a retired id to the id that replaces it. `freeze` rewrites every reference to a retired id into one to its replacement. `Draft.alias` fills it.
- `origins`: a map from an id to its `Origin`, the file, line and note where the record was authored. It sits outside the tables. Moving a line does not change the digest.
- `digests`: one digest for each registered namespace, such as `core`, `facet` or `layout`. A change to `layout` records leaves the `core` and `facet` digests alone.
- `digest`: one digest that combines the `digests`. A generated parts module records it as its library digest. `fr.design` refuses a stale module, so a library change must be regenerated before use.
- `Model.origin_of` and `Model.key_of` read `origins` and the tables. See `target` below.

### Finding

`Finding` is one reported engineering problem. Every domain validator emits this one shape. All four fields are required keyword arguments.

- `code`: a stable `UPPER_SNAKE` string, such as `NET_UNREALISED`. The module that emits it lists it. The reader sees it in the findings list. The order is error, warning, then info, and inside each band by `code`, then `subjects`, then `message`.
- `severity`: a `Severity`. Only `ERROR` stops an export. See the Severity section above.
- `subjects`: the ids the finding is about. They are stored once each, in id order, so the order a validator found them in does not matter.
- `message`: the text a reader sees. For a `write` finding the facade's `describe` turns it into printed text first. A `release` finding prints its message as written.

## Draft calls

A `Draft` collects records from input files before `freeze`. Inputs call these methods. A consumer
rarely does.

- `origin` on `Draft.add` and `Draft.extend`: the `Origin` the records are attributed to. It is required, with no default. An identical record already present keeps the smaller origin by `(file, line, note)`, so call order does not matter. A different record under the same id raises a merge conflict. `extend` is not atomic: a conflict leaves the records before it in place.
- `old` on `Draft.alias`: the id that has been retired. The `new` argument is its replacement. It raises when `old` is `new`, the two are of different kinds, or `old` is already retired in favour of another id. The input decoder and the merge both call it.
- `target` on `Draft.key_of`, `Draft.origin_of` and `Draft.record_of`: the id to look up. `key_of` returns the record's authoring key, `origin_of` returns its `Origin`, and `record_of` returns the record itself. Each returns `None` when nothing is held. `record_of` does not follow an alias.
- `target` on `Model.key_of` and `Model.origin_of`: the same lookup on a frozen `Model`. `key_of` returns `None` when no record holds the id. `origin_of` returns the `Origin` or `None`. The `describe` function asks it where an id was written.

## Design calls

These are methods of `Design` and of its handles. They are the consumer's own keywords.

- `definition` on `Design.add`: the unit definition, made by `fr.unit`. The call builds it as instance `tag`, printed with a leading dash. `tag` may be `None`, and then the instance is numbered. It does not take a lowercase tag. The call returns the unit's interface.
- `unused` on `Design.add`: a tuple of field or function names to leave unused. A field is named, such as `X1`. A function is named with its device, such as `X1.x1`. The default is an empty tuple.
- `approved` on `Design.revision`: the approval recorded in one history entry. The default is an empty string. The method does not rename or default a field. It is stored in the history entry. A unit's child design refuses `revision` and uses `fr.unit(history=)` instead.
- `pe_mpn` on `TerminalStrip.__init__`: the part number of the strip's PE terminal. Consumers pass it as `pe=` to `Design.terminal_strip`, not as `pe_mpn`. The default is `None`. A strip without it cannot take a PE terminal, and the error message asks for `pe=`.
- `signal` on `Fn.plc` and on `TypedFn.plc`: the kind of channel requested, as a `SignalType`. Pass a short name such as `fr.DI` or the full member. The call does not choose a channel. The allocation pass binds the request later.
- `priority` on `Fn.plc` and on `TypedFn.plc`: a whole number, default 0. The allocation pass serves a lower number first. Equal numbers are ordered by the requesting function's key, then its id. The call does not choose a channel.

## Layout calls

`d.layout` gives a `Layout`. Every hint on it only advises the layout engine. None draws or places anything.

- `engine` on `Layout.__init__`: the design whose drawing hints this layout writes. A consumer never passes it. `d.layout` builds the layout around the design's engine.
- `target` on `Layout.side`: a field of a unit's interface, such as `u1.bus_in`, or a function, device, terminal or strip. A `side` argument of `fr.ABOVE` or `fr.BELOW` says which edge the interface stands on. An interface with no harness line ignores the target.
- `target` on `Layout.symbol`: a function, a device, or a `FunctionKind` such as `FunctionKind.X`. Pass a kind as a name, never as a string. A string raises. `symbol` names the library symbol to draw. `port_map` is optional and defaults to `None`.
