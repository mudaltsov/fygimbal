#!/usr/bin/env python3
import fyproto

params = [
    [-1, -1, -7683],                   # 0x00           |
    [0, 0, 0],                         # 0x01           |
    [0, 2, 2],                         # 0x02  dynamic  |       Statuses?
    [0, 0, 59],                        # 0x03  dynamic  |
    [0, 0, 0],                         # 0x04  dynamic  |       Gyro angular velocity
    [0, 0, 0],                         # 0x05           |
    [0, 1294, -2232],                  # 0x06  dynamic  |       Magnetic-related, unknown sensor reading
    [0, 117, 119],                     # 0x07  dynamic  |       Version related?
    [0, 0, 0],                         # 0x08  dynamic  |       Set to 0 by windows software after motor powerup and write to 0x67
    [0, -3754, -296],                  # 0x09  dynamic  |       Gyro angle reading?
    [0, 0, 0],                         # 0x0a           |
    [500, 500, 500],                   # 0x0b           |
    [500, 500, 500],                   # 0x0c           |
    [1, 1, 1],                         # 0x0d           |
    [90, 90, 90],                      # 0x0e           |
    [1, 1, 1],                         # 0x0f           |
    [600, 600, 600],                   # 0x10           |
    [100, 100, 100],                   # 0x11           |
    [1000, 1000, 1000],                # 0x12           |
    [30000, 30000, 30000],             # 0x13           |
    [30000, 30000, 30000],             # 0x14           |
    [1650, 1650, 1650],                # 0x15           |
    [1650, 1650, 1650],                # 0x16           |
    [63, 63, 63],                      # 0x17           |
    [1, 1, 1],                         # 0x18           |
    [500, 500, 500],                   # 0x19           |
    [500, 500, 500],                   # 0x1a           |
    [18000, 18000, 8000],              # 0x1b           |
    [200, 200, 50],                    # 0x1c           |
    [0, 0, 0],                         # 0x1d           |
    [0, 0, 0],                         # 0x1e           |
    [9, 9, 9],                         # 0x1f           |
    [10, 10, 10],                      # 0x20           |
    [0, 1, 2],                         # 0x21           |
    [1000, 1000, 1000],                # 0x22           |
    [1024, 1024, 1024],                # 0x23           |
    [4096, 4096, 4096],                # 0x24           |
    [1, 1, 1],                         # 0x25           |
    [7, 7, 7],                         # 0x26           |
    [16384, 16384, 16384],             # 0x27           |
    [25205, -9389, -19586],            # 0x28  dynamic  |
    [200, 200, 200],                   # 0x29           |
    [20, 20, 20],                      # 0x2a           |
    [20000, 20000, 20000],             # 0x2b           |
    [2945, 2529, 2912],                # 0x2c  dynamic  |       Cooked angles from magnetic sensors
    [30, 30, 30],                      # 0x2d           |
    [-32768, -32768, -32768],          # 0x2e           |
    [0, 0, 0],                         # 0x2f           |
    [100, 100, 100],                   # 0x30           |
    [0, 0, 0],                         # 0x31           |
    [0, 0, 0],                         # 0x32           |
    [4000, 4000, 4000],                # 0x33           |
    [0, 0, 0],                         # 0x34           |
    [20, 20, 20],                      # 0x35           |
    [2500, 2500, 2500],                # 0x36           |
    [1, 1, 1],                         # 0x37           |
    [10, 10, 10],                      # 0x38           |
    [0, 0, 0],                         # 0x39           |
    [0, 0, 0],                         # 0x3a           |
    [0, 0, 0],                         # 0x3b           |
    [0, 0, 0],                         # 0x3c           |
    [1000, 1000, 1000],                # 0x3d           |
    [3, 3, 3],                         # 0x3e           |
    [10, 10, 10],                      # 0x3f           |
    [0, 0, 0],                         # 0x40           |
    [1024, 1024, 1024],                # 0x41           |
    [1024, 1024, 1024],                # 0x42           |
    [0, 0, 0],                         # 0x43           |
    [0, 0, 0],                         # 0x44           |
    [0, 0, 0],                         # 0x45           |
    [0, 0, 0],                         # 0x46           |
    [0, 0, 0],                         # 0x47           |
    [-1935, 1369, -2324],              # 0x48  dynamic  |
    [0, 0, 288],                       # 0x49           |
    [0, 0, 0],                         # 0x4a  dynamic  |         Rates?
    [0, 0, 0],                         # 0x4b           |
    [17, -4042, 0],                    # 0x4c  dynamic  |         Magnetic related sensor value?
    [-400, 3812, 2928],                # 0x4d           |         Stored center location
    [22000, 22000, 22000],             # 0x4e           |
    [50, 50, 50],                      # 0x4f           |
    [2000, 2000, 2000],                # 0x50           |
    [5000, 5000, 5000],                # 0x51           |
    [200, 200, 200],                   # 0x52           |
    [0, 0, 0],                         # 0x53           |
    [0, 0, 0],                         # 0x54           |
    [0, 0, 14],                        # 0x55           |
    [0, 0, 19],                        # 0x56           |
    [0, 0, 23],                        # 0x57           |
    [0, 0, 1],                         # 0x58           |
    [0, 0, 287],                       # 0x59           |
    [0, 0, -149],                      # 0x5a           |
    [0, 0, -54],                       # 0x5b           |
    [0, 0, 75],                        # 0x5c           |
    [0, 0, -47],                       # 0x5d           |
    [0, 0, 1],                         # 0x5e           |
    [1000, 1000, 1000],                # 0x5f           |
    [1000, 1000, 1000],                # 0x60           |
    [1000, 1000, 1000],                # 0x61           |
    [437, 437, 437],                   # 0x62           |
    [0, 0, 0],                         # 0x63           |
    [1696, 2174, 2648],                # 0x64           |
    [900, 900, 900],                   # 0x65           |         Heading follow rate (set by Windows app)
    [0, 0, 0],                         # 0x66  dynamic  |         Flags?
    [0, 0, 0],                         # 0x67           |         Control loop on/off? Set to 1 by windows software after motor poweron
    [0, 0, 0],                         # 0x68           |
    [0, 0, 112],                       # 0x69           |
    [0, 0, 0],                         # 0x6a           |
    [0, 0, 0],                         # 0x6b           |
    [0, 0, 0],                         # 0x6c           |
    [0, 0, 0],                         # 0x6d           |
    [0, 0, 0],                         # 0x6e           |
    [42, 47, 46],                      # 0x6f  dynamic  |
    [17, 67, 54],                      # 0x70  dynamic  |
    [0, 0, 0],                         # 0x71           |         Unused?
    [0, 0, 0],                         # 0x72           |         Unused?
    [0, 0, 0],                         # 0x73           |         Unused?
    [0, 0, 0],                         # 0x74           |         Unused?
    [0, 0, 0],                         # 0x75           |         Unused?
    [0, 0, 0],                         # 0x76           |         Unused?
    [0, 0, 0],                         # 0x77           |         Unused?
    [0, 0, 0],                         # 0x78           |         Unused?
    [0, 0, 0],                         # 0x79           |         Unused?
    [0, 0, 0],                         # 0x7a           |         Unused?
    [0, 0, 0],                         # 0x7b           |         Unused?
    [0, 0, 0],                         # 0x7c           |         Unused?
    [0, 0, 0],                         # 0x7d           |         Unused?
    [0, 0, 0],                         # 0x7e           |         Unused?
    [115, 115, 115],                   # 0x7f           |         Firmware version associated with parameter set
]

gimbal = fyproto.GimbalPort()
gimbal.waitConnect(timeout=10)
print("Connected, version %s" % gimbal.version)

for n, vec in enumerate(params):
    gimbal.setVectorParam(n, vec)
    readback = gimbal.getVectorParam(n)  # Also throttles outgoing data
    print("Set n=%02x to %r (read %r)" % (n, vec, readback))

gimbal.saveParams()
