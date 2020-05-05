#!/usr/bin/env python3

from fractions import Fraction

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.build.generic_platform import *

from litex.boards.platforms import minispartan6

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

scope_io = [
    ("scope0", 0, Pins("B:0")),
    ("scope1", 0, Pins("C:0")),
]

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, clk_freq, use_s6pll=True):
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sys_ps = ClockDomain()

        # # #

        self.cd_sys.clk.attr.add("keep")
        self.cd_sys_ps.clk.attr.add("keep")

        self.submodules.pll = pll = S6PLL(speedgrade=-1)
        pll.register_clkin(platform.request("clk32"), 32e6)
        pll.create_clkout(self.cd_sys, clk_freq, phase=0)
        pll.create_clkout(self.cd_sys_ps, clk_freq, phase=180)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCMini):
    def __init__(self, sys_clk_freq=int(8e6)):
        platform = minispartan6.Platform()
        platform.add_extension(scope_io)
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq)

        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # led
        counter = Signal(32)
        self.sync += counter.eq(counter + 1)
        self.comb += platform.request("user_led", 0).eq(counter[26])

        # scope
        self.specials += Instance("ODDR2", p_DDR_ALIGNMENT="NONE",
                                  p_INIT=0, p_SRTYPE="SYNC",
                                  i_D0=0, i_D1=1, i_S=0, i_R=0, i_CE=1,
                                  i_C0=ClockSignal("sys"), i_C1=~ClockSignal("sys"),
                                  o_Q=platform.request("scope0"))
        self.specials += Instance("ODDR2", p_DDR_ALIGNMENT="NONE",
                                  p_INIT=0, p_SRTYPE="SYNC",
                                  i_D0=0, i_D1=1, i_S=0, i_R=0, i_CE=1,
                                  i_C0=ClockSignal("sys_ps"), i_C1=~ClockSignal("sys_ps"),
                                  o_Q=platform.request("scope1"))

# Build --------------------------------------------------------------------------------------------

def main():
    soc = BaseSoC()
    builder = Builder(soc, output_dir="build")
    builder.build()


if __name__ == "__main__":
    main()
