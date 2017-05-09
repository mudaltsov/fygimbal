#!/usr/bin/env python3 
import fyproto

gimbal = fyproto.GimbalPort(verbose=False)
gimbal.waitConnect(timeout=10)
print("Connected, version %s" % gimbal.version)

slots = [[None] * 3 for i in range(128)]

tRange = range(3)
nRange = range(128)

# Clear
print("\x1b[2J")

def update(n, sgr=[0]):
	cols = 4
	print("\x1b[%sm\x1b[%d;%dH[%02x] %-25r\x1b[0m" % (
		';'.join(map(str, sgr)),
		3 + n/cols, 10 + (n%cols) * 30,
		n, slots[n]))


# Initial values
for t in tRange:
	for n in nRange:
		slots[n][t] = gimbal.getParam(t, n)
		update(n)


while True:
	for t in tRange:
		for n in nRange:
			previous = slots[n][t]
			current = gimbal.getParam(t, n)
			if previous != current:
				slots[n][t] = current
				update(n, sgr=[1])
