import struct
import binascii
import threading
import traceback
import queue
import time
import serial

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
        '''CRC-16 with an initial value that depends on the packet format'''
        return binascii.crc_hqx(data, cls.formats[framing]['initial_crc_value'])

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


class Timeout(Exception):
    '''Timed out while waiting for a response from the gimbal'''
    pass


class TransmitThread(threading.Thread):
    def __init__(self, port, verbose=False):
        threading.Thread.__init__(self)
        self.port = port
        self.queue = queue.Queue()
        self.running = True
        self.verbose = verbose
        self.setDaemon(True)

    def run(self):
        while self.running:
            try:
                p = self.queue.get(timeout=1.0)
            except queue.Empty:
                pass
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
                if self.verbose:
                    print("RX %s" % packet)
                try:
                    self.callback(packet)
                except:
                    traceback.print_exc()


class GimbalPort:
    '''High-level connection to a Feiyu Tech gimbal,
       with background threads handling serial communication.
       '''
    transmitThreadClass = TransmitThread
    receiverThreadClass = ReceiverThread

    axes = range(3)
    transactionRetries = 15
    transactionTimeout = 2.0
    connectTimeout = 10.0

    def __init__(self, port='/dev/ttyAMA0', baudrate=115200, verbose=True):
        self.verbose = verbose
        self.version = None
        self.connected = False

        self.connectedCV = threading.Condition()
        self.responseQueue = queue.Queue()
        self.port = serial.Serial(port, baudrate=baudrate)

        self.tx = self.transmitThreadClass(self.port, verbose=self.verbose)
        self.rx = self.receiverThreadClass(self.port, callback=self._receive, verbose=self.verbose)
        self.rx.start()
        self.tx.start()

    def close(self):
        self.rx.running = False
        self.tx.running = False
        self.rx.join()
        self.tx.join()
        self.port.close()

    def send(self, packet):
        self.waitConnect()
        self.tx.queue.put(packet)

    def waitConnect(self, timeout=None):
        if self.connected:
            return
        timeout = timeout or self.connectTimeout
        with self.connectedCV:
            self.connectedCV.wait_for(lambda: self.connected, timeout=timeout)
        if not self.connected:
            raise Timeout()

    def _receive(self, packet):
        '''One packet received by the ReceiverThread.
           This immediately handles some packets,
           and queues responses to be picked up later by waitResponse().
           '''
        if packet.framing == LONG_FORM:
            if packet.command == 0x00:
                self.cmd00 = packet
                _unknown, version = struct.unpack("<HH", packet.data)
                self.version = version / 100.0
                return

        if packet.framing == SHORT_FORM:
            if packet.command == 0x0B:
                if self.verbose:
                    print("Connecting to gimbal, firmware version %s" % self.version)
                with self.connectedCV:
                    self.connected = True
                    self.send(Packet(target=0, command=0x0b, data=bytes([0x01])))
                    self.connectedCV.notify_all()
                return

            if packet.target == 0x03:
                self.responseQueue.put(packet)
                return

    def waitResponse(self, command, timeout):
        '''Wait for a response to the indicated command, with a timeout.'''
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

    def transaction(self, packet, timeout=None, retries=None):
        '''Send a packet, and wait for the corresponding response, with retry on timeout'''
        self.waitConnect()
        timeout = timeout or self.transactionTimeout
        retries = retries or self.transactionRetries
        while retries >= 0:
            try:
                self.send(packet)
                return self.waitResponse(packet.command, timeout=timeout)
            except Timeout:
                retries -= 1

    def saveParams(self, targets=axes):
        for target in targets:
            r = self.transaction(Packet(target=target, command=0x05, data=b'\x00'))
            if struct.unpack('<B', r.data)[0] != target:
                raise IOError("Failed to save parameters, response %r" % packet)
            if self.verbose:
                print("Saved params on MCU %d" % target)

    def getParam(self, target, number, fmt='h'):
        r = self.transaction(Packet(target=target, command=0x06, data=struct.pack('B', number)))
        return struct.unpack('<' + fmt, r.data)[0]

    def setParam(self, target, number, value, fmt='h'):
        self.send(Packet(target=target, command=0x08, data=struct.pack('<BB' + fmt, number, 0, value)))

    def getVectorParam(self, number, targets=axes):
        return tuple(self.getParam(t, number) for t in targets)

    def setVectorParam(self, number, vec, targets=axes):
        for i, t in enumerate(targets):
            self.setParam(t, number, vec[i])
