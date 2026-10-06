Fransys facade: pipeline, findings policy, file writing.

Facade contract: the only package that merges drafts, freezes, runs passes, applies the findings policy and writes files.

Public surface: `fransys.__all__`. It holds the engineer surface (decision 0103), the
pipeline (`parts`, `document`, `build`, `check`, `write`, `release`, ...) and `derive`, the
model's `derive` module re-exported whole. `just api fransys` lists every name with its
signature and docstring (decision 0053).

The consumer guide in `src/fransys/guide/` documents this surface with tested examples. It
ships as package data. Each public name's docstring is the reference.

Findings policy (decision 0011): any `ERROR` in `check(result)` makes `write` put
nothing into `out_dir` and raise `BuildErrors`. There is no escape hatch. A half-finished design
still draws into `intermediates`.

`write`'s export table and `out_dir` ownership rule, and `document`'s cover/notes handling, are
decisions 0016, 0027, 0033 and author-0001. This work package wires the outputs that exist today: parts, author, document,
build, check (plus `fransys_kicad.check` per board), and write's CSV, WAGO, overview and
netlist-as-intermediate legs. `fransys_render` and `fransys_pdf` wire themselves in when
their own work packages land.

Status: implemented (facade work package). There is no CLI. One gets its own spec when a consumer
asks for something a script does not do.
