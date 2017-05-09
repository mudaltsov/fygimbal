#!/usr/bin/env python3

import fyproto
import time
import argparse
import struct

parser = argparse.ArgumentParser(description='Simple remote for the Feiyu Tech gimbal')
parser.add_argument('--port', default='/dev/ttyAMA0')
args = parser.parse_args()
gimbal = fyproto.GimbalPort(args.port)

while True:
    x,y,z = 0,0,0
    mode = 1
    gimbal.send(fyproto.Packet(target=0, command=0x01, data=struct.pack('<hhhB', x, y, z, mode)))
    time.sleep(1.0/90)
