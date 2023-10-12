from luna.gateware.applets.speed_test import USBInSpeedTestDevice
from luna import top_level_cli
from amaranth import *

class SpeedTestDevice(Elaboratable):

    def elaborate(self, platform):
        m = Module()
        control_phy = platform.request('control_phy')
        aux_phy = platform.request('aux_phy')
        target_phy = platform.request('target_phy')
        m.submodules += platform.clock_domain_generator()
        m.submodules += USBInSpeedTestDevice(generate_clocks=False,
                                             phy=control_phy,
                                             vid=0x1209,
                                             pid=0x0001)
        m.submodules += USBInSpeedTestDevice(generate_clocks=False,
                                             phy=aux_phy,
                                             vid=0x1209,
                                             pid=0x0002)
        m.submodules += USBInSpeedTestDevice(generate_clocks=False,
                                             phy=target_phy,
                                             vid=0x1209,
                                             pid=0x0003)
        return m

top_level_cli(SpeedTestDevice)
