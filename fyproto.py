import struct
import binascii
import threading
import traceback
import queue

import serial
import crc16

LONG_FORM = 0xaa55
SHORT_FORM = 0x5aa5

# LONG_FORM commands
#   cmd00  Init / Firmware version

# SHORT_FORM commands
#   cmd01  Control data?
#   cmd02
#   cmd03  On/Off
#   cmd04
#   cmd05  Save (per-axis?) config
#   cmd06  Get 16-bit value from 8-bit (per-axis?) config space
#   cmd07  Set 16-bit value in 8-bit (main?) config space
#   cmd08  Set 16-bit value in 8-bit (per-axis?) config space
#   cmd09  Unknown get, 12 bytes
#   cmd0a
#   cmd0b  Init PC control handshake
#   cmd0c
#   cmd0d  IMU data?

# Are these param defaults?
# [-1, 0, 2, -600, 0, 0, -3848, 115, 0, 5512, 0, 500, 500, 1, 90, 1, 600, 100, 1000, 30000, 30000, 1650, 1650, 63, 1, 500, 500, 8000, 50, 0, 0, 9, 10, 2, 1000, 1024, 4096, 1, 7, 16384, 30581, 200, 20, 20000, 1297, 30, -32768, 0, 100, 0, 0, 4000, 0, 20, 2500, 1, 10, 0, 0, 0, 0, 1000, 3, 10, 0, 1024, 1024, 0, 0, 0, 0, 0, -3868, 0, 0, 0, 0, 0, 22000, 50, 2000, 5000, 200, 0, 0, -7176, -27381, -28261, 0, 352, -305, 0, 0, 0, 0, 1000, 1000, 1000, 437, 0, 0, 900, 0, 0, 0, 112, 0, 0, 0, 0, 0, 54, 48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 115]
# [-1, 0, 2, -600, 0, 0, -3898, 115, 22, 6188, 0, 500, 500, 1, 90, 1, 600, 100, 1000, 30000, 30000, 1650, 1650, 63, 1, 500, 500, 8000, 50, 0, 0, 9, 10, 2, 1000, 1024, 4096, 1, 7, 16384, -26599, 200, 20, 20000, 1371, 30, -32768, 0, 100, 0, 0, 4000, 0, 20, 2500, 1, 10, 0, 0, 0, 0, 1000, 3, 10, 0, 1024, 1024, 0, 0, 0, 0, 0, -3897, 0, 0, 0, 0, 0, 22000, 50, 2000, 5000, 200, 0, 0, -9962, -8056, 26107, 0, 345, -308, -1, 0, 0, 0, 1000, 1000, 1000, 437, 0, 0, 900, 0, 0, 0, 112, 0, 0, 0, 0, 0, 52, 47, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 115]

class Packet:
    formats = {
        LONG_FORM: { 'len_struct': 'H', 'initial_crc_value': 0xffff },
        SHORT_FORM: { 'len_struct': 'B', 'initial_crc_value': 0x0000 },
    }

    def __init__(self, command, framing=SHORT_FORM, target=0, data=b''):
        if framing not in self.formats:
            raise ValueError('Unknown framing type 0x%04x', framing)
        self.command = command
        self.framing = framing
        self.target = target
        self.data = data

    def __repr__(self):
        return '<Pkt-%04X t=%02x cmd=%02x [%s]>' % (
            self.framing, self.target, self.command, binascii.b2a_hex(self.data).decode())

    @classmethod
    def crc(cls, framing, data):
        return crc16.crc16xmodem(data, cls.formats[framing]['initial_crc_value'])

    def format_option(self, name, default=None):
        return self.formats[self.framing].get(name, default)

    def pack(self):
        parts = [
            struct.pack('BB', self.target, self.command),
            struct.pack('<' + self.format_option('len_struct'), len(self.data)),
            self.data
        ]
        parts.append(struct.pack('<H', self.crc(self.framing, b''.join(parts))))
        return struct.pack('<H', self.framing) + b''.join(parts)


