#!/usr/bin/env python3
#
# Prototype serial remote control.
#
# WORK IN PROGRESS... yaw is cool, pitch not working yet.
#
# - Input via XBox 360 USB controller analog stick,
#   mapped to yaw/pitch speed control, with the control
#   software here tracking angles and applying angle limits.
#
# - Also runs a websocket server for live poking at parameters.
#
# * Tested with the 1.15 "rocker position mode" firmware only!
#
# We control yaw by turning off the heading follow loop on
# MCU0 and commanding the speed directly. The pitch speed
# loop on MCU2 can't be turned off, so we command it by
# sending joystick packets.
# 

import time
import argparse
import struct

from fyproto import Packet
from fyserial import GimbalPort
from fysocketserver import run_server_thread
from tinyjoy import deadzone, JoystickThread


def controller(gimbal, js, hz=75.0, yaw_limits=(450, 3800), pitch_limits=(1000, 2040)):

    # We must be ready to respond when the gimbal is powered on.
    # Proceed only once we have a good connection.
    gimbal.waitConnect()

    # Turn off the yaw follow loop so we can control the speed directly.
    # For pitch, we disable it so we can control pitch via joystick packets.
    gimbal.setVectorParam(number=0x63, value=(0,0,0))

    # Zero the velocity output from the follow loop (relevant when the loop is off)
    gimbal.setVectorParam(number=0x03, value=(0,0,0))

    # Turn motors on if they aren't already
    gimbal.setMotors(True)

    # Integrate pitch locally, but keep yaw in param08 on MCU0.
    # This is an offset from the center calibration position,
    # measured in faux PWM microseconds.
    command_pitch = (pitch_limits[0] + pitch_limits[1])/2

    while True:
        time.sleep(1.0/hz)
        controls = js.state()

        # Yaw is a speed (angle per time) integrated on MCU0
        command_yaw_speed = int(pow(deadzone(controls.get('rx', 0)), 3.0) * -300)

        # In this example the Pitch input is speed, but we are commanding
        # the gimbal by sending a joystick packet (in faux-servo units)
        # which applies an offset to the target of its follow loop
        command_pitch_speed = deadzone(controls.get('ry', 0)) * 200.0
        command_pitch = min(pitch_limits[1], max(pitch_limits[0],
            command_pitch + command_pitch_speed / hz))

        # Send joystick packets. The yaw MCU0 doesn't respond to joystick
        # packets, but it will forward them to MCU2 which treats them like
        # inputs from the PWM port. This packet has three int16 values.
        # First is pitch, the next two are yaw related so we won't be using
        # them in this configuration. The final byte is the joystick mode.
        # Note that MCU1 does not accept joystick packets directly once the
        # PC has attached to MCU0.
        gimbal.send(Packet(target=2, command=0x01,
           data=struct.pack('<hhhB', int(command_pitch), 0, 0, 1)))

        # For this particular controller's purposes, our most appropriate
        # absolute notion of yaw (relative to the robot body) will be the
        # magnetic encoder on the yaw axis.
        current_yaw = gimbal.getParam(number=0x2c, target=0)

        # Not perfect, but put the brakes on if we're out of yaw range
        if current_yaw <= yaw_limits[0] and command_yaw_speed < 0:
            command_yaw_speed = 0
        if current_yaw >= yaw_limits[1] and command_yaw_speed > 0:
            command_yaw_speed = 0

        # Send latest yaw speed to MCU0
        gimbal.setParam(number=0x03, target=0, value=command_yaw_speed)

        # Status!
        print("Yaw: current=%d speed=%d  Pitch: command=%d speed=%d" % (
            current_yaw, command_yaw_speed,
            command_pitch, command_pitch_speed))


def main():
    parser = argparse.ArgumentParser(description='Simple remote for the Feiyu Tech gimbal')
    parser.add_argument('--port', default='/dev/ttyAMA0')
    args = parser.parse_args()
    js = JoystickThread()
    gimbal = GimbalPort(args.port, verbose=False)
    run_server_thread(gimbal)
    controller(gimbal, js)


if __name__ == '__main__':
    main()
