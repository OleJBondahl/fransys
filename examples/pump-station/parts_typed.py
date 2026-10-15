"""Generated from example_parts. Do not edit: regenerate with python -m fransys parts-module."""

from typing import TYPE_CHECKING, ClassVar, Literal, Never, override

from fransys import Pin, Throw, TypedDevice, TypedFn

SOURCES = ("example_parts",)
LIBRARY_DIGEST = "e05ea95aef8c24af118e2ac3ce67596204db39910ea01ee546c82cf9c0e6e2b8"


class P_1085039__port_1(TypedFn):
    P_1: Pin
    P_2: Pin
    P_3: Pin
    P_4: Pin
    P_5: Pin
    P_6: Pin
    P_7: Pin
    P_8: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self, m: Literal["1", 1, "2", 2, "3", 3, "4", 4, "5", 5, "6", 6, "7", 7, "8", 8]
        ) -> Pin: ...


class P_1085039(TypedDevice[Literal["port_1"], "P_1085039"]):
    mpn: ClassVar[str] = "1085039"
    port_1: P_1085039__port_1
    P_1: Pin
    P_2: Pin
    P_3: Pin
    P_4: Pin
    P_5: Pin
    P_6: Pin
    P_7: Pin
    P_8: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self, m: Literal["1", 1, "2", 2, "3", 3, "4", 4, "5", 5, "6", 6, "7", 7, "8", 8]
        ) -> Pin: ...


class P_1119304(TypedDevice[Never, "P_1119304"]):
    mpn: ClassVar[str] = "1119304"


class P_1119405(TypedDevice[Never, "P_1119405"]):
    mpn: ClassVar[str] = "1119405"


class P_1757022__x(TypedFn):
    P_1: Pin
    P_2: Pin
    P_3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["1", 1, "2", 2, "3", 3]) -> Pin: ...


class P_1757022(TypedDevice[Literal["x"], "P_1757022"]):
    mpn: ClassVar[str] = "1757022"
    x: P_1757022__x
    P_1: Pin
    P_2: Pin
    P_3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["1", 1, "2", 2, "3", 3]) -> Pin: ...


class P_1757255__x(TypedFn):
    P_1: Pin
    P_2: Pin
    P_3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["1", 1, "2", 2, "3", 3]) -> Pin: ...


class P_1757255(TypedDevice[Literal["x"], "P_1757255"]):
    mpn: ClassVar[str] = "1757255"
    x: P_1757255__x
    P_1: Pin
    P_2: Pin
    P_3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["1", 1, "2", 2, "3", 3]) -> Pin: ...


class P_1LE1003_0EB42_2AA4__motor(TypedFn):
    PE: Pin
    U1: Pin
    V1: Pin
    W1: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["PE", "U1", "V1", "W1"]) -> Pin: ...


class P_1LE1003_0EB42_2AA4(TypedDevice[Literal["motor"], "P_1LE1003_0EB42_2AA4"]):
    mpn: ClassVar[str] = "1LE1003-0EB42-2AA4"
    motor: P_1LE1003_0EB42_2AA4__motor
    PE: Pin
    U1: Pin
    V1: Pin
    W1: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["PE", "U1", "V1", "W1"]) -> Pin: ...


class P_2002_1201__terminal(TypedFn):
    external: Pin
    internal: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["external", "internal"]) -> Pin: ...


class P_2002_1201(TypedDevice[Literal["terminal"], "P_2002_1201"]):
    mpn: ClassVar[str] = "2002-1201"
    terminal: P_2002_1201__terminal
    external: Pin
    internal: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["external", "internal"]) -> Pin: ...


class P_2002_1204__terminal(TypedFn):
    external: Pin
    internal: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["external", "internal"]) -> Pin: ...


class P_2002_1204(TypedDevice[Literal["terminal"], "P_2002_1204"]):
    mpn: ClassVar[str] = "2002-1204"
    terminal: P_2002_1204__terminal
    external: Pin
    internal: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["external", "internal"]) -> Pin: ...


class P_2002_1207__terminal(TypedFn):
    external: Pin
    internal: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["external", "internal"]) -> Pin: ...


class P_2002_1207(TypedDevice[Literal["terminal"], "P_2002_1207"]):
    mpn: ClassVar[str] = "2002-1207"
    terminal: P_2002_1207__terminal
    external: Pin
    internal: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["external", "internal"]) -> Pin: ...


class P_21700601__x(TypedFn):
    P_1: Pin
    P_2: Pin
    P_3: Pin
    P_4: Pin
    P_5: Pin
    P_6: Pin
    P_7: Pin
    P_8: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self, m: Literal["1", 1, "2", 2, "3", 3, "4", 4, "5", 5, "6", 6, "7", 7, "8", 8]
        ) -> Pin: ...


