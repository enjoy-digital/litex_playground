#!/usr/bin/env python3

# This file is Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import argparse

from migen import *

from litex.boards.platforms import arty

from litex.soc.cores.clock import *
from litex.soc.cores.uart import UARTWishboneBridge
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *


# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys       = ClockDomain()
        # # #

        self.submodules.pll = pll = S7PLL(speedgrade=-1)
        self.comb += pll.reset.eq(~platform.request("cpu_reset"))
        pll.register_clkin(platform.request("clk100"), 100e6)
        pll.create_clkout(self.cd_sys,       sys_clk_freq)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(100e6)):
        platform = arty.Platform()

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq,
            cpu_type                = "microwatt",
            integrated_rom_size     = 0x8000,
            integrate_main_ram_size = 0x8000,
            uart_name               = "stub")

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # Bridge -----------------------------------------------------------------------------------
        self.submodules.bridge = UARTWishboneBridge(
            pads     = self.platform.request("serial"),
            clk_freq = sys_clk_freq,
            baudrate = 115200)
        self.bus.add_master("bridge", master=self.bridge.wishbone)

        # LiteScope --------------------------------------------------------------------------------
        analyzer_signals = [
            self.cpu.reset,
            self.cpu.wb_insn,
            self.cpu.wb_data,
        ]
        from litescope import LiteScopeAnalyzer
        self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals,
            depth        = 512,
            clock_domain = "sys",
            csr_csv      = "analyzer.csv")
        self.add_csr("analyzer")

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX Microwatt Test SoC on Arty")
    args = parser.parse_args()
    soc = BaseSoC()
    builder = Builder(soc, output_dir="build")
    builder.build()

if __name__ == "__main__":
    main()
