from luna.gateware.applets.speed_test import USBSpeedTestDevice
from luna import top_level_cli
from apollo_fpga.gateware.advertiser import ApolloAdvertiser
from amaranth import *

class SpeedTestDevice(Elaboratable):

    def elaborate(self, platform):
        m = Module()
        m.submodules += platform.clock_domain_generator()
        m.submodules += USBSpeedTestDevice(generate_clocks=False,
                                           phy_name="control_phy",
                                           vid=0x1209,
                                           pid=0x0001)
        m.submodules += USBSpeedTestDevice(generate_clocks=False,
                                           phy_name="aux_phy",
                                           vid=0x1209,
                                           pid=0x0002)
        m.submodules += USBSpeedTestDevice(generate_clocks=False,
                                           phy_name="target_phy",
                                           vid=0x1209,
                                           pid=0x0003)
        return m

top_level_cli(SpeedTestDevice)
