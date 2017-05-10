'''
Jupyter Notebook widgets for interacting with the Feiyu Tech gimbal protocol
'''

import ipywidgets
import fyproto
import struct
import threading
import time
from IPython.display import display


class LoopThread(threading.Thread):
    def __init__(self, loopfn):
        threading.Thread.__init__(self)
        self.fn = loopfn
        self.running = True
        self.setDaemon(True)
        self.start()

    def run(self):
        while self.running:
            self.fn()


class ThreadToggle:
    def __init__(self, loopFunc, **kw):
        self.thread = None
        self.loopFunc = loopFunc
        ipywidgets.interact(self.toggler, x=ipywidgets.ToggleButton(**kw))

    def toggler(self, x):
        if x and not self.thread:
            self.thread = LoopThread(self.loopFunc)
        if self.thread and not x:
            self.thread.running = False
            self.thread.join()
            self.thread = None


class MotorControls:
    def __init__(self, gimbal):
        self.gimbal = gimbal
        ipywidgets.interact(self.fn, x=ipywidgets.ToggleButton(description='Motor Enable'))

    def fn(self, x):
        self.gimbal.setMotors(x)


class ParamEditor:
    def __init__(self, gimbal, number, axes=range(3), min=-0x8000, max=0x7fff, step=1):
        self.gimbal = gimbal
        self.number = number
        self.axes = axes
        self.widgets = [None] * 3

        ThreadToggle(self._update, description='Refresh param %02x' % number)

        for t in self.axes:
            v = self.gimbal.getParam(number=number, target=t)
            self.widgets[t] = ipywidgets.IntSlider(description='Param %02x t=%d' % (self.number, t),
                value=v, min=min, max=max, step=step,layout=dict(width='100%'))
            ipywidgets.interact(self._set, x=self.widgets[t], target=ipywidgets.fixed(t))

    def _update(self):
        for t in self.axes:
            self.widgets[t].value = self.gimbal.getParam(number=self.number, target=t)

    def _set(self, x, target):
        self.gimbal.setParam(value=x, number=self.number, target=target)


class Controller:
    def __init__(self, gimbal):
        self.gimbal = gimbal
        self.controlPacket = None

        xw = ipywidgets.IntSlider(value=0, min=-0x8000, max=0x7fff, step=1, layout=dict(width='100%'))
        yw = ipywidgets.IntSlider(value=0, min=-0x8000, max=0x7fff, step=1, layout=dict(width='100%'))
        zw = ipywidgets.IntSlider(value=0, min=-0x8000, max=0x7fff, step=1, layout=dict(width='100%'))
        mw = ipywidgets.IntSlider(value=1, min=0, max=255, step=1, layout=dict(width='100%'))
        ipywidgets.interact(self.setFn, x=xw, y=yw, z=zw, m=mw)

        ThreadToggle(self.loopFn, description='Controller thread')

        self.rate = ipywidgets.IntSlider(description='Update rate',
            value=25, min=1, max=400, step=1, layout=dict(width='100%'))
        display(self.rate)

    def setFn(self, x, y, z, m):
        self.controlPacket = fyproto.Packet(target=0, command=0x01, data=struct.pack('<hhhB', x, y, z, m))
        print(self.controlPacket)

    def loopFn(self):
        if self.controlPacket:
            self.gimbal.send(self.controlPacket)
        time.sleep(1 / self.rate.value)
