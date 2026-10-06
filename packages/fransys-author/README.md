Fransys input: the engineer API and its engine. The surface (`fransys_author.surface`) is
what a consumer sees as `fransys`. The engine (`Design`, `Scope`, the handles) builds the Draft
and is internal.

Input contract: produces a Draft. Every record carries an Origin (file, line). An input never calls freeze().

Two layers:
- The surface is the engineer API of ENGINEER-API (`docs/specs/2026-10-02-engineer-api.md`).
  Its worked example is the consumer guide's "The shape of a build script"
  (`packages/fransys/src/fransys/guide/index.md`), whose code runs as a test.
- The engine builds the Draft. The surface builds only through it.
- Agents changing either layer read this package's `CLAUDE.md` first.

Surface status:
- EA-CORE (author-0014): `design`, `location`, `function`, `device`, `terminal_strip`, `wire`
  and the PLC signal kinds.
- EA-PARTS-MODULE: the generated, typed parts module the surface takes parts from.
- EA-SERIES (author-0015):
  - `series` connects its elements in order, each load side to the next line side, pole by pole.
    `parallel` stands in a series as one element. Poles come from the model's pole facts.
  - `ac_supply` and `dc_supply` give the rails: `ac.L1` to `ac.N`, and `dc.plus`, `dc.minus` and
    `dc.mid`.
  - A series takes a strip's next free terminals, the inner side toward the source.
  - A cable lands core i on pole i. Its GNYE core goes to the PE ports, through a terminal of the
    strip's `pe=` part.
  - `device(..., mounted_on=Q1)` joins a directly mounted device's line side to Q1's load side.
- EA-COVERAGE (author-0016): `earth`, `net`, `busbar`, `rail_bond`, `mate` and `harness`; the
  project facts `project`, `revision`, `rating` and `operating`; the drawing hints under
  `d.layout`. `with d.function(...) as m1:` gives the function's handle for those hints.
- EA-UNITS-RUNS (author-0014):
  - `@unit(...)` makes a function a unit release. `io = d.add(fn, "U1")` builds it as a child
    and returns what the unit function returned, a `NamedTuple` instance, so `io.X1` is typed.
  - `interface=True` marks a boundary device or strip, and `unused=True` marks one left open on
    purpose. A boundary function states its values with `X1.power.limits(rating=, operating=)`.
  - `X3.run("valve supply", 8, bridged=True)` declares a named run. A series may name a run in
    place of its strip.
- SWAP (decision 0103, author-0017): `fransys` re-exports the surface; `fransys.author` is
  gone. EA15's gaps are built: `wire=(colour, mm²)` is the one wire form, so `Wire` left the
  surface.

Engine status: WP done (decisions
`docs/decisions/author-0001-builder-implementation-choices.md`, author-0002, author-0003, author-0010). `Design`, `Scope` and
the handle types (`Location`, `Group`, `Item`, `Strip`, `Terminal`, `Cable`, `Fn`,
`Port`, `Wiring`) cover the spec's public names, plus `Rating` and `Operating`, the model's own
value types for a unit's boundary values (`u.boundary(fn, rating=, operating=)`; a scope reads a
part's values with `s.rating(mpn, function=None)` and `s.operating(mpn, function)`, decision
`docs/decisions/author-0010-boundary-values-and-part-reads.md`). 100% test coverage.

The engine's own form, for agents changing it. A consumer writes the surface: the same circuit
takes 242 tokens there against 745 here (the DOL pair in `tests/equivalence/`).

```python
import fransys_parts
from fransys_author import Design

parts = fransys_parts.load("demo_parts")      # the part library, a Draft
d = Design(parts)

d.project(title="Pump station", number="P-1001", customer="Example Co",
          revision=1, author="OJB")                  # version=1 by default: prints 1.1
d.revision(1, date="2026-09-21", text="First issue", created="OJB")  # the date lives here

c1  = d.location("C1", "Pump cabinet")              # a + node
sup = d.group("SUP", "24 V supply")                 # a = node: a functional group
p1  = d.group("P1", "Pump 1")

q1 = d.item("DEMO-MCB-C6", tag="Q1", at=c1, group=p1)        # tag written by the author
k1 = d.item("DEMO-RLY-2CO-24", name="run", at=c1, group=p1)  # tag given by numbering: K1
h1 = d.item("DEMO-LAMP-24", name="lamp", at=c1, group=p1, installed=False)
m1 = d.item("DEMO-MOTOR-4KW", tag="M1", at=d.location("F1", "Field"), group=p1)

x1 = d.strip("X1", at=c1)                           # a terminal strip
t1 = x1.terminal("DEMO-TB-2.5", group=sup)          # X1:1
t2 = x1.terminal("DEMO-TB-2.5", group=p1)           # X1:2, pump 1's return terminal
l1 = x1.terminal("DEMO-TB-2.5", "L", group=p1)      # X1:L:1

wire = d.wiring(colour="BU", gauge="0.75")          # a wire maker with defaults
wire(t1.inner, q1["1"])
wire(q1["2"], k1["A1"], label="W101")
wire.run(k1["A2"], h1["2"], t2.inner)               # a daisy chain: two wires

d.net("P24", t1.outer, cls="power", potential="+24V")
d.net("M24", t2.outer, cls="power", potential="0V")

w1 = d.cable("DEMO-CBL-4G1.5", tag="W1", length_mm=12000)
w1.core(1, l1.outer, m1["U"])                       # colour comes from the cable part

k1.fn("coil").plc("do", "PUMP1_RUN")                # a request; the allocation pass binds it

d.chain(q1, k1.fn("coil"), t2)                      # a layout hint: one column, in this order;
                                                     # t1 (=SUP) is reached by its wire and drawn
                                                     # again in =P1 by the layout engine

draft = d.draft()                                   # the Draft the facade builds
```

Every call that creates something returns a small immutable handle (`Location`,
`Group`, `Item`, `Strip`, `Terminal`, `Cable`, `Fn`, `Port`); later calls take handles,
never a designation string. `group=` on an item, a terminal or a cable is a placement at
the `=` node, exactly like `at=` at the `+` node; `d.draw_in(fn, group)` is the only way
to draw one function of a multi-function item in a different group than the rest of it.
There is no argument anywhere that takes a coordinate, a page or a column number (a test
walks every public signature and proves it).
