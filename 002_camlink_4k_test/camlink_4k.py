#!/usr/bin/env python3

# This file is Copyright (c) 2019 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

# The Cam Link 4K PCB and IOs have been documented by @GregDavill and @ApertusOSCinema:
# https://wiki.apertus.org/index.php/Elgato_CAM_LINK_4K

# The FX3 exploration tool (and FPGA loader) has been developed by @ktemkin:
# https://github.com/ktemkin/camlink-re

import sys

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.build.generic_platform import *
from litex.build.lattice import LatticePlatform

from litex.soc.interconnect import stream
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *
from litex.soc.cores.clock import *

from litedram.modules import MT41K64M16
from litedram.phy import ECP5DDRPHY

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("clk27", 0, Pins("B11"), IOStandard("LVCMOS25")),

    ("led",   0, Pins("A6"), IOStandard("LVCMOS25")),
    ("led",   1, Pins("A9"), IOStandard("LVCMOS25")),

    ("serial", 0,
        Subsignal("tx", Pins("A6")), # led0
        Subsignal("rx", Pins("A9")), # led1
        IOStandard("LVCMOS25")
    ),

    ("ddram", 0,
        Subsignal("a", Pins(
            "P2 L2 N1 P1 N5 M1 M3 N4",
            "L3 L1 P5 N2 N3"),
            IOStandard("SSTL135_I")),
        Subsignal("ba", Pins("C4 A3 B4"), IOStandard("SSTL135_I")),
        Subsignal("ras_n", Pins("D3"), IOStandard("SSTL135_I")),
        Subsignal("cas_n", Pins("C3"), IOStandard("SSTL135_I")),
        Subsignal("we_n", Pins("D5"), IOStandard("SSTL135_I")),
        Subsignal("cs_n", Pins("B5"), IOStandard("SSTL135_I")),
        Subsignal("dm", Pins("J4 H5"), IOStandard("SSTL135_I")),
        Subsignal("dq", Pins(
            "L5 F1 K4 G1 L4 H1 G2 J3",
            "D1 C1 E2 C2 F3 A2 E1 B1"),
            IOStandard("SSTL135_I"),
            Misc("TERMINATION=75")),
        Subsignal("dqs_p", Pins("K2 H4"), IOStandard("SSTL135D_I"),
            Misc("TERMINATION=OFF"), Misc("DIFFRESISTOR=100")),
        Subsignal("clk_p", Pins("A4"), IOStandard("SSTL135D_I")),
        Subsignal("cke", Pins("E4"), IOStandard("SSTL135_I")),
        Subsignal("odt", Pins("B3"), IOStandard("SSTL135_I")),
        Subsignal("reset_n", Pins("C5"), IOStandard("SSTL135_I")),
        Misc("SLEWRATE=FAST"),
    ),

    ("hdmi_in", 0,
        Subsignal("pclk",  Pins("D11")),
        Subsignal("de",    Pins("C16")),
        Subsignal("hsync", Pins("D16")),
        Subsignal("vsync", Pins("B17")),
        Subsignal("r",     Pins("A7  A8  E9  B9  B6  E6  D6  E7")),
        Subsignal("g",     Pins("A12 A13 B13 C13 D13 E13 A14 C14")),
        Subsignal("b",     Pins("D14 E14 B15 C15 D15 E15 A16 B16")),
        IOStandard("LVCMOS25"),
    ),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(LatticePlatform):
    default_clk_name   = "clk27"
    default_clk_period = 1e9/27e6

    def __init__(self, **kwargs):
        LatticePlatform.__init__(self, "LFE5U-25F-8BG381C", _io, **kwargs)

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_init    = ClockDomain()
        self.clock_domains.cd_por     = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys     = ClockDomain()
        self.clock_domains.cd_sys2x   = ClockDomain()
        self.clock_domains.cd_sys2x_i = ClockDomain(reset_less=True)

        # # #

        self.stop = Signal()

        # clk / rst
        clk27 = platform.request("clk27")
        platform.add_period_constraint(clk27, 1e9/27e6)

        # power on reset
        por_count = Signal(16, reset=2**16-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(ClockSignal())
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # pll
        self.submodules.pll = pll = ECP5PLL()
        pll.register_clkin(clk27, 27e6)
        pll.create_clkout(self.cd_sys2x_i, 2*sys_clk_freq)
        pll.create_clkout(self.cd_init, 27e6)
        self.specials += [
            Instance("ECLKSYNCB",
                i_ECLKI = self.cd_sys2x_i.clk,
                i_STOP  = self.stop,
                o_ECLKO = self.cd_sys2x.clk),
            Instance("CLKDIVF",
                p_DIV     = "2.0",
                i_ALIGNWD = 0,
                i_CLKI    = self.cd_sys2x.clk,
                i_RST     = self.cd_sys2x.rst,
                o_CDIVX   = self.cd_sys.clk),
            AsyncResetSynchronizer(self.cd_init, ~por_done | ~pll.locked),
            AsyncResetSynchronizer(self.cd_sys, ~por_done | ~pll.locked)
        ]

# CamLink4KSoC -------------------------------------------------------------------------------------

class CamLink4KSoC(SoCSDRAM):
    def __init__(self, platform, with_hdmi_in=False):
        sys_clk_freq = int(81e6)

        # SoCSDRAM ---------------------------------------------------------------------------------
        SoCSDRAM.__init__(self, platform, clk_freq=sys_clk_freq, integrated_rom_size=0x8000)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # DDR3 SDRAM -------------------------------------------------------------------------------
        if not self.integrated_main_ram_size:
            self.submodules.ddrphy = ECP5DDRPHY(
                platform.request("ddram"),
                sys_clk_freq=sys_clk_freq)
            self.add_csr("ddrphy")
            self.add_constant("ECP5DDRPHY", None)
            self.comb += self.crg.stop.eq(self.ddrphy.init.stop)
            sdram_module = MT41K64M16(sys_clk_freq, "1:2")
            self.register_sdram(self.ddrphy,
                geom_settings   = sdram_module.geom_settings,
                timing_settings = sdram_module.timing_settings)


        # HDMI In ----------------------------------------------------------------------------------
        if with_hdmi_in:
            from litedram.frontend.fifo import LiteDRAMFIFO
            hdmi_layout = [("de", 1), ("hsync", 1), ("vsync", 1), ("r", 8), ("g", 8), ("b", 8)]
            hdmi_pads   = platform.request("hdmi_in")
            self.clock_domains.cd_hdmi = ClockDomain()
            self.comb += self.cd_hdmi.clk.eq(hdmi_pads.pclk)
            # FIXME: Check hdmi_clk freq vs sys_clk freq
            cdc  = stream.AsyncFIFO(hdmi_layout, 4)
            cdc  = ClockDomainsRenamer({"write": "hdmi", "read": "sys"})(cdc)
            converter = stream.Converter(32, 128)
            self.submodules += cdc, converter
            fifo_base  = 0x00100000 # FIXME: Add control
            fifo_depth = 0x00100000 # FIXME: Add control
            fifo = LiteDRAMFIFO(
                data_width      = 128,
                base            = fifo_base,
                depth           = fifo_depth,
                write_port      = self.sdram.crossbar.get_port(mode="write"),
                write_threshold = fifo_depth - 32,
                read_port       = self.sdram.crossbar.get_port(mode="read"),
                read_threshold  = 32
            )
            self.submodules += fifo
            self.sync.hdmi += [
                cdc.sink.valid.eq(1), # FIXME: Add control
                cdc.sink.de.eq(hdmi_pads.de),
                cdc.sink.hsync.eq(hdmi_pads.hsync),
                cdc.sink.vsync.eq(hdmi_pads.vsync),
                cdc.sink.r.eq(hdmi_pads.r),
                cdc.sink.g.eq(hdmi_pads.g),
                cdc.sink.b.eq(hdmi_pads.b),
            ]
            self.comb += cdc.source.connect(converter.sink, keep={"valid", "ready"})
            self.comb += converter.sink.data.eq(cdc.source.payload.raw_bits())
            self.comb += converter.source.connect(fifo.sink)
            self.comb += fifo.source.ready.eq(1) # FIXME: to FX3, always ready for now

# BlinkSoC -----------------------------------------------------------------------------------------

class BlinkSoC(SoCCore):
    def __init__(self, platform):
        sys_clk_freq = int(81e6)

        # SoCMini ---------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # Leds -------------------------------------------------------------------------------------
        counter = Signal(32)
        self.sync += counter.eq(counter + 1)
        self.comb += platform.request("led", 0).eq(counter[26])

# Build --------------------------------------------------------------------------------------------

def main():
    platform = Platform(toolchain="diamond")
    if "blink" in sys.argv[1:]:
        soc = BlinkSoC(platform)
    else:
        soc = CamLink4KSoC(platform)
    builder = Builder(soc, output_dir="build")
    vns = builder.build(toolchain_path="/usr/local/diamond/3.10_x64/bin/lin64")

if __name__ == "__main__":
    main()
