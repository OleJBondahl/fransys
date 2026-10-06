# example-parts

The part library for the `fransys-examples` two-pump station: real, current catalogue parts
only. One row per part. Port names on every part are the markings printed on the manufacturer's
own datasheet, except where noted below.

Each part file carries its datasheet `[rating]` where the datasheet states one, and `[function.operating]`
where the contract has it. A part whose datasheet could not be read for a rating carries none.

| Designation(s) | MPN | Manufacturer | Datasheet |
|---|---|---|---|
| `-W1` | 1119405 | Lapp | https://www.lapp.com/en_US/us/oelflex-classic-110/p/1119405 |
| `+EXT-X0`, `-X1`, `-X01`, `-X2`, `-X3` | 2002-1201 | WAGO | https://www.wago.com/us/rail-chassis-terminal-blocks/topjobs-feedthrough-terminal-block/p/2002-1201 |
| N terminals | 2002-1204 | WAGO | https://www.wago.com/us/rail-chassis-terminal-blocks/topjobs-feedthrough-terminal-block/p/2002-1204 |
| PE terminals | 2002-1207 | WAGO | https://www.wago.com/us/rail-chassis-terminal-blocks/topjobs-ground-terminal-block/p/2002-1207 |
| `-Q1` | 3LD2054-0TK51 | Siemens | https://apim.industry.siemens.cloud/ted/datasheet?format=pdf&mlfbs=3LD20540TK51 |
| `-Fn1` | 3NW7033 | Siemens | https://apim.industry.siemens.cloud/ted/datasheet?format=pdf&mlfbs=3NW7033 |
| `-Mn` | 1LE1003-0EB42-2AA4 | Innomotics | Innomotics catalogue D 81.1, ed. 04/2024 (base code 1LE1003-0EB4); the exact article's own datasheet could not be fetched (Siemens Mall docuservice error for this MLFB) |
| `-Wn1` | 1119304 | Lapp | https://e.lapp.com/in/p/cables-for-standard-applications/oelflex-classic-110-4g1-5-1119304 |
| `-P1`, `-P2` | 3SU1102-6AA40-1AA0 | Siemens | https://apim.industry.siemens.cloud/ted/datasheet?format=pdf&mlfbs=3SU1102-6AA40-1AA0 (X1/X2 from the device circuit diagram, page 4) |
| `-F01` | 5SY6506-7 | Siemens | https://apim.industry.siemens.cloud/ted/datasheet?format=pdf&mlfbs=5SY6506-7 |
| `-T1` | 2904598 (QUINT4-PS/1AC/24DC/2.5/SC) | Phoenix Contact | https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/929/2904598_Ds.pdf |
| `-U1` DI | 750-402 | WAGO | https://www.alldataresource.com/assets/Wago_Corporation/Wago-Corporation-750-402-4-Channel-Digital-Input-Module-Dc-24V-3-0Ms-Specification-Sheet.pdf |
| `-U1` DO | 750-504 | WAGO | https://docs.rs-online.com/537f/0900766b80b765a7.pdf |
| `-U1` end | 750-600 | WAGO | https://pim.galco.com/Manufacturer/Wago/TechDocument/Data%20Sheet/750-600_dat.pdf |
| `-U2` | SKX-RIB-2 | this repo | designed here; `pcb` part, revision 01. The board's own components (relays, headers) are separate items placed on it by `build.py` (STEP 3) |
| `-U2-K1`, `-U2-K2` | 40.61.9.024.1000 | Finder | https://cdn.findernet.com/app/uploads/S40EN.pdf |
| `-U2-J1`, `-U2-J2` | 1757255 (MSTBA 2,5/3-G-5,08) | Phoenix Contact | phoenixcontact.com product page |
| `-J1`, `-J2` | 1757022 (MSTB 2,5/3-ST-5,08) | Phoenix Contact | phoenixcontact.com product page |
| `-W3` cable | 2170465 (ETHERLINE Cat.6A P) | Lapp | https://www.lapp.com/en_US/us/etherline-cat-6a/p/2170465 |
| `-W3` plugs | 21700601 | Lapp | Lapp Tannehill EPIC/ETHERLINE connector catalogue, p.258 |
| `-K1` | 1085039 (FL SWITCH 1005N) | Phoenix Contact | https://docs.rs-online.com/ef73/A700000010361010.pdf (by others, G3: BOM entry, see below) |
| `-Qn1` | LC1D09BD | Schneider Electric | https://www.se.com/ww/en/product/download-pdf/LC1D09BD (page 7 "Connections and Schema") |
| `-Qn1` front block | LADN11 | Schneider Electric | https://www.se.com/ww/en/product/download-pdf/LADN11 (markings 53/54, 61/62 from the TeSys catalogue "Schemes", 24532-EN Ver2.11) |
| `-Bn2` | LRD08 | Schneider Electric | https://www.se.com/ww/en/product/download-pdf/LRD08 (markings: see below) |
| links in `-Fn1` | 3NW8004-1 | Siemens | https://apim.industry.siemens.cloud/ted/datasheet?format=pdf&mlfbs=3NW8004-1&language=en&caller=SIOS |
| `-U1` controller | 750-8212 | WAGO | manual 2100861323 / 2 / 8.6.2024 with data sheet v31.07.2024: https://assets.heizung-billiger.de/documents/wago_26f8d7572ae6c272.pdf |


