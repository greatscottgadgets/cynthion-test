from greatfet import GreatFET
from tps55288 import TPS55288

gpio_allocations = dict(
    BOOST_EN = ('J2_P27', 0),
    BOOST_VBUS_AUX = ('J2_P16', 0),
    BOOST_VBUS_CON = ('J2_P15', 0),
    BOOST_VBUS_TC = ('J2_P34', 0),
    CC1_test = ('J1_P17', None),
    CC2_test = ('J1_P18', None),
    D_S_1 = ('J1_P4', 0),
    D_C0 = ('J1_P19', 0),
    D_C1 = ('J1_P20', 0),
    D_OEn_1 = ('J1_P3', 1),
    GND_EN = ('J2_P31', 0),
    GND_EUT = ('J2_P33', None),
    SBU1_test = ('J1_P30', None),
    SBU2_test = ('J1_P32', None),
    D_TEST_PLUS = ('J1_P6', None),
    D_TEST_MINUS = ('J1_P8', None),
    V_DIV = ('J1_P9', 0),
    V_DIV_MULT = ('J1_P5', 0),
    REF_LED_EN = ('J1_P35', 0),
    MUX1_EN = ('J1_P15', 0),
    MUX1_A0 = ('J1_P14', 0),
    MUX1_A1 = ('J1_P13', 0),
    MUX1_A2 = ('J1_P12', 0),
    MUX1_A3 = ('J1_P10', 0),
    MUX2_EN = ('J1_P23', 0),
    MUX2_A0 = ('J1_P24', 0),
    MUX2_A1 = ('J1_P21', 0),
    MUX2_A2 = ('J1_P22', 0),
    MUX2_A3 = ('J1_P25', 0),
    TEST_5V = ('J1_P40', 0),
    TEST_20V = ('J1_P39', 0),
    DISCHARGE = ('J1_P34', 0),
    HOST_VBUS_CON = ('J2_P13', 0),
    HOST_VBUS_AUX = ('J2_P14', 0),
    SIG1_OEn = ('J2_P24', 1),
    SIG2_OEn = ('J2_P19', 1),
    SIG1_S = ('J2_P23', 0),
    SIG2_S = ('J2_P25', 0),
    nBTN_PROGRAM = ('J1_P27', None),
    nBTN_RESET = ('J1_P29', None),
    PASS = ('J2_P35', None),
    FAIL = ('J2_P36', None),
    FX2_EN = ('J1_P37', 0),
)

mux_channels = {
    '+1V1': (0, 7),
    '+2V5': (1, 9),
    '+3V3': (1, 8),
    '+5V': (0, 13),
    'VCCRAM': (1, 11),
    'CONTROL_PHY_1V8': (1, 1),
    'CONTROL_PHY_3V3': (0, 6),
    'AUX_PHY_1V8': (1, 0),
    'AUX_PHY_3V3': (1, 2),
    'TARGET_PHY_1V8': (1, 10),
    'TARGET_PHY_3V3': (1, 12),
    'TARGET_A_VBUS': (1, 3),
    'VBUS_CON': (1, 4),
    'VBUS_AUX': (1, 5),
    'VBUS_TA': (1, 7),
    'VBUS_TC': (1, 6),
    'CC1_test': (0, 3),
    'CC2_test': (0, 2),
    'D2_Vf': (0, 1),
    'D3_Vf': (0, 0),
    'D4_Vf': (0, 9),
    'D5_Vf': (0, 8),
    'D6_Vf': (0, 11),
    'D7_Vf': (0, 10),
    'D10_Vf': (0, 12),
    'D11_Vf': (0, 4),
    'D12_Vf': (0, 14),
    'D13_Vf': (0, 5),
    'D14_Vf': (0, 15),
    'CDC': (1, 15),
    'D_TEST_PLUS': (1, 14),
    'D_TEST_MINUS': (1, 13),
}

vbus_channels = {
    'CONTROL':  'VBUS_CON',
    'AUX':      'VBUS_AUX',
    'TARGET-A': 'VBUS_TA',
    'TARGET-C': 'VBUS_TC',
}

gf = GreatFET()

for name, (position, state) in gpio_allocations.items():
    pin = gf.gpio.get_pin(position)
    globals()[name] = pin
    if state is None:
        pin.input()
    elif state:
        pin.high()
    else:
        pin.low()

BOOST_EN.high()
boost = TPS55288(gf)
boost.disable()
