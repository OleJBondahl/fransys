# fransys-wago

Fransys output: WAGO module XML.

Output contract: pure function of a Model returning str, bytes or a tuple of pages. No file I/O, no clock, no randomness. Same model digest, same bytes.

- `modules_xml(model, rack, *, unit=None) -> str`: the `<Modules>` fragment of CDP Studio's `WagoPFCIOServer.xml` for one rack, formatted from `rack_modules_for_cdp`. The format: `docs/SPEC.md`; the decision: `docs/decisions/wago-0001-modules-fragment.md`.
- `fransys_wago.signals.SIGNALS`: the one table from a CDP kind (`derive.cdp_kind`) to how its channel is written.

Status: `modules_xml` implemented. Reading or merging a CDP file, other PLC vendors and PLC program code are out of scope.
