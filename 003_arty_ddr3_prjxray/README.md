# Minimal Arty DDR3 Design for tests with Project X-Ray

Vivado toolchain installed.

## Installing LiteX
```sh
$ wget https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py
$ chmod +x litex_setup.py
$ sudo ./litex_setup.py init install
```
## Building design
```sh
$ ./arty.py --build
```

## Loading design
```sh
$ ./arty.py --load
```

## Test design
```sh
$ lxserver --uart --uart-port=/dev/ttyUSBX
$ ./test_sdram.py
```
should produce results similar to:
```
Minimal Arty DDR3 Design for tests with Project X-Ray 2020-01-31 15:41:14
Release reset
Bring CKE high
Load Mode Register 2, CWL=5
Load Mode Register 3
Load Mode Register 1
Load Mode Register 0, CL=6, BL=8
ZQ Calibration
bitslip 0: |00|01|02|03|04|05|06|07|08|09|10|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|
bitslip 1: |..|..|..|..|..|..|..|..|..|..|..|..|..|13|14|15|16|17|18|19|20|21|22|23|24|25|..|..|..|..|..|..|
bitslip 2: |..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|29|30|31|
bitslip 3: |..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|
bitslip 4: |..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|
bitslip 5: |..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|
bitslip 6: |..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|
bitslip 7: |..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|..|
```
