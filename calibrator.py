#!/usr/bin/env python3

import argparse
from fyserial import GimbalPort

default_params = [[-1, -1, -1], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [500, 500, 500], [500, 500, 500], [1, 1, 1], [90, 90, 90], [1, 1, 1], [600, 600, 600], [100, 100, 100], [1000, 1000, 1000], [30000, 30000, 30000], [30000, 30000, 30000], [1650, 1650, 1650], [1650, 1650, 1650], [63, 63, 63], [1, 1, 1], [500, 500, 500], [500, 500, 500], [18000, 18000, 8000], [200, 200, 50], [0, 0, 0], [0, 0, 0], [9, 9, 9], [10, 10, 10], [0, 1, 2], [1000, 1000, 1000], [1024, 1024, 1024], [4096, 4096, 4096], [1, 1, 1], [7, 7, 7], [16384, 16384, 16384], [0, 0, 0], [200, 200, 200], [20, 20, 20], [20000, 20000, 20000], [0, 0, 0], [30, 30, 30], [0, 0, 0], [0, 0, 0], [100, 100, 100], [0, 0, 0], [0, 0, 0], [4000, 4000, 4000], [0, 0, 0], [20, 20, 20], [2500, 2500, 2500], [1, 1, 1], [10, 10, 10], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [1000, 1000, 1000], [3, 3, 3], [10, 10, 10], [0, 0, 0], [1024, 1024, 1024], [1024, 1024, 1024], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [22000, 22000, 22000], [50, 50, 50], [2000, 2000, 2000], [5000, 5000, 5000], [200, 200, 200], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [1000, 1000, 1000], [1000, 1000, 1000], [1000, 1000, 1000], [437, 437, 437], [0, 0, 0], [0, 0, 0], [900, 900, 900], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [115, 115, 115]]

parser = argparse.ArgumentParser(description=
    'DANGEROUS. Run this at your own risk. Always back up parameters from your gimbal first.')
parser.add_argument('--port', default='/dev/ttyAMA0')
parser.add_argument('--set-defaults', action='store_true')
parser.add_argument('--store-0', action='store_true')
parser.add_argument('--store-1', action='store_true')
parser.add_argument('--save', action='store_true')
args = parser.parse_args()

gimbal = GimbalPort(args.port)
gimbal.waitConnect()
print("Connected, version %s" % gimbal.version)

if args.set_defaults:
    for n, vec in enumerate(default_params):
        gimbal.setVectorParam(n, vec)
        readback = gimbal.getVectorParam(n)  # Also throttles outgoing data
        print("Set n=%02x to %r (read %r)" % (n, vec, readback))

if args.store_0:
    gimbal.storeCalibrationAngle(0)

if args.store_1:
    gimbal.storeCalibrationAngle(1)

if args.save:
    gimbal.saveParams()
