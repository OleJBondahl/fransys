# fransys-kernel

The record kernel of Fransys: records, typed ids, `Draft`, `freeze()`, canonical form, merge and diff. **Internal: Fransys is the only consumer.** It knows no engineering term and imports no workspace package and no third-party package but the family libraries `elecdef` and `refdef` (owner 2026-10-23, spec LIB-ADOPT).

Status: moved out of `fransys-model` (root decision 0208). `fransys_model.kernel` re-exports every name of this package's `__all__`, so existing imports keep working.

## Role contract

- Holds the generic layer: `@record` and `@value` kinds, the kind registry, `Draft` to `freeze()` to `Model`, canonical JSON and digests, `merge`, `diff`.
- The registry is module-global state in `fransys_kernel.registry`. One instance exists per process; import it only through this package.
- A domain package registers its own kinds, namespaces and schema version (decision model-0251).
- Output is deterministic: no file I/O, no clock, no randomness.
