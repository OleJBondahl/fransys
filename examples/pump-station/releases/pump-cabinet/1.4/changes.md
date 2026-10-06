# pump-cabinet: changes from 1.3 to 1.4

## Items

- Removed `=CTL-X01:L1:2`: 2002-1201, WAGO.
- Removed `=P1-Q12`: LADN11, Schneider Electric.
- Removed `=P1-X01:L1:3`: 2002-1201, WAGO.
- Removed `=P1-X01:L2:3`: 2002-1201, WAGO.
- Removed `=P1-X01:L3:3`: 2002-1201, WAGO.
- Removed `=P2-Q22`: LADN11, Schneider Electric.
- Removed `=P2-X01:L1:4`: 2002-1201, WAGO.
- Removed `=P2-X01:L2:4`: 2002-1201, WAGO.
- Removed `=P2-X01:L3:4`: 2002-1201, WAGO.
- Added `=SUP-X01:L1:2`: 2002-1201, WAGO.
- Added `=SUP-X01:L1:3`: 2002-1201, WAGO.
- Added `=SUP-X01:L1:4`: 2002-1201, WAGO.
- Added `=SUP-X01:L2:2`: 2002-1201, WAGO.
- Added `=SUP-X01:L2:3`: 2002-1201, WAGO.
- Added `=SUP-X01:L3:2`: 2002-1201, WAGO.
- Added `=SUP-X01:L3:3`: 2002-1201, WAGO.
- Changed `=SUP-X1:N:1`: mpn 2002-1204 to 2002-1201.

## Units

- Changed `=PLC-U2` (relay-interface-board): revision 1.2 to 1.3.

## Conductors

- Added between `-X01:L2:1` and `-X01:L2:2`.
- Removed between `-X01:L2:1` and `-X01:L2:3`.
- Added between `-X01:L2:2` and `-X01:L2:3`.
- Added between `-X01:L2:2` and `=P1-F11:3`.
- Removed between `-X01:L2:3` and `-X01:L2:4`.
- Removed between `-X01:L2:3` and `=P1-F11:3`.
- Added between `-X01:L2:3` and `=P2-F21:3`.
- Removed between `-X01:L2:4` and `=P2-F21:3`.
- Added between `-X01:L3:1` and `-X01:L3:2`.
- Removed between `-X01:L3:1` and `-X01:L3:3`.
- Added between `-X01:L3:2` and `-X01:L3:3`.
- Added between `-X01:L3:2` and `=P1-F11:5`.
- Removed between `-X01:L3:3` and `-X01:L3:4`.
- Removed between `-X01:L3:3` and `=P1-F11:5`.
- Added between `-X01:L3:3` and `=P2-F21:5`.
- Removed between `-X01:L3:4` and `=P2-F21:5`.
- Changed between `-X1:PE:1` and `-X3:PE:1`: colour GNYE to ; gauge_mm2 2.5 to ; kind wire to rail.
- Changed between `-X1:PE:1` and `-X3:PE:2`: colour GNYE to ; gauge_mm2 2.5 to ; kind wire to rail.
- Added between `-X2:24V:5` and `=P1-Q11:53/NO`.
- Removed between `-X2:24V:5` and `=P1-Q12:53/NO`.
- Added between `-X2:24V:8` and `=P2-Q21:53/NO`.
- Removed between `-X2:24V:8` and `=P2-Q22:53/NO`.
- Changed between `=P1-B12:1/L1` and `=P1-Q11:2/T1`: colour BN to ; gauge_mm2 1.5 to ; kind wire to mount.
- Changed between `=P1-B12:3/L2` and `=P1-Q11:4/T2`: colour BK to ; gauge_mm2 1.5 to ; kind wire to mount.
- Changed between `=P1-B12:5/L3` and `=P1-Q11:6/T3`: colour GY to ; gauge_mm2 1.5 to ; kind wire to mount.
- Added between `=P1-P1:X1` and `=P1-Q11:54`.
- Removed between `=P1-P1:X1` and `=P1-Q12:54`.
- Changed between `=P2-B22:1/L1` and `=P2-Q21:2/T1`: colour BN to ; gauge_mm2 1.5 to ; kind wire to mount.
- Changed between `=P2-B22:3/L2` and `=P2-Q21:4/T2`: colour BK to ; gauge_mm2 1.5 to ; kind wire to mount.
- Changed between `=P2-B22:5/L3` and `=P2-Q21:6/T3`: colour GY to ; gauge_mm2 1.5 to ; kind wire to mount.
- Added between `=P2-P2:X1` and `=P2-Q21:54`.
- Removed between `=P2-P2:X1` and `=P2-Q22:54`.
- Changed between `=PLC-C1:+` and `=PLC-DI1:24V`: colour WH to ; gauge_mm2 1.5 to ; kind wire to busbar.
- Changed between `=PLC-C1:+` and `=PLC-DO1:24V`: colour WH to ; gauge_mm2 1.5 to ; kind wire to busbar.
- Changed between `=PLC-C1:-` and `=PLC-DI1:0V`: colour WH to ; gauge_mm2 1.5 to ; kind wire to busbar.
- Changed between `=PLC-C1:-` and `=PLC-DO1:0V`: colour WH to ; gauge_mm2 1.5 to ; kind wire to busbar.

## Mates

- Added between `-U2/=PLC-J1:x` and `=PLC-J1:x`.
- Added between `-U2/=PLC-J2:x` and `=PLC-J2:x`.
- Removed between `=PLC-J1:x` and `=PLC-U2/=PLC-J1:x`.
- Removed between `=PLC-J2:x` and `=PLC-U2/=PLC-J2:x`.

## Nets

- Changed `PE`: potential PE to .