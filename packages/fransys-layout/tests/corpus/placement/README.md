# Placement instances (Q1, Q22)

Each `.txt` file is one invented demo circuit, exported from today's engine on main at bc1f5c36b. The PLACEMENT-SCORER step re-dumped them to add `route` and `marker` lines and the `set=` tokens. Every `.score.json` is unchanged. In `s01`, `t02` and `w08` a function drawn as several copies is now named `SID@k`, k from 1, in its `sym`, `net`, `fact`, `today` and `kind` lines. The PNG pages are not kept here. The format needs no repo. Each `.score.json` is today's score of that drawing.

## Which files

| prefix | what | why chosen |
|---|---|---|
| `s01_skid_v16_m3` (and `s01_skid_source.txt`, the script that writes it; run with SKID_V=16 SKID_M=3) | the demo skid: 16 valves, 3 motors, a PLC with DI and DO cards | Q1, the TARGET-LOOK ground truth |
| `w01` to `w10` | the ten field-case builds with the most references plus crossings | Q22 worst |
| `p01_sixteen_channel` | a 16-channel output card with a coil under every pin | the brief; today draws it right (the prototype's 16-channel circuit, where today places 13 of 16, is a different circuit) |
| `p02_strip_to_plc` | terminals wired to a card's pins, today drawn as a staircase | worst on the terminal counter |
| `t01` to `t05` | five typical builds, 13 to 22 symbols, near the median of builds with 10 or more symbols | Q22 typical |

The brief asked for the five worst builds by placement count; Fable's Q22 asked for the worst by references plus crossings. This folder follows Q22. Three of the placement top list are here: `w02`, `w06` and `p02`. The others are left out. Three are builds whose `loose` count comes from parts a test draws without wires (a harness assembly, a board of headers, a unit boundary check). One is a PE-bar build that reproduced only in the full suite run.

The skid is drawn at V=16 valves and M=3 motors. TARGET-LOOK's figure of 17 references was at M=2 (17 again on this SHA, MEASURED-CPU). M=3 adds 6 star flags from the X3 terminals to their breakers, so 23.


Every circuit is invented demo data. No consumer data is in this folder.


## The text format

Units are G. 8 G is one wiring grid, 2.5 mm. x grows right and y grows down. Lines, in file order:

- `area W H`: the content box of one page, in G (1,312 x 854 for A3).
- `group LABEL order=K break_before=0|1 "description"`: the consumer's groups in order. `break_before=1` means the group starts a new page.
- `sym ID group=G body=x,y,w,h keepout=x,y,w,h`: one drawn symbol. Boxes are relative to the symbol origin, at orientation R0. The keep-out holds the designation and pin-marking slots.
- `  pin NAME SIDE dx,dy [node=k] [stand=g]`: one pin. SIDE (N, E, S or W) is the way its wire leaves. Pins with the same `node=` are one electrical point (a terminal's four sides). `stand=` means the pin carries a power symbol (24 V, 0 V, PE) and no wire.
- `net nI [rail rank=r power=K] SYM.PIN ...`: one physical net and its drawn pins. `rail` marks a net that carries a declared supply potential. A smaller `rank` is drawn higher: AC rails by phase, DC rails high to low, 0 V, PE last. `power=SUPPLY`, `GROUND` or `PE` draws as power symbols; `NONE` draws as wires.
- `fact item SYM ...`: symbols that are parts of one device, such as a relay coil and its contacts.
- `fact boxpin SYM.PIN ...`: pins of a box that sit on a PLC channel and can move along their edge. `fact attached SYM ...`: symbols that head a column hung on such a pin. `fact head SYM ...`: symbols that head a fan, a protective device feeding several legs. `fact strip TAG SYM ...`: the terminals of one strip. They were added by the PLACEMENT-SCORER step.
- `kind SYM K`: today's kind of each symbol. It is a legend for a human reader. A general placer must not read it.
- `today SYM page=P at=x,y orient=O set=K`: today's placement of each drawn copy. One symbol can have several copies.
- `route NET page=P set=K a=SYM.PIN b=SYM.PIN x,y x,y ...`: one routed polyline of today's engine, on page P, from pin a to pin b. The vertices are pin-absolute points in G, in order. NET is the `nI` of the net it belongs to. One net can have many routes (a trunk and its drops).
- `marker NET SYM.PIN page=P set=K at=x,y side=S star=K partner=SYM.PIN@K.P`: one printed cross-reference (a link marker), at the pin SYM.PIN of net NET, on page P. K is its star kind: `-` for a plain pair, `REF` or `BRANCH` for a star net, `OFF` for a unit-boundary stub; `partner` is the other end. A page is the pair (set K, page P): pages are numbered from 1 inside a drawing set, and the sets are numbered from 0. The `marker` pages come from the built model. The `today` and `route` pages come from a re-run of the layout stages. On `w02` and `w06` the final layout has fewer pages than the re-run, so the two numberings differ there. A function placed on several pages has one `today` line per placement. The `references` figure is the number of these lines.

Symbol ids read `designation.function`, so `=R1-U1-K1.coil` is the coil of relay K1.
