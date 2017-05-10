#!/usr/bin/env python3
from fyserial import GimbalPort

gimbal = GimbalPort()

slots = [ gimbal.getVectorParam(n) for n in range(128) ]

print(repr(slots))
