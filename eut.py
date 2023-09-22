# Static data about the EUT.

supplies = (
    ('+3V3',   3.2, 3.4),
    ('+2V5',   2.4, 2.6),
    ('+1V1',   1.0, 1.2),
    ('VCCRAM', 3.2, 3.4))

phy_supplies = (
    ('CONTROL_PHY_3V3', 3.15, 3.4),
    ('CONTROL_PHY_1V8', 1.65, 1.9),
    ('AUX_PHY_3V3',     3.15, 3.4),
    ('AUX_PHY_1V8',     1.65, 1.9),
    ('TARGET_PHY_3V3',  3.15, 3.4),
    ('TARGET_PHY_3V3',  3.15, 3.4))

fpga_leds = (
    ('D7_Vf', 0.6, 0.8), # OSVX0603C1E, Purple
    ('D6_Vf', 0.7, 0.9), # ORH-B36G, Blue
    ('D5_Vf', 0.9, 1.1), # ORH-G36G, Green
    ('D4_Vf', 1.3, 1.5), # E6C0603UYAC1UDA, Yellow
    ('D3_Vf', 1.3, 1.5), # E6C0603SEAC1UDA, Orange
    ('D2_Vf', 1.4, 1.6)) # OSR50603C1E, Red

debug_leds = ( # Values are 3.3V - Vf
    ('D10_Vf', 2.4, 2.6), # MHT192WDT-ICE, Ice Blue
    ('D11_Vf', 2.4, 2.7), # OSK40603C1E, Pink
    ('D12_Vf', 2.5, 2.7), # ORH-W46G, White
    ('D13_Vf', 2.4, 2.7), # OSK40603C1E, Pink
    ('D14_Vf', 2.4, 2.6)) # MHT192WDT-ICE, Ice Blue
