#!/usr/bin/env python3

import fyproto
import time
import argparse

parser = argparse.ArgumentParser(description='Simple remote for the Feiyu Tech gimbal')
parser.add_argument('--port', default='/dev/ttyAMA0')
args = parser.parse_args()

gimbal = fyproto.GimbalPort(args.port)

def showAllParams():
    def cb(params):
        print(params)
        showAllParams()
    gimbal.getParamList( range(128), cb )
showAllParams()

while True:
   time.sleep(0.5)

# Sending other questions maybe
# self.send(Packet(target=2, command=0x09, data=bytes([0x00])))
# self.send(Packet(target=0, command=0x06, data=bytes([0x65])))
# print("Starting up")
# for onoff in (0, 1):
#     for t in (2,1,0):
#         self.tx.queue.put(Packet(target=t, command=0x03, data=bytes([onoff])))
