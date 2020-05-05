#!/usr/bin/env python3

# This file is Copyright (c) 2019 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

# CAM Link 4K IOs streamer.

import sys

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.build.generic_platform import *
from litex.build.lattice import LatticePlatform

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

# IOs ----------------------------------------------------------------------------------------------

_io = [("clk27", 0, Pins("B11"), IOStandard("LVCMOS33"))]

# Platform -----------------------------------------------------------------------------------------

class Platform(LatticePlatform):
    default_clk_name   = "clk27"
    default_clk_period = 1e9/27e6

    def __init__(self, **kwargs):
        LatticePlatform.__init__(self, "LFE5UM-25F-8BG381C", _io, **kwargs)

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_por = ClockDomain(reset_less=True)

        # # #

        # Clk / Rst
        clk27 = platform.request("clk27")
        platform.add_period_constraint(clk27, 1e9/27e6)

        # Power on reset
        por_count = Signal(16, reset=2**16-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(ClockSignal())
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL
        self.submodules.pll = pll = ECP5PLL()
        pll.register_clkin(clk27, 27e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)
        self.specials += AsyncResetSynchronizer(self.cd_sys, ~por_done | ~pll.locked)

# IOStreamer ---------------------------------------------------------------------------------------

class IOStreamer(Module):
    """Stream an identifier string over UART"""
    def __init__(self, identifier, pad, sys_clk_freq, baudrate):
        from litex.soc.cores.uart import RS232PHYTX
        assert len(identifier) <= 4
        for i in range(4-len(identifier)):
            identifier += " "

        # UART
        pads = Record([("tx", 1)])
        self.comb += pad.eq(pads.tx)
        phy = RS232PHYTX(pads, int((baudrate/sys_clk_freq)*2**32))
        self.submodules += phy

        # Memory
        mem  = Memory(8, 4, init=[ord(identifier[i]) for i in range(4)])
        port = mem.get_port()
        self.specials += mem, port
        self.comb += phy.sink.valid.eq(1)
        self.comb += phy.sink.data.eq(port.dat_r)
        self.sync += If(phy.sink.ready, port.adr.eq(port.adr + 1))

# IOsStreamSoC -------------------------------------------------------------------------------------

class IOsStreamSoC(SoCMini):
    def __init__(self, platform):
        sys_clk_freq = int(27e6)
        SoCMini.__init__(self, platform, sys_clk_freq)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # Get IOs from JSON database ---------------------------------------------------------------
        import json
        json_file = open("iodb.json")
        json_data = json.load(json_file)
        json_file.close()
        ios = list(json_data["packages"]["CABGA381"].keys())

        # Exclude some IOs -------------------------------------------------------------------------
        excludes = []
        excludes += ["B11"]
        for exclude in excludes:
            ios.remove(exclude)

        # Create platform IOs ----------------------------------------------------------------------
        for io in ios:
            platform.add_extension([(io, 0, Pins(io), IOStandard("LVCMOS33"), Misc("DRIVE=4"))])

        # Stream IOs' identifiers to IOs -----------------------------------------------------------
        for io in ios:
            io_streamer = IOStreamer(io, platform.request(io), sys_clk_freq, baudrate=9600)
            self.submodules += io_streamer

# Build --------------------------------------------------------------------------------------------

def main():
    platform = Platform(toolchain="trellis")
    soc = IOsStreamSoC(platform)
    builder = Builder(soc, output_dir="build")
    vns = builder.build()

if __name__ == "__main__":
    main()
