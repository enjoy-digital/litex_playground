# Cam Link 4K experiments

## Prerequisites
Yosys/Nextpnr ECP5 toolchain installed.

## Installing LiteX
```sh
$ wget https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py
$ chmod +x litex_setup.py
$ sudo ./litex_setup.py init install
```
## Building IOs streamer bitstream
```sh
$ ./ios_stream.py
```
Load the bistream and probe to board with a scope able to decode UART or with a USB-UART dongle and a terminal configured to 9600 bauds :)

## Building Led blink bitstream
```sh
$ ./camlink_4k.py blink
```

## Building LiteX SoC bitstream
```sh
$ ./camlink_4k.py
```

## Loading bitstream
```sh
$ sudo pip3 install pyusb pyusb tqdm pyfwup
$ git clone https://github.com/ktemkin/camlink-re
$ cd camlink-re/exploration
$ sudo python3 camlink configure <bitstream.bit>
```

## Notes
iodb.json from PrjTrellis
