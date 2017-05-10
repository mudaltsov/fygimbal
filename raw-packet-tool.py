#!/usr/bin/env python3
#
# Send arbitrary packets in the Feiyu gimbal protocol,
# optionally wait for all incoming packets and display them.

import fyproto
import serial
import argparse
import binascii

def hexint(x):
    return int(x, 16)

parser = argparse.ArgumentParser(description='Talk to the Feiyu Tech gimbal')
parser.add_argument('--port', default='/dev/ttyAMA0')
parser.add_argument('--framing', type=hexint, default=fyproto.SHORT_FORM)
parser.add_argument('--command', type=hexint, default=None)
parser.add_argument('--target', type=hexint, default=0)
parser.add_argument('--read', action='store_true')
parser.add_argument('data', nargs='*')
args = parser.parse_args()

port = serial.Serial(args.port, baudrate=115200)
rx = fyproto.PacketReceiver()

if args.command is not None:
    data = binascii.a2b_hex(''.join(args.data))
    packet = fyproto.Packet(command=args.command, target=args.target, framing=args.framing, data=data)
    print(packet)
    port.write(packet.pack())

if args.read:
    while True:
        for packet in rx.parse(port.read(1)):
            print(packet)
