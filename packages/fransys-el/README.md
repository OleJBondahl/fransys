# fransys-el

Fransys electrical conventions: the values the general layout core takes as options.

Role contract: conventions as values, and the placement-problem builder. `fransys_el` holds our drawing conventions and builds the placement problem that `fransys_layout` solves. Its `build(model, kit, conventions, library)` is a pure function from a model, a symbol kit, conventions and a library to a `PlacementProblem` and what it left out. It reads facts from `fransys_model.derive`, derives none, and reads no file (el-0002). `fransys_layout` and `fransys_render` never import it. The facade builds the conventions with `house_conventions` and passes them into every layout call (FRANSYS-SPLIT, seam 1).

Public names (`just api fransys_el`, 14 names):

- The builder: `build`, `symbol_kit`, `unknown_symbols`, `house_conventions`, and `ProblemError`, the error for an impossible input (el-0002).
- The drawings and their pens: `lay_out_drawn` (the page `Drawing` values laid out straight from the core, el-0004), `style(library)` (the pens and sizes `svg` takes, layout-0323), and `readability`.
- The findings: `FINDING_CODES`, `block_wire_findings`, `problem_finding`, `read_findings`, `skipped_findings` and `unknown_symbol_key_findings`.

Imports (checked by grep over `packages/fransys-el/src`): `fransys_model` (its surfaces and `derive` submodules), `electrical_symbols`, and `fransys_layout` through its top-level, `core`, `symbols` and `drawing` surfaces. Decision: `docs/decisions/layout-0192-*.md`.
