#!/usr/bin/env python3

from litex import RemoteClient
from litescope import LiteScopeAnalyzerDriver

wb = RemoteClient()
wb.open()

# # #

analyzer = LiteScopeAnalyzerDriver(wb.regs, "analyzer", debug=True)
analyzer.add_falling_edge_trigger("basesoc_microwatt_reset")
analyzer.run(offset=32)
wb.regs.ctrl_reset.write(1) # Reset CPU
analyzer.wait_done()
analyzer.upload()
analyzer.save("dump.vcd")

# # #

wb.close()