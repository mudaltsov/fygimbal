#!/bin/sh
./unpack.py
r2 -a arm -m 0x8004000 -b 16 mcu0.bin -q -w -i mcu0-patches.r2
r2 -a arm -m 0x8004000 -b 16 mcu1.bin -q -w -i mcu1-patches.r2
r2 -a arm -m 0x8004000 -b 16 mcu2.bin -q -w -i mcu2-patches.r2
./pack.py
