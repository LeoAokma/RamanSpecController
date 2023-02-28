import serial
import serial.tools.list_ports
import struct
import platform


def get_device_list():
    return list(serial.tools.list_ports.comports())


def byte_process(read_data):
    spectra = []
    data = read_data[64:-28]
    for _ in range(0, 3648):
        fig = int.from_bytes(data[2*_:2*_+2], byteorder='little')
        spectra.append(fig)
    return spectra


def continuous_reading(port, bps=115200):
    try:
        # 超时设置 None：永远等待操作，0为立即返回请求结果，其他值为等待超时时间(单位为秒）
        timex = None
        ser = serial.Serial(port, bps, timeout=timex)
        # 十六进制的发送
        result = ser.write('#Start%'.encode("utf-8"))
        read = ser.read(3694*2)
        data = byte_process(read)
        # 十六进制的读取
        ser.close()
        return data
    except Exception as e:
        print("---异常---：", e)


def stop_serial(port, bps=115200):
    try:
        # 超时设置 None：永远等待操作，0为立即返回请求结果，其他值为等待超时时间(单位为秒）
        timex = None
        ser = serial.Serial(port, bps, timeout=timex)

        # 十六进制的发送
        result = ser.write('#Stop%'.encode("utf-8"))
        return True
    except Exception as e:
        print("---异常---：", e)


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
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
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)
    line_plot, = ax.plot(np.linspace(1, 3648, 3648), y)
    ax.set_ylim(0, 10000)
    ax.set_xlim([0, 3648])
    plt.grid(axis='both')

    def data():
        while True:
            read = ser.read(3694 * 2)
            yield byte_process(read)


    def update(data):
        line_plot.set_ydata(data)
        ax.set_ylim(min(data), max(data))
        return line_plot,


    ani = animation.FuncAnimation(fig, update, data, interval=100)
    plt.show()


