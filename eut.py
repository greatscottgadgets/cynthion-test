# Static data about the EUT.

supplies = (
    ('+3V3',   3.25, 3.35),
    ('+2V5',   2.45, 2.55),
    ('+1V1',   1.05, 1.20),
    ('VCCRAM', 3.25, 3.35))

phy_supplies = (
    ('CONTROL_PHY_3V3', 3.25, 3.35),
    ('CONTROL_PHY_1V8', 1.70, 1.90),
    ('AUX_PHY_3V3',     3.25, 3.35),
    ('AUX_PHY_1V8',     1.70, 1.90),
    ('TARGET_PHY_3V3',  3.25, 3.35),
    ('TARGET_PHY_1V8',  1.70, 1.90))

fpga_leds = (
    ('D7_Vf', 0.65, 0.85), # OSVX0603C1E, Purple
    ('D6_Vf', 0.75, 0.95), # ORH-B36G, Blue
    ('D5_Vf', 1.00, 1.25), # ORH-G36G, Green
    ('D4_Vf', 1.35, 1.55), # E6C0603UYAC1UDA, Yellow
    ('D3_Vf', 1.35, 1.55), # E6C0603SEAC1UDA, Orange
    ('D2_Vf', 1.40, 1.60)) # OSR50603C1E, Red

debug_leds = ( # Values are 3.3V - Vf
    ('D10_Vf', 2.45, 2.65), # MHT192WDT-ICE, Ice Blue
    ('D11_Vf', 2.50, 2.70), # OSK40603C1E, Pink
    ('D12_Vf', 2.45, 2.65), # ORH-W46G, White
    ('D13_Vf', 2.50, 2.75), # OSK40603C1E, Pink
    ('D14_Vf', 2.45, 2.65)) # MHT192WDT-ICE, Ice Blue
