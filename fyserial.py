'''
Serial port interface for talking to Feiyu Tech gimbals.
'''

import struct
import threading
import traceback
import queue
import time

import fyproto
import serial


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
    receiverClass = fyproto.PacketReceiver

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

    def __init__(self, port='/dev/ttyAMA0', baudrate=115200, verbose=True, connected=None):
        self.verbose = verbose
        self.version = None

        self.connectedCV = threading.Condition()
        self.responseQueue = queue.Queue()
        self.port = serial.Serial(port, baudrate=baudrate)
        self._transactionLock = threading.Lock()

        self.tx = self.transmitThreadClass(self.port, verbose=self.verbose)
        self.rx = self.receiverThreadClass(self.port, callback=self._receive, verbose=self.verbose)
        self.rx.start()
        self.tx.start()

        if connected is None:
            self.connected = True
            self.connected = self._testForExistingConnection()
        else:
            self.connected = connected
        if self.verbose:
            if self.connected:
                print("Already connected to gimbal, version %s" % self.version)
            else:
                print("Waiting for gimbal to power on")

    def close(self):
        self.rx.running = False
        self.tx.running = False
        self.rx.join()
        self.tx.join()
        self.port.close()

    def _testForExistingConnection(self):
        if self.verbose:
            print("Checking for existing connection")
        try:
            paramVersion = self.getParam(target=0, number=0x7f, retries=0, timeout=0.1)
            self.version = self.version or (paramVersion / 100)
            return True
        except Timeout:
            return False

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
           and queues responses to be picked up later by _waitResponse().
           '''
        if packet.framing == fyproto.LONG_FORM:
            if packet.command == 0x00:
                self.cmd00 = packet
                _unknown, version = struct.unpack("<HH", packet.data)
                self.version = version / 100.0
                return

        if packet.framing == fyproto.SHORT_FORM:
            if packet.command == 0x0B:
                if self.verbose:
                    print("Connecting to gimbal, firmware version %s" % self.version)
                with self.connectedCV:
                    self.connected = True
                    self.send(fyproto.Packet(target=0, command=0x0b, data=bytes([0x01])))
                    self.connectedCV.notify_all()
                return

            if packet.target == 0x03:
                self.responseQueue.put(packet)
                return

    def _waitResponse(self, command, timeout):
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
        if timeout is None:
            timeout = self.transactionTimeout
        if retries is None:
            retries = self.transactionRetries
        while True:
            try:
                with self._transactionLock:
                    self.send(packet)
                    return self._waitResponse(packet.command, timeout=timeout)
            except Timeout:
                retries -= 1
                if retries < 0:
                    raise

    def setMotors(self, enable, targets=axes):
        # Not sure if order matters
        for t in sorted(targets, reverse=True):
            self.send(fyproto.Packet(target=t, command=0x03, data=struct.pack('B', enable)))

        if enable:
            # Unknown, this init happens in the windows app right after enabling motors
            self.setParam(target=2, number=0x67, value=1)
            self.setParam(target=2, number=0x08, value=0)

    def saveParams(self, targets=axes, timeout=None, retries=None):
        for target in targets:
            p = fyproto.Packet(target=target, command=0x05, data=b'\x00')
            r = self.transaction(p, timeout=timeout, retries=retries)
            if struct.unpack('<B', r.data)[0] != target:
                raise IOError("Failed to save parameters, response %r" % packet)
            if self.verbose:
                print("Saved params on MCU %d" % target)

    def getParam(self, target, number, fmt='h', timeout=None, retries=None):
        p = fyproto.Packet(target=target, command=0x06, data=struct.pack('B', number))
        r = self.transaction(p, timeout=timeout, retries=retries)
        return struct.unpack('<' + fmt, r.data)[0]

    def setParam(self, target, number, value, fmt='h'):
        self.send(fyproto.Packet(target=target, command=0x08, data=struct.pack('<BB' + fmt, number, 0, value)))

    def getVectorParam(self, number, targets=axes, timeout=None, retries=None):
        return tuple(self.getParam(t, number, timeout=timeout, retries=retries) for t in targets)

    def setVectorParam(self, number, vec, targets=axes):
        for i, t in enumerate(targets):
            self.setParam(t, number, vec[i])