## Corrections to the source table (E4)

- `-W1`: order number resolved from "verify" to **1119405**.
- `-Wn1`: order number resolved from "verify" to **1119304**.
- N terminals: **2002-1204 confirmed correct as given**.
- `-F01`: the given MPN **5SY6106-7 is wrong** -- it is a plain 1-pole C6 breaker, not 1P+N.
  5SY6606-7 (checked as a candidate replacement) turned out to be a 3+N-pole device. The correct
  current Siemens 1P+N, curve C, 6 A breaker is **5SY6506-7**, used instead.
- `-W3` plugs: the given order number **21700616 is wrong** for this cable (rated for solid 26-24
  AWG) -- corrected to **21700601** (solid 24-22 AWG, matches the cable's solid AWG22/1 cores).

## The fuse

The link in `-Fn1` is the one Schneider's Type 2 coordination table gives for the LC1D09 contactor
with the LRD08 overload relay at 400 V: a **4 A aM** fuse, 10x38 mm (catalogue A6, page A6/5). The
matching IEC 60269-2 link is the Siemens SENTRON **3NW8004-1** (500 V AC, 250 V DC), which fits the
existing 3NW7033 holder. The choice of aM over gG is flagged for the owner's look.

## Markings not confirmed / judgement calls

- **`-U2-K1`, `-U2-K2` (Omron G2RL-1-E DC24) replaced (E4, STEP 2c).** Its own datasheet never
  states, by pin number, which throw is NO or NC (STEP 2b re-check, three passes, all
  inconclusive — see git history on this file for that research). The designer replaced it with
  **Finder 40.61.9.024.1000**: its terminals are marked `11`/`12`/`14` per the EN 50005 standard
  (`.1` = common, `.2` = NC, `.4` = NO -- confirmed from Finder's own "General technical
  information", https://cdn.findernet.com/app/uploads/TecEN.pdf, "Terminal marking" section), so
  the NO/NC assignment is standard-defined, not read off a drawing. AgNi contact material (not
  the ordering table's bold/preferred AgSnO2): the load is one small DC contactor coil,
  24 V DC, ~0.17 A -- light and low-inrush, not what AgSnO2 is for.
  The coil has no flyback diode (owner, 2026-10-02): the coils are small and the PLC modules
  handle the switching, with no sensitive electronics on the board.
- **`-Mn` (Innomotics 1LE1003-0EB42-2AA4) rated-current source, named.** The exact article's own
  datasheet could not be fetched (Siemens Mall docuservice error for this MLFB). Its 3.15 A rated
  current at 400 V Y is read instead from the sibling MLFB **1LE1003-0EB42-2FA4-Z** (same base
  code and winding as this article; B5 flange mount plus brake options F01+F11, in place of this
  article's B3 foot mount) -- Siemens' own 2018 datasheet for that sibling,
  https://cdn.kempstoncontrols.com/files/3942b04ec7457596105baf312f896377/1LE1003%200EB42%202FA4-Z.pdf
  -- cross-checked against the 2024 Innomotics catalogue D 81.1 row for the same base code
  (already cited above).
- **`-K1` (Phoenix FL SWITCH 1005N) port numbering.** Order number and 5-port count are confirmed
  from Phoenix's own user manual, which ties each port's Link/ACT LED to "the port number," but no
  legible front-panel diagram was found to confirm the exact printed digit format (product page
  403s, no port-numbering figure in the manual). The one port E3 mates `-W3` to is modelled as
  `"1"`, carried over from that documented convention, not read off a diagram.
- **`-K1` (Phoenix FL SWITCH 1005N) `port_1` pin count fixed from 1 to 8 (orchestrator ruling).**
  Was modelled with a single port `"1"` despite `[function.connector].pincount = 8`, mismatching
  the RJ45 plug part's 8-pin model and raising a `MATE_PORT_MISMATCH` finding. Checked whether
  fewer than 8 contacts are actually wired: web search (RS Online's listing) confirms the
  1005N is 10/100 Mbps (Fast Ethernet, pins 1/2/3/6 only electrically used); the manual PDF
  (https://docs.rs-online.com/ef73/A700000010361010.pdf) could not be re-read as text and the
  Phoenix/Mouser/alldatasheet pages all 403'd or timed out, so no pinout diagram was found
  either way. The RJ45 female jack is still mechanically an 8-contact 8P8C jack regardless of
  how many pins are wired through electrically, which is what `d.mate()` needs to match against
  the plug part -- `port_1` now models all 8 pins, `role = "generic"`, same shape as the plug.
- **Manufacturer name for `-Mn`.** Recorded as "Innomotics" (the current, 2024-catalogue brand for
  this motor family); the exact article's own datasheet could not be fetched to confirm the
  printed brand on that specific document.
- **`-Bn2` (LRD08) markings.** The datasheet prints no terminal markings on the relay; the
  markings used are those of Schneider's TeSys catalogue (95-96 NC, 97-98 NO), which follow IEC
  60947-4-1 and EN 50012. The relay direct-mounts on the contactor and prints no input designation:
  the ports `1/L1`, `3/L2`, `5/L3` are the IEC 60445 family convention so that the `-Qn1` to
  `-Bn2` mount link has pins to join (GAPS.md G8). Both parts state `side = "line"` on the odd pins and
  `side = "load"` on the even ones, which the mount link reads.
- **`-Qn1` and its front block carry a NC contact each (21/22 and 61/62) that the example leaves
  unwired.** They are part of the catalogue part, so the part files keep them; at v0.5.1
  each drew alone as a `LONE_CELL` warning, which the pin no longer reports (GAPS.md G20).
- **`-U1` controller (750-8212).** Its `system` and `field` supplies are separate inputs (ports
  `24 V`/`0V` and `+`/`-`), read from the WAGO manual cited in the table. The rack carries no
  separate supply module: the controller takes the field supply itself, and the jumper contacts to
  the I/O modules are `u.busbar` links (GAPS.md G9). Its RJ45 ports carry `marking = "X1"` and `"X2"`.
  The field-supply "Ground" terminals 4 and 8 stay open: manual 2100861323 section 3.2.1 calls them only "Field supply voltage ground" (the ground power jumper contact, section 3.3) and requires no PE connection.
- **WAGO TOPJOB S terminals (2002-1201/-1204/-1207).** No printed per-clamp marking exists on the
  terminal body (WAGO's own marking is via a separate clip-in strip, an accessory); all three
  terminal parts use `internal`/`external` port names, the same form as
  `examples/demo-parts/parts/terminal-feedthrough-2_5.toml`, not a printed marking. PE-ness is
  carried by the net the terminal lands on, not by port role, so the PE terminal uses the same
  `internal`/`external` form as the others (needed for the terminal plan's inner/outer sides).

## Cable core colours

Lapp's OELFLEX CLASSIC 110 5G2.5 and 4G1.5 do **not** use the brown/black/grey/blue/green-yellow
sequence assumed before checking: per Lapp's own family datasheet (DB1119752EN), cores are black
with printed white numbers (EN 50334 / VDE 0293-1), plus one green-yellow PE core. Encoded as
`"BK1"`, `"BK2"`, ... plus `"GNYE"`. The Cat.6A cable's cores are encoded in T568B pin order
(white/orange, orange, white/green, blue, white/blue, green, white/brown, brown) as IEC 60757
codes: `"WHOG"`, `"OG"`, `"WHGN"`, `"BU"`, `"WHBU"`, `"GN"`, `"WHBN"`, `"BN"` (two base codes
joined for the white/coloured pairs; Schematika v0.3.4 accepts only these codes). The shield is
not a core (E3).
