# Moving to 0.22

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page lists each call that 0.22 adds or changes for ratings, with the old spelling and the new one.

## Rating is the elecdef Rating

`fr.derive.Rating` is removed, with `BreakingPoint` and `effective_rating`. A rating is a `fr.elecdef.Rating`: its voltage and current are tuples of `fr.elecdef.Range`, each with the current kind in `at`.
`Rating(voltage_ac_v=Decimal(250))` becomes
`fr.elecdef.Rating(voltage=(fr.elecdef.Range(fr.elecdef.Role.RATED, nom=fr.elecdef.Unit.V(250), at=fr.elecdef.At(fr.elecdef.Current.AC)),))`.
The rating has no breaking fields: a breaking figure is in the function's `[function.block]`
(`breaking_capacity` for a fuse; `icn`, `icu` and `ics` for a breaker). A fuse link with no function states a breaking minimum in its part-level `[block]`.

## Operating has Range and Quantity fields

`fr.derive.Operating` keeps its name. `voltage_ac_v`, `voltage_dc_v`, `nominal_voltage_v`, `min_voltage_v` and `max_voltage_v` are one `voltage` tuple of `Range`
(a nominal with a window is one `Range` with `nom`, `min` and `max`). `max_current_ac_a` and `max_current_dc_a` are `max_current`;
`fault_current_ac_a` and `fault_current_dc_a` are `fault_current`. The rest drop the unit suffix and hold a `fr.elecdef.Quantity`,
for example `fault_time_constant=fr.elecdef.Unit.MS(15)`. In a part file the keys are the same names; see `parts.md`.

## Current comes from elecdef

The AC/DC enum is `fr.elecdef.Current` (`Current.AC`, `Current.DC`). The old model enum is gone; the authoring string `current="ac"` is unchanged.

## A rail is declared

Bridged DC or PE strips are no longer rails: add `rail=True` to the bridged `run` or `d.terminal_strip` that is the rail. An unflagged terminal draws as a terminal, and `d.detail.rail_bond` is gone with the `rail` link kind.
