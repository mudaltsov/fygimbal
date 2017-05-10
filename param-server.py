#!/usr/bin/env python3

from fyserial import GimbalPort
import asyncio
import websockets

@asyncio.coroutine
def fn(websocket, path):
	global gimbal
	try:
		while True:
			# Multiple commands can be batched into a websocket packet, one per line.
			# Results are sent immediately, not batched.
			results = []
			for line in (yield from websocket.recv()).split('\n'):
				# Each line has space separated tokens
				tokens = line.split()

				if tokens[0] == 'set':
					gimbal.setParam(target=int(tokens[1]), number=int(tokens[2]), value=int(tokens[3]))

				elif tokens[0] == 'get':
					r = gimbal.getParam(target=int(tokens[1]), number=int(tokens[2]))
					yield from websocket.send('value %s %s %s' % (tokens[1], tokens[2], r))

				elif tokens[0] == 'motors':
					gimbal.setMotors(int(tokens[1]))

				else:
					raise ValueError("Unrecognized command %r" % tokens[0])

	except websockets.exceptions.ConnectionClosed:
		return

gimbal = GimbalPort()
gimbal.waitConnect()
print("Conected to gimbal version %s" % gimbal.version)

def run_server(host, port):
	server = websockets.serve(fn, host, port)
	asyncio.get_event_loop().run_until_complete(server)
	print("Server running at ws://%s:%d" % (host, port))
	asyncio.get_event_loop().run_forever()

run_server('tucoflyer.local', 8893)
