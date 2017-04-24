import sigrokdecode as srd
from fyproto import PacketReceiver

class Decoder(srd.Decoder):
    api_version = 2
    id = 'fygimbal'
    name = 'FY-Gimbal'
    longname = 'Feiyu Tech gimbal control protocol over RS232'
    desc = 'Firmware updates and settings and such, over YAW and PITCH wires.'
    license = 'mit'
    inputs = ['uart']
    outputs = ['fygimbal']
    annotations = (
        ('rx-data', ''),
        ('tx-data', ''),
    )
    annotation_rows = (
        ('rx', 'RX Data', (0,)),
        ('tx', 'TX Data', (1,)),
    )

    def __init__(self):
        self.begin_ss = None

    def start(self):
        self.receivers = ( PacketReceiver(), PacketReceiver() )
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_python = self.register(srd.OUTPUT_PYTHON)

    def decode(self, ss, es, data):
        ptype, rxtx, pdata = data
        if ptype == 'DATA':
            byteval = bytes((pdata[0],))
            receiver = self.receivers[rxtx]

            if len(receiver.buffer) == 0:
                self.begin_ss = ss
            for packet in receiver.parse(byteval):
                packet_ss = self.begin_ss or ss
                self.put(packet_ss, es, self.out_ann,
                    [rxtx, ["%s %s" % (self.annotations[rxtx][0], packet)]])
                self.put(packet_ss, es, self.out_python, ['PACKET', packet])