class P_21700601(TypedDevice[Literal["x"], "P_21700601"]):
    mpn: ClassVar[str] = "21700601"
    x: P_21700601__x
    P_1: Pin
    P_2: Pin
    P_3: Pin
    P_4: Pin
    P_5: Pin
    P_6: Pin
    P_7: Pin
    P_8: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self, m: Literal["1", 1, "2", 2, "3", 3, "4", 4, "5", 5, "6", 6, "7", 7, "8", 8]
        ) -> Pin: ...


class P_2170465(TypedDevice[Never, "P_2170465"]):
    mpn: ClassVar[str] = "2170465"


class P_3LD2054_0TK51__main(TypedFn):
    P_1L1: Pin
    P_2T1: Pin
    P_3L2: Pin
    P_4T2: Pin
    P_5L3: Pin
    P_6T3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["1L1", "2T1", "3L2", "4T2", "5L3", "6T3"]) -> Pin: ...


class P_3LD2054_0TK51(TypedDevice[Literal["main"], "P_3LD2054_0TK51"]):
    mpn: ClassVar[str] = "3LD2054-0TK51"
    main: P_3LD2054_0TK51__main
    P_1L1: Pin
    P_2T1: Pin
    P_3L2: Pin
    P_4T2: Pin
    P_5L3: Pin
    P_6T3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["1L1", "2T1", "3L2", "4T2", "5L3", "6T3"]) -> Pin: ...


class P_3NW7033__pole_1(TypedFn):
    P_1: Pin
    P_2: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["1", 1, "2", 2]) -> Pin: ...


class P_3NW7033__pole_2(TypedFn):
    P_3: Pin
    P_4: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["3", 3, "4", 4]) -> Pin: ...


class P_3NW7033__pole_3(TypedFn):
    P_5: Pin
    P_6: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["5", 5, "6", 6]) -> Pin: ...


class P_3NW7033(TypedDevice[Literal["pole_1", "pole_2", "pole_3"], "P_3NW7033"]):
    mpn: ClassVar[str] = "3NW7033"
    pole_1: P_3NW7033__pole_1
    pole_2: P_3NW7033__pole_2
    pole_3: P_3NW7033__pole_3
    P_1: Pin
    P_2: Pin
    P_3: Pin
    P_4: Pin
    P_5: Pin
    P_6: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self, m: Literal["1", 1, "2", 2, "3", 3, "4", 4, "5", 5, "6", 6]
        ) -> Pin: ...


class P_3NW8004_1(TypedDevice[Never, "P_3NW8004_1"]):
    mpn: ClassVar[str] = "3NW8004-1"


class P_3SU1102_6AA40_1AA0__lamp(TypedFn):
    X1: Pin
    X2: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["X1", "X2"]) -> Pin: ...


class P_3SU1102_6AA40_1AA0(TypedDevice[Literal["lamp"], "P_3SU1102_6AA40_1AA0"]):
    mpn: ClassVar[str] = "3SU1102-6AA40-1AA0"
    lamp: P_3SU1102_6AA40_1AA0__lamp
    X1: Pin
    X2: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["X1", "X2"]) -> Pin: ...


class P_40_61_9_024_1000__coil(TypedFn):
    A1: Pin
    A2: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["A1", "A2"]) -> Pin: ...


class P_40_61_9_024_1000__contact(TypedFn):
    no: Throw
    nc: Throw
    P_11: Pin
    P_12: Pin
    P_14: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["11", 11, "12", 12, "14", 14]) -> Pin: ...


class P_40_61_9_024_1000(TypedDevice[Literal["coil", "contact"], "P_40_61_9_024_1000"]):
    mpn: ClassVar[str] = "40.61.9.024.1000"
    coil: P_40_61_9_024_1000__coil
    contact: P_40_61_9_024_1000__contact
    A1: Pin
    A2: Pin
    P_11: Pin
    P_12: Pin
    P_14: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["A1", "A2", "11", 11, "12", 12, "14", 14]) -> Pin: ...


class P_5SY6506_7__pole(TypedFn):
    P_1: Pin
    P_2: Pin
    P_3_N: Pin
    N_4: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["1", 1, "2", 2, "3 N", "N 4"]) -> Pin: ...


class P_5SY6506_7(TypedDevice[Literal["pole"], "P_5SY6506_7"]):
    mpn: ClassVar[str] = "5SY6506-7"
    pole: P_5SY6506_7__pole
    P_1: Pin
    P_2: Pin
    P_3_N: Pin
    N_4: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["1", 1, "2", 2, "3 N", "N 4"]) -> Pin: ...


