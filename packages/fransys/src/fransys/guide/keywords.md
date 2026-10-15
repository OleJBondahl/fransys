# Keywords and handles

This page lists the public names of the facade's handles and signal types, then the keyword
arguments of the record constructors. The keywords of the `d.*` calls are in `keywords-design.md`,
those of the handle methods and layout hints in `keywords-handles.md`, those of the `fr.*` functions in `keywords-output.md`.

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
