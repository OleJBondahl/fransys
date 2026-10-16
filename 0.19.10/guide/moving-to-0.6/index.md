# Moving to 0.6

This page lists every change a 0.5 consumer script or part file must make for 0.6.
Each entry gives the 0.5 spelling, the 0.6 spelling and one line of why.
The 0.5 spellings sit in text blocks: they no longer run.

## Imports and build

| 0.5 | 0.6 | Why |
|---|---|---|
| `fr.author` and `from fransys.author import ...` | `d = fr.design("demo_parts", place="C1")`, then calls on `d` | `fransys.author` left `__all__`: the engineer surface is the one spelling. |
| `fr.build(parts, d.draft())` | `fr.build(d)` | A design holds its library, so the build needs no second argument. |
| `fr.build(parts, d.draft(), doc)` | `fr.build(d, doc)` | The same reason, with a document. |

Pass `fr.design` the generated parts module or the import-name strings that `fr.parts` takes.

## Tags and units

| 0.5 | 0.6 | Why |
|---|---|---|
| `location("-C1")`, `"=M1"`, `"+X1"` | `d.location("C1", text)` | A tag is a bare key. A prefixed tag raises. |
| `unit("-A1", ...)` | `@fr.unit("A1", ...)` | A unit name is a key, with no `-`, `+` or `=` prefix. |
| unit release `interface=` | `interface_version=`; boundary values are `fn.limits(...)` | `interface` now means only the boundary marking, `interface=True`. |
| `d.add(fn, "io")`, the second argument a lowercase key | `d.add(fn, "U1")`, a printed tag; or `d.add(fn, None, name="io")` with `class_code=` on the unit | The argument is the instance's tag and key, and a container prints it: `-U1-J1`. A lowercase letter raises. |
| `d.location` called twice for one tag, order mattering | one call per tag, in any order | A location is order-free, and its text is set once. |

## Devices and terminal strips

| 0.5 | 0.6 | Why |
|---|---|---|
| `item(mpn, tag=, at=, group=)` | `d.device("Q1", mpn, place=)` | The electrotechnical word is device, and its tag is the first argument. |
| `strip.terminal(3)` | `X1[3]` | A terminal strip is indexed by terminal number. |
| `strip.take(...)` | `X1[3]` or `X1.run(label, n)` | `take` had no surface spelling. Indexing and runs cover it. |
| `bridge(t1, t2)` | `X1.run(label, n, bridged=True)` | A bridge joins the adjacent terminals of one run. A run may be two terminals. |
| two parts of one MPN in a library | no surface spelling | The surface names a part by its MPN, which then names both makers. |

`d.device` and `d.terminal_strip` raise on such an MPN and name both makers.
The surface has no spelling for either part. Report the case, as a consumer case brings a form back.

## Wires

| 0.5 | 0.6 | Why |
|---|---|---|
| `Wire(colour, mm2, label)` | `wire=(BU, 0.75)` and `d.wire(a, b, label="L1")` | `Wire` is gone. The tuple is the one form, and the label belongs to the call. |
| `wiring(a, b, n=2)` | `d.wire(a, b, n=2)` | One spelling for a wire between two pins. |

## Groups, supplies and ids

| 0.5 | 0.6 | Why |
|---|---|---|
| a terminal's `group` argument, `d.interface(fn, ...)` | the `d.function` block where the terminal is first taken; `X1.x1.limits(rating=, operating=)` | One spelling each: the block names the group, and `interface` means the boundary marking. |
| a supply with no source device | `d.dc_supply(name, plus=, minus=, voltage=)` | The pins and the voltage stand in for the source. |
| a DC supply's M rail named `M` | the rail is named `0V` | The 0 V conductor carries its potential as its name. |
| `derive.unit_ids(model)` | `sorted(fr.derive.units(model))` | It listed the keys of the units table. |
| a unit function returning a dict, `d.add(...)` returning `AddedUnit` | a `typing.NamedTuple` instance, returned by `d.add` as it is | A misspelt boundary is a type error. `fr.Run` and `fr.Terminal` type the fields that hold strips, runs and terminals. |
| `Design.unit_id` | a unit is named by its release name: `unit="pump-cabinet"` in `fr.write`, `fr.release`, `fr.verify` | There is no successor; the release name is the one name. |
| `derive.wire_label_rows` | `derive.wire_rows` and `<set>-wires.csv` | WIRE-LIST removed it on purpose (bf2d3968). |
| a per-terminal part on a strip | one strip part; a run labelled `"PE"` takes `pe=` | The strip has no per-terminal part. |

## Findings that change

| 0.5 | 0.6 | Why |
|---|---|---|
| `Net.potential` with no supply declared | declare the supply system: `d.ac_supply(...)` or `d.dc_supply(...)` | Without it the model gets POTENTIAL_WITHOUT_SUPPLY (WARNING) and no rank. |
| `Profile.potential_ranks` | removed: ranks follow the declared supply | A rank keyed by rail name left a rail named `L` or `12V` unranked, and its pins swapped sides. |

## Part files

| 0.5 | 0.6 | Why |
|---|---|---|
| a switched link with no `rest` | `rest = "open"` or `rest = "closed"` | SWITCHED_LINK_WITHOUT_REST is an ERROR. |
| `conductor = "PE"` on a pin | `role = "pe"` | A PE pin is named by its role. The pole-side `conductor` value is refused. |
| a protection `type` on a non-protection function | remove the `type` | A load ERROR in 0.6. |

A changeover contact (`contact_co`) needs no `rest` line.
Its throw roles imply it: `break` is closed at rest and `make` is open.
Its ports must still carry `common`, `break` and `make`, as in 0.5.
Only `switch` and `generic` functions with a switched link need `rest`.

## Stored models

The model `SCHEMA_VERSION` went from 2 to 7. Rebuild every stored model with `fr.build`.