class PacketReceiver:
    packetClass = Packet

    def __init__(self):
        self.buffer = b''

    def parse(self, data):
        '''Yields a list of Packet instances, from 'data' or prior bytes.'''
        self.buffer += data
        while len(self.buffer) >= 2:
            framing = struct.unpack('<H', self.buffer[:2])[0]
            if framing not in self.packetClass.formats:
                self.buffer = self.buffer[1:]
                continue

            header_format = '<BB' + self.packetClass.formats[framing]['len_struct']
            header_len = struct.calcsize(header_format)
            header = self.buffer[2:2+header_len]
            if len(self.buffer) < header_len + 4:
                break
            target, command, data_len = struct.unpack(header_format, header)

            if len(self.buffer) < header_len + data_len + 4:
                break
            data = self.buffer[2+header_len:2+header_len+data_len]
            rx_crc = struct.unpack('<H', self.buffer[2+header_len+data_len:4+header_len+data_len])[0]
            self.buffer = self.buffer[4+header_len+data_len:]

            calc_crc = self.packetClass.crc(framing, header + data)
            if rx_crc != calc_crc:
                print("CRC mismatch, received %04x and expected %04x" % (rx_crc, calc_crc))
                continue

            yield Packet(command, framing, target, data)


class TransmitThread(threading.Thread):
    def __init__(self, port, hz):
        threading.Thread.__init__(self)
        self.port = port
        self.queue = queue.Queue()
        self.idleInterval = 1.0 / hz
        self.idlePackets = []
        self.running = True
        self.setDaemon(True)

    def run(self):
        while self.running:
            try:
                p = self.queue.get(timeout=self.idleInterval)
            except queue.Empty:
                for p in self.idlePackets:
                    self.port.write(p.pack())
            else:
                # print("TX %s" % p)
                self.port.write(p.pack())


class ReceiverThread(threading.Thread):
    receiverClass = PacketReceiver

    def __init__(self, port, callback):
        threading.Thread.__init__(self)
        self.port = port
        self.callback = callback
        self.running = True
        self.receiver = self.receiverClass()
        self.setDaemon(True)

    def run(self):
        while self.running:
            for packet in self.receiver.parse(self.port.read(1)):
                try:
                    self.callback(packet)
                except:
                    traceback.print_exc()


class GimbalPort:
    transmitThreadClass = TransmitThread
    receiverThreadClass = ReceiverThread

    def __init__(self, port='/dev/ttyAMA0', baudrate=115200, hz=75.0):
        self.version = None
        self.connected = False
        self.paramCallbackQueue = queue.Queue(1)
        self.port = serial.Serial(port, baudrate=baudrate)
        self.tx = self.transmitThreadClass(self.port, hz=hz)
        self.rx = self.receiverThreadClass(self.port, self.receive)
        self.rx.start()
        self.tx.start()

    def close(self):
        self.rx.running = False
        self.tx.running = False
        self.rx.join()
        self.tx.join()
        self.port.close()

    def send(self, packet):
        self.tx.queue.put(packet)

    def receive(self, packet):
        if packet.framing == LONG_FORM:
            if packet.command == 0x00:
                _unknown, version = struct.unpack("<HH", packet.data)
                self.version = version / 100.0
                return

        if packet.framing == SHORT_FORM:
            if packet.command == 0x0B:
                print("Responding to init packet")
                self.send(Packet(target=0, command=0x0b, data=bytes([0x01])))
                self.connected = True
                return

            if packet.command == 0x06:
                self.paramCallbackQueue.get(block=False)(struct.unpack("<h", packet.data)[0])
                return

            if packet.command == 0x05:
                print("Response from saving, %02x" % packet.data[0])
                return

        # Other packets, log them raw
        print("RX %s" % packet)

    def saveParams(self, target=2):
        self.send(Packet(target=target, command=0x05, data=bytes([0x00])))

    def getParamList(self, numbers, callback, target=2):
        results = [None] * len(numbers)
        for i, n in enumerate(numbers):
            def cb(value, i=i):
                results[i] = value
                if i + 1 == len(numbers):
                    callback(results)
            self.getParam(n, cb, target)

    def getParam(self, number, callback, target=2):
        self.paramCallbackQueue.put(callback)
        self.send(Packet(target=target, command=0x06, data=bytes([ number ])))

    def setParam(self, number, value, target=2):
        self.send(Packet(target=target, command=0x08, data=struct.pack("<BBh", number, 0, value)))
