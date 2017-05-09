#!/usr/bin/env python3
import fyproto

gimbal = fyproto.GimbalPort()

slots = [ gimbal.getVectorParam(n) for n in range(128) ]

print(repr(slots))
