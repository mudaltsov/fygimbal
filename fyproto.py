import struct
import binascii
import threading
import traceback
import queue
import time

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
                if self.verbose:
                    print("CRC mismatch, received %04x and expected %04x" % (rx_crc, calc_crc))
                continue

            yield Packet(command, framing, target, data)


class TransmitThread(threading.Thread):
    def __init__(self, port, hz, verbose=False):
        threading.Thread.__init__(self)
        self.port = port
        self.queue = queue.Queue()
        self.idleInterval = 1.0 / hz
        self.idlePackets = []
        self.running = True
        self.verbose = verbose
        self.setDaemon(True)

    def run(self):
        while self.running:
            try:
                p = self.queue.get(timeout=self.idleInterval)
            except queue.Empty:
                for p in self.idlePackets:
                    self.port.write(p.pack())
            else:
                if self.verbose:
                    print("TX %s" % p)
                self.port.write(p.pack())


class ReceiverThread(threading.Thread):
    receiverClass = PacketReceiver

    def __init__(self, port, callback, verbose=False):
        threading.Thread.__init__(self)
        self.port = port
        self.callback = callback
        self.running = True
        self.verbose = verbose
        self.receiver = self.receiverClass()
        self.setDaemon(True)

    def run(self):
        while self.running:
            for packet in self.receiver.parse(self.port.read(1)):
                try:
                    self.callback(packet)
                except:
                    traceback.print_exc()


class Timeout(Exception):
    pass


class GimbalPort:
    transmitThreadClass = TransmitThread
    receiverThreadClass = ReceiverThread

    def __init__(self, port='/dev/ttyAMA0', baudrate=115200, hz=75.0, timeout=5.0, verbose=True):
        self.timeout = timeout
        self.verbose = verbose
        self.version = None
        self.connected = False
        self.connectedCV = threading.Condition()
        self.responseQueue = queue.Queue()
        self.port = serial.Serial(port, baudrate=baudrate)
        self.tx = self.transmitThreadClass(self.port, hz=hz, verbose=self.verbose)
        self.rx = self.receiverThreadClass(self.port, self.receive, verbose=self.verbose)
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

    def waitConnect(self, timeout=None):
        timeout = timeout or self.timeout
        with self.connectedCV:
            self.connectedCV.wait_for(lambda: self.connected, timeout=timeout)
        if not self.connected:
            raise Timeout()

    def waitResponse(self, command, timeout=None):
        timeout = timeout or self.timeout
        deadline = timeout and (time.time() + timeout)
        try:
            while True:
                timeout = deadline and max(0, deadline - time.time())
                packet = self.responseQueue.get(timeout=timeout)
                if packet.command == command:
                    return packet
                if self.verbose:
                    print("Ignored response %r" % packet)
        except queue.Empty:
            raise Timeout()

    def receive(self, packet):
        if self.verbose:
            print("RX %s" % packet)

        if packet.framing == LONG_FORM:
            if packet.command == 0x00:
                self.cmd00 = packet
                _unknown, version = struct.unpack("<HH", packet.data)
                self.version = version / 100.0
                return

        if packet.framing == SHORT_FORM:
            if packet.command == 0x0B:
                if self.verbose:
                    print("Responding to init packet")
                self.send(Packet(target=0, command=0x0b, data=bytes([0x01])))
                with self.connectedCV:
                    self.connected = True
                    self.connectedCV.notify_all()
                return

            # Give the main thread a chance to handle other t=03 packets
            if packet.target == 0x03:
                self.responseQueue.put(packet)

    def saveParams(self, target, timeout=None):
        self.send(Packet(target=target, command=0x05, data=bytes([0x00])))
        packet = self.waitResponse(command=0x05, timeout=timeout)
        if struct.unpack('<B', packet.data)[0] != target:
            raise IOError("Failed to save parameters, response %r" % packet)

    def getParam(self, target, number, format='h', timeout=None):
        self.send(Packet(target=target, command=0x06, data=bytes([ number ])))
        packet = self.waitResponse(command=0x06, timeout=timeout)
        return struct.unpack('<' + format, packet.data)[0]

    def setParam(self, target, number, value, format='h'):
        self.send(Packet(target=target, command=0x08, data=struct.pack('<BB' + format, number, 0, value)))
