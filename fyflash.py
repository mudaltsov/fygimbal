#!/usr/bin/env python3
#
# Firmware update tool.
# Use this at your own risk, naturally.
# Run this before powering on the gimbal.

import fyproto
import serial
import struct
import argparse
import binascii

class FirmwarePackage:
    def __init__(self, filename):
        self.data = open(filename, 'rb').read()
        stored_crc16, size0, size1, size2 = struct.unpack('<HHHH', self.data[:8])
        calc_crc16 = binascii.crc_hqx(self.data[2:], 0xffff)
        if calc_crc16 != stored_crc16:
            raise ValueError("Unexpected CRC, found %04X but calculated %04X" % (stored_crc16, calc_crc16))
        self.sizes = (size0, size1, size2)

    def block(self, mcu, offset):
        offset += sum(self.sizes[:mcu])
        return self.data[8+offset*1024:8+(offset+1)*1024]

def waitResponse(command):
    print("Waiting for %02x" % command)
    while True:
        for packet in rx.parse(port.read(1)):
            if packet.framing == fyproto.LONG_FORM:
                if packet.command == command:
                    print("RX %s" % packet)
                    return packet

def send(packet):
    print("TX %s" % packet)
    port.write(packet.pack())

def nextMicrocontroller():
    send(fyproto.Packet(command=0x07, target=0, framing=fyproto.LONG_FORM, data=b'\x01'))
    return waitResponse(0x08)

def writeBlock(number, content):
    header = struct.pack("<HH", number, 0)
    send(fyproto.Packet(command=0x02, target=0, framing=fyproto.LONG_FORM, data=header+content))
    r = waitResponse(0x03)
    if len(r.data) != 2 or struct.unpack('<H', r.data)[0] != number:
        raise ValueError("Unexpected response to firmware block 0x%04x write: %s" % (number, r))

def hexint(x):
    return int(x, 16)


parser = argparse.ArgumentParser(description='Gimbal flasher')
parser.add_argument('--port', default='/dev/ttyAMA0')
parser.add_argument('--first-block', type=hexint, default=0)
parser.add_argument('--num-blocks', type=hexint, default=None)
parser.add_argument('filename')
args = parser.parse_args()

fw = FirmwarePackage(args.filename)
port = serial.Serial(args.port, baudrate=115200)
rx = fyproto.PacketReceiver()

# Power must be off before running this
print("Power on the gimbal now")

# Look for the bootloader's "hello" announcement
hello = waitResponse(0x00)
_unknown, version = struct.unpack("<HH", hello.data)
print("Connected to version %s" % (version / 100.0))

# Respond to the bootloader, prevent normal boot
send(fyproto.Packet(command=0x01, target=0, framing=fyproto.LONG_FORM, data=b''))

# Each microcontroler is programmed, then we ask it to become a pass-through for the next
for mcu in range(3):
    for i in range(args.num_blocks or fw.sizes[mcu]):
        blockNum = i + args.first_block
        writeBlock(blockNum, fw.block(mcu, blockNum))
    nextMicrocontroller()
