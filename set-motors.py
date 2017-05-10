#!/usr/bin/env python3

import time
import argparse
import struct
from fyproto import Packet
from fyserial import GimbalPort

parser = argparse.ArgumentParser(description='Simple remote for the Feiyu Tech gimbal')
parser.add_argument('--port', default='/dev/ttyAMA0')
parser.add_argument('--on', action='store_true')
args = parser.parse_args()

gimbal = GimbalPort(args.port)
gimbal.setMotors(args.on)
gimbal.flush()
