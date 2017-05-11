#!/usr/bin/env python3
from fyserial import GimbalPort

gimbal = GimbalPort(verbose=False)

def vecdiff(a,b):
	return tuple(x-b[i] for i, x in enumerate(a))	

while True:
	current_angle = gimbal.getVectorParam(0x2c)
	cal_slots = tuple(map(gimbal.getVectorParam, (0x4d, 0x64)))

	print("current={0} CAL0 stored={1} diff={2} CAL1 stored={3} diff={4}".format(
		current_angle, cal_slots[0], vecdiff(current_angle, cal_slots[0]),
		cal_slots[1], vecdiff(current_angle, cal_slots[1])))
