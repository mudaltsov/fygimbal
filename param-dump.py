#!/usr/bin/env python3 
import fyproto

gimbal = fyproto.GimbalPort()
gimbal.waitConnect(timeout=10)
print("Connected, version %s" % gimbal.version)

slots = [[0] * 3 for i in range(128)]

for t in range(3):
	for n in range(128):
		value = gimbal.getParam(t, n)
		slots[n][t] = value
		print("t=%02x n=%02x %d" % (t, n, value))

print(repr(slots))
