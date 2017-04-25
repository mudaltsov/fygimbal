#!/usr/bin/env python3

import fyproto
import serial
import argparse
import binascii
import struct

parser = argparse.ArgumentParser(description='Simple remote for the Feiyu Tech gimbal')
parser.add_argument('--port', default='/dev/ttyAMA0')
args = parser.parse_args()

port = serial.Serial(args.port, baudrate=115200)
rx = fyproto.PacketReceiver()

def send(packet):
    print("TX %s" % packet)
    port.write(packet.pack())

cmd06_counter = 0

while True:
    for packet in rx.parse(port.read(1)):
        print("RX %s" % packet)

        if packet.framing == 0xAA55 and packet.command == 0x00:
            _, version = struct.unpack("<HH", packet.data)
            print("Version packet, %d.%d" % (version // 100, version % 100))

        if packet.framing == 0x5AA5 and packet.command == 0x0B:
            print("Responding to init packet")
            send(fyproto.Packet(target=0, command=0x0b, data=bytes([0x01])))
            # print("Sending other questions maybe")
            # send(fyproto.Packet(target=2, command=0x09, data=bytes([0x00])))
            # send(fyproto.Packet(target=0, command=0x06, data=bytes([0x65])))
            print("Starting up")
            for onoff in (0, 1):
                for t in (2,1,0):
                    send(fyproto.Packet(target=t, command=0x03, data=bytes([onoff])))

        # if packet.framing == 0x5AA5 and packet.command == 0x06:
        #     send(fyproto.Packet(target=0, command=0x06, data=bytes([cmd06_counter])))
        #     cmd06_counter += 1