class P_750_402__di_1(TypedFn):
    DI1: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["DI1"]) -> Pin: ...


class P_750_402__di_2(TypedFn):
    DI2: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["DI2"]) -> Pin: ...


class P_750_402__di_3(TypedFn):
    DI3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["DI3"]) -> Pin: ...


class P_750_402__di_4(TypedFn):
    DI4: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["DI4"]) -> Pin: ...


class P_750_402__power(TypedFn):
    P_0V: Pin
    P_24V: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["0V", "24V"]) -> Pin: ...


class P_750_402(TypedDevice[Literal["di_1", "di_2", "di_3", "di_4", "power"], "P_750_402"]):
    mpn: ClassVar[str] = "750-402"
    di_1: P_750_402__di_1
    di_2: P_750_402__di_2
    di_3: P_750_402__di_3
    di_4: P_750_402__di_4
    power: P_750_402__power
    DI1: Pin
    DI2: Pin
    DI3: Pin
    DI4: Pin
    P_0V: Pin
    P_24V: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["DI1", "DI2", "DI3", "DI4", "0V", "24V"]) -> Pin: ...


class P_750_504__do_1(TypedFn):
    DO1: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["DO1"]) -> Pin: ...


class P_750_504__do_2(TypedFn):
    DO2: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["DO2"]) -> Pin: ...


class P_750_504__do_3(TypedFn):
    DO3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["DO3"]) -> Pin: ...


class P_750_504__do_4(TypedFn):
    DO4: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["DO4"]) -> Pin: ...


class P_750_504__power(TypedFn):
    P_0V: Pin
    P_24V: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["0V", "24V"]) -> Pin: ...


class P_750_504(TypedDevice[Literal["do_1", "do_2", "do_3", "do_4", "power"], "P_750_504"]):
    mpn: ClassVar[str] = "750-504"
    do_1: P_750_504__do_1
    do_2: P_750_504__do_2
    do_3: P_750_504__do_3
    do_4: P_750_504__do_4
    power: P_750_504__power
    DO1: Pin
    DO2: Pin
    DO3: Pin
    DO4: Pin
    P_0V: Pin
    P_24V: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["DO1", "DO2", "DO3", "DO4", "0V", "24V"]) -> Pin: ...


class P_750_600(TypedDevice[Never, "P_750_600"]):
    mpn: ClassVar[str] = "750-600"


class P_750_8212__field(TypedFn):
    _plus: Pin
    _minus: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["+", "-"]) -> Pin: ...


class P_750_8212__system(TypedFn):
    P_0V: Pin
    P_24_V: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["0V", "24 V"]) -> Pin: ...


class P_750_8212__x1(TypedFn):
    P_1: Pin
    P_2: Pin
    P_3: Pin
    P_4: Pin
    P_5: Pin
    P_6: Pin
    P_7: Pin
    P_8: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self, m: Literal["1", 1, "2", 2, "3", 3, "4", 4, "5", 5, "6", 6, "7", 7, "8", 8]
        ) -> Pin: ...


class P_750_8212__x2(TypedFn):
    P_1: Pin
    P_2: Pin
    P_3: Pin
    P_4: Pin
    P_5: Pin
    P_6: Pin
    P_7: Pin
    P_8: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self, m: Literal["1", 1, "2", 2, "3", 3, "4", 4, "5", 5, "6", 6, "7", 7, "8", 8]
        ) -> Pin: ...


class P_750_8212(TypedDevice[Literal["field", "system", "x1", "x2"], "P_750_8212"]):
    mpn: ClassVar[str] = "750-8212"
    field: P_750_8212__field
    system: P_750_8212__system
    x1: P_750_8212__x1
    x2: P_750_8212__x2
    _plus: Pin
    _minus: Pin
    P_0V: Pin
    P_24_V: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["+", "-", "0V", "24 V"]) -> Pin: ...


class LADN11__nc(TypedFn):
    P_61_NC: Pin
    P_62: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["61/NC", "62", 62]) -> Pin: ...


class LADN11__no(TypedFn):
    P_53_NO: Pin
    P_54: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["53/NO", "54", 54]) -> Pin: ...


class LADN11(TypedDevice[Literal["nc", "no"], "LADN11"]):
    mpn: ClassVar[str] = "LADN11"
    nc: LADN11__nc
    no: LADN11__no
    P_61_NC: Pin
    P_62: Pin
    P_53_NO: Pin
    P_54: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["61/NC", "62", 62, "53/NO", "54", 54]) -> Pin: ...


