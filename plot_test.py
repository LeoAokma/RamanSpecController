import math
import itertools
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.animation import FuncAnimation
import serial
import platform
from communication import get_device_list, continuous_reading, byte_process
import numpy as np
import time


ls = get_device_list()
for _ in ls:
    print(_.name)
print(platform.system())
if platform.system() == 'Darwin':
    device = "/dev/{}".format(ls[1].name)
else:
    device = 'COM3'

ser = serial.Serial(device, 115200, timeout=1)
# 十六进制的发送
result = ser.write('#Start%'.encode("utf-8"))
read = ser.read(3694 * 2)
y = byte_process(read)


def data_gen():
    while True:
        read = ser.read(3694 * 2)
        yield byte_process(read)


class Plot(tk.Frame):

    def __init__(self, master, data_source, interval=100, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.data_source = data_source
        self.figure = Figure((5, 5), 100)
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.axis = self.figure.add_subplot(111)
        self.y_data = [0]*3648
        self.line = self.axis.plot([], [])[0]  # Axes.plot returns a list
        # Set the data to a mutable type so we only need to append to it then force the line to invalidate its cache
        self.line.set_data(np.linspace(1, 3648, 3648), self.y_data)
        self.ani = FuncAnimation(self.figure, self.update_plot, interval=interval)

    def update_plot(self, _):
        self.line.set_ydata(self.data_source)
        # (realistically the data source wouldn't be restricted to be a generator)
        # Because the Line2D object stores a reference to the two lists, we need only update the lists and signal
        # that the line needs to be updated.
        self.line.recache_always()
        self._refit_artists()
        # return self.line,

    def _refit_artists(self):
        self.axis.set_ylim(min(self.data_source), max(self.data_source))
        self.axis.autoscale_view()


root = tk.Tk()
data = data_gen()
plot = Plot(root, data)
plot.pack(fill=tk.BOTH, expand=True)
root.mainloop()