class LC1D09BD__aux(TypedFn):
    P_13_NO: Pin
    P_14: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["13/NO", "14", 14]) -> Pin: ...


class LC1D09BD__aux_nc(TypedFn):
    P_21_NC: Pin
    P_22: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["21/NC", "22", 22]) -> Pin: ...


class LC1D09BD__coil(TypedFn):
    A1: Pin
    A2: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["A1", "A2"]) -> Pin: ...


class LC1D09BD__main(TypedFn):
    P_1_L1: Pin
    P_2_T1: Pin
    P_3_L2: Pin
    P_4_T2: Pin
    P_5_L3: Pin
    P_6_T3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self, m: Literal["1/L1", "2/T1", "3/L2", "4/T2", "5/L3", "6/T3"]
        ) -> Pin: ...


class LC1D09BD(TypedDevice[Literal["aux", "aux_nc", "coil", "main"], "LC1D09BD"]):
    mpn: ClassVar[str] = "LC1D09BD"
    aux: LC1D09BD__aux
    aux_nc: LC1D09BD__aux_nc
    coil: LC1D09BD__coil
    main: LC1D09BD__main
    P_13_NO: Pin
    P_14: Pin
    P_21_NC: Pin
    P_22: Pin
    A1: Pin
    A2: Pin
    P_1_L1: Pin
    P_2_T1: Pin
    P_3_L2: Pin
    P_4_T2: Pin
    P_5_L3: Pin
    P_6_T3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self,
            m: Literal[
                "13/NO",
                "14",
                14,
                "21/NC",
                "22",
                22,
                "A1",
                "A2",
                "1/L1",
                "2/T1",
                "3/L2",
                "4/T2",
                "5/L3",
                "6/T3",
            ],
        ) -> Pin: ...


class LRD08__main(TypedFn):
    P_1_L1: Pin
    P_2_T1: Pin
    P_3_L2: Pin
    P_4_T2: Pin
    P_5_L3: Pin
    P_6_T3: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self, m: Literal["1/L1", "2/T1", "3/L2", "4/T2", "5/L3", "6/T3"]
        ) -> Pin: ...


class LRD08__nc(TypedFn):
    P_95: Pin
    P_96: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["95", 95, "96", 96]) -> Pin: ...


class LRD08__no(TypedFn):
    P_97: Pin
    P_98: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["97", 97, "98", 98]) -> Pin: ...


class LRD08(TypedDevice[Literal["main", "nc", "no"], "LRD08"]):
    mpn: ClassVar[str] = "LRD08"
    main: LRD08__main
    nc: LRD08__nc
    no: LRD08__no
    P_1_L1: Pin
    P_2_T1: Pin
    P_3_L2: Pin
    P_4_T2: Pin
    P_5_L3: Pin
    P_6_T3: Pin
    P_95: Pin
    P_96: Pin
    P_97: Pin
    P_98: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(
            self,
            m: Literal[
                "1/L1",
                "2/T1",
                "3/L2",
                "4/T2",
                "5/L3",
                "6/T3",
                "95",
                95,
                "96",
                96,
                "97",
                97,
                "98",
                98,
            ],
        ) -> Pin: ...


class QUINT4_PS_1AC_24DC_2_5_SC__input(TypedFn):
    L__plus: Pin
    N__minus: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["L/+", "N/-"]) -> Pin: ...


class QUINT4_PS_1AC_24DC_2_5_SC__output(TypedFn):
    _plus: Pin
    _minus: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["+", "-"]) -> Pin: ...


class QUINT4_PS_1AC_24DC_2_5_SC__signal(TypedFn):
    SIG: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["SIG"]) -> Pin: ...


class QUINT4_PS_1AC_24DC_2_5_SC(
    TypedDevice[Literal["input", "output", "signal"], "QUINT4_PS_1AC_24DC_2_5_SC"]
):
    mpn: ClassVar[str] = "QUINT4-PS/1AC/24DC/2.5/SC"
    input: QUINT4_PS_1AC_24DC_2_5_SC__input
    output: QUINT4_PS_1AC_24DC_2_5_SC__output
    signal: QUINT4_PS_1AC_24DC_2_5_SC__signal
    L__plus: Pin
    N__minus: Pin
    _plus: Pin
    _minus: Pin
    SIG: Pin
    if TYPE_CHECKING:

        @override
        def __getitem__(self, m: Literal["L/+", "N/-", "+", "-", "SIG"]) -> Pin: ...


class SKX_RIB_2(TypedDevice[Never, "SKX_RIB_2"]):
    mpn: ClassVar[str] = "SKX-RIB-2"
