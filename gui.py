# 图形界面及其响应函数类
import tkinter
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import animation
import os
import numpy as np
import serial
import serial.tools.list_ports
import time
import threading
import platform
import communication as commu
from sklearn.linear_model import LinearRegression
from settings import Settings


class MainApp:
    def __init__(self, height=800, width=1200):
        # 初始化多线程
        self.n_proc = 1
        t1 = threading.Thread(target=self.data_generator, daemon=True)
        t3 = threading.Thread(target=self.update)
        # 识别操作系统
        self.os = platform.system()
        # 串口数据初始化
        self.bps = 9600
        self.bps_list = [50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800,
                         2400, 4800, 9600, 19200, 38400, 57600, 115200]
        self.timex = 10
        # 初始化serial串口通讯实例，未连接设备为None
        self.serial = None

        # 初始化文件工作目录
        self.working_dir = ''

        # 初始化选择设备
        self.device_choice = None
        self.lang_choice = None
        self.is_connect = False
        self.is_start = False
        self.is_pause = False
        self.is_stop = True

        # 初始化背景采集
        self.is_capture = False

        # 初始化背景扣除
        self.is_sub_bg = False

        # 初始化采集方式
        self.is_read_once = False

        # 初始化数据变量和背景
        self.background = [0]*3648
        self.y = [0]*3648
        self.exposure = 1
        self.y_max = 0
        self.y_min = 0

        # 窗口初始化
        self.width = width
        self.height = height
        self.win = tkinter.Tk()
        self.win.title("Raman Spectroscopy Reader - v.1.1.5 by LeoAokma")
        self.win.geometry("{}x{}".format(self.width, self.height))

        # 定义顶层工具栏
        self.top_frame = tkinter.Frame(height=10)
        self.top_frame.pack(side='top', expand=False, anchor='w')

        # 定义程序左右的独立排版功能区
        self.left_frame = tkinter.Frame(height=self.height, width=0.2*self.width)
        self.right_frame = tkinter.Frame(height=self.height, width=0.8*self.width)

        self.left_frame.pack(side='left', expand=1)
        self.right_frame.pack(side='right', expand=1)

        # 创建菜单栏功能
        self.font = ("Arial", 10)
        self.menuBar = tkinter.Menu(self.win)
        self.win.config(menu=self.menuBar)
        self.fileMenu = tkinter.Menu(self.menuBar, tearoff=0, font=self.font, bg="white", fg="black")
        self.controlMenu = tkinter.Menu(self.menuBar, tearoff=0, font=self.font, bg="white", fg="black")
        self.setMenu = tkinter.Menu(self.menuBar, tearoff=0, font=self.font, bg="white", fg="black")
        self.helpMenu = tkinter.Menu(self.menuBar, tearoff=0, font=self.font, bg="white", fg="black")

        self.menuBar.add_cascade(label="File", menu=self.fileMenu)
        self.fileMenu.add_command(label="Open file", command=self.on_open)
        self.fileMenu.add_command(label="Save as...", command=self.on_save)
        self.fileMenu.add_separator()
        self.fileMenu.add_command(label="Exit", command=self.quit)

        self.menuBar.add_cascade(label='Control', menu=self.controlMenu)
        self.controlMenu.add_command(label="Connect", command=self.on_connect)
        self.controlMenu.add_command(label="Disconnect")
        self.controlMenu.add_separator()
        self.controlMenu.add_command(label="Start Capture")
        self.controlMenu.add_command(label="Pause Capture")

        self.menuBar.add_cascade(label='Settings', menu=self.setMenu)
        self.setMenu.add_command(label='Language...', command=self.on_language)

        self.menuBar.add_cascade(label="Help", menu=self.helpMenu)
        self.helpMenu.add_command(label="User Guide")
        self.helpMenu.add_command(label="About License", command=self.on_license)
        self.helpMenu.add_command(label='Report Bug', command=self.on_report)

        # 顶部工具栏

        self.startButton = tkinter.Button(self.top_frame, text='Start', command=self.on_start)
        self.pauseButton = tkinter.Button(self.top_frame, text='Pause', command=self.on_pause, state='disabled')
        self.stopButton = tkinter.Button(self.top_frame, text='Stop', command=self.on_stop, state='disabled')
        self.bgButton = tkinter.Button(self.top_frame, text='Subtract Background', command=self.sub_bg, state='disabled')
        self.startButton.grid(row=0, column=0, padx=20)
        self.pauseButton.grid(row=0, column=1, padx=20)
        self.stopButton.grid(row=0, column=2, padx=20)
        self.bgButton.grid(row=0, column=3, padx=20)

        # 左侧控制栏

        # 曝光时间
        tkinter.Label(self.left_frame, text='Exposure\n Time', anchor='w').grid(row=1, column=0)
        self.inputExposingTime = tkinter.Entry(self.left_frame, width=10)
        self.inputExposingTime.grid(row=1, column=1)
        self.inputExposingTime.insert(0, '20')
        tkinter.Button(self.left_frame, text='OK', command=self.on_expose_time).grid(row=1, column=2, columnspan=2)

        # 暗背景
        self.capture_text = tkinter.StringVar()
        self.capture_text.set('Capture')
        self.capture = False
        tkinter.Label(self.left_frame, text='Background\n Capture', anchor='w').grid(row=2, column=0)
        self.captureButton = tkinter.Button(self.left_frame,
                                            textvariable=self.capture_text,
                                            command=self.on_capture_bg
                                            )
        self.captureButton.grid(row=2, column=1, columnspan=2)

        # 坐标轴归一化
        self.slope = 0
        self.intercept = 0
        self.is_standardize = False
        tkinter.Label(self.left_frame, text='Wavelength\nStandardization').grid(row=3, column=0)
        tkinter.Label(self.left_frame, text='Intercept(nm)').grid(row=4, column=0)
        tkinter.Label(self.left_frame, text='Slope(nm/pixel)').grid(row=5, column=0)
        self.slope_box = tkinter.Entry(self.left_frame, width=10)
        self.intercept_box = tkinter.Entry(self.left_frame, width=10)
        self.slope_box.insert(0, 495.60)
        self.intercept_box.insert(0, 0.04776)
        self.slope_box.grid(row=4, column=1)
        self.intercept_box.grid(row=5, column=1)
        self.stand_but_text = tkinter.StringVar()
        self.stand_but_text.set('Standardize')
        self.standardize_but = tkinter.Button(self.left_frame,
                                              textvariable=self.stand_but_text,
                                              command=self.on_standardize)
        self.standardize_but.grid(row=6, column=0)

        # 坐标轴归一化的标准谱校准

        self.calibrate_but = tkinter.Button(self.left_frame,
                                            text='Calibrate',
                                            command=self.on_calibrate)
        self.calibrate_but.grid(row=6, column=1)

        # 工作目录(wd)和相关操作
        self.working_dir_text = tkinter.StringVar()
        self.wd_label = tkinter.Label(self.left_frame, text='Working\nDirectory', anchor='w')
        self.wd_label.grid(row=7, column=0)
        self.wd_dir_label = tkinter.Label(self.left_frame, textvariable=self.working_dir_text)
        self.wd_dir_label.grid(row=7, column=1)

        self.wd_browse_button = tkinter.Button(self.left_frame,
                                               text='Browse...',
                                               command=self.on_wd_browse)
        self.wd_browse_button.grid(row=8, column=0)

        self.wd_quick_save_button = tkinter.Button(self.left_frame,
                                             text='Quick Save',
                                             command=self.on_quick_save)
        self.wd_quick_save_button.grid(row=8, column=1)

        self.wd_screenshot_but = tkinter.Button(self.left_frame,
                                                text='Screenshot',
                                                command=self.on_screenshot)
        self.wd_save_but = tkinter.Button(self.left_frame,
                                          text='Save Data',
                                          command=self.on_save_data)
        self.wd_screenshot_but.grid(row=9, column=0)
        self.wd_save_but.grid(row=9, column=1)

        # 右侧作图窗口
        self.pic = plt.figure(figsize=(0.8*self.width/300, self.height/300), dpi=300)

        # 设置字体
        matplotlib.rcParams['font.sans-serif'] = ['SimHei']
        # 初始化动画对象
        self.animate = None

        self.fig = plt.figure(figsize=(self.width*0.8/300, self.height/300), dpi=300)
        self.subplot = self.fig.add_subplot(111)
        plt.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)
        self.line_plot, = self.subplot.plot([], [], lw=0.2)
        self.subplot.set_ylim(0, 10000)
        self.subplot.set_xlim([0, 3648])
        plt.tick_params(labelsize=5)
        plt.xticks(list(range(0, 3649, 304)))
        plt.grid(axis='both', linewidth=0.3)

        self.fig_canvas = FigureCanvasTkAgg(self.fig,
                                            master=self.right_frame
                                            )
        self.fig_canvas.draw()
        self.fig_canvas.get_tk_widget().pack(side=tkinter.RIGHT, fill=tkinter.BOTH, expand=1)
        self.fig_canvas._tkcanvas.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)
        # 窗口自适应大小

        # self.win.bind("<Configure>", self.set_win_size)
        # 进入消息循环
        time.sleep(0.001)
        self.win.mainloop()

    def data_generator(self):
        """
        用于持续与串口进行通讯，读取串口输出数据的函数，将在在独立的线程中循环进行
        :return:
        """
        while True:
            read = self.serial.read(3694 * 2)
            self.y = commu.byte_process(read)
            if self.is_sub_bg:
                self.data = np.array(commu.byte_process(read)) - np.array(self.background)
            else:
                self.data = np.array(commu.byte_process(read))
            yield list(self.data)

    def msg_valid(self, msg):
        """
        验证用户输入的值是否可以转换成数字（浮点）
        :param msg:
        :return:
        """
        try:
            new = float(msg)
            return True
        except ValueError:
            return False

    def on_calibrate(self):

        ethanol = {'shift': [2973, 2927, 2876, 1455, 1097, 1053, 864],
                   'wavelength': [631.95, 630.12, 628.10, 576.63, 564.97, 563.57, 557.63]}

        acetone = {'shift': [2921, 1708, 787],
                   'wavelength': [629.88, 585.17, 555.25]}

        def click_calibrate(*args):
            ethanol_value = []
            acetone_value = []
            for _ in range(7):
                eval('ethanol_value.append(int(ethanol{}.get()))'.format(_))
            for _ in range(3):
                eval('acetone_value.append(int(ethanol{}.get()))'.format(_))
            line = LinearRegression(fit_intercept=True)

            y_data = np.append(ethanol['wavelength'], acetone['wavelength'])
            x_data = np.append(ethanol_value, acetone_value)
            line.fit(x_data.reshape(-1, 1), y_data)

            messagebox.showinfo(title='Linear Fit Success!',
                                message='Slope={:.6f}\nIntercept={:.2f}'.format(line.coef_[0], line.intercept_))
            self.slope_box.delete(0, "end")
            self.intercept_box.delete(0, "end")
            self.slope_box.insert(0, "{:.5f}".format(line.intercept_))
            self.intercept_box.insert(0, "{:.5f}".format(line.coef_[0]))
            self.calibrate_win.destroy()

        self.calibrate_win = tkinter.Toplevel()
        self.calibrate_win.title("Calibrate to Spectra")
        self.calibrate_win.geometry("500x450")
        self.calibrate_win.resizable(0, 0)
        self.calibrate_frame = tkinter.Frame(master=self.calibrate_win, height=300, width=400)
        self.calibrate_frame.pack(side=tkinter.TOP)

        tkinter.Label(master=self.calibrate_frame, text='Ethanol').grid(row=1, column=1)

        tkinter.Label(master=self.calibrate_frame,
                      text='Shift(cm^(-1))').grid(row=2, column=0)
        tkinter.Label(master=self.calibrate_frame,
                      text='Wavelength(nm)').grid(row=2, column=1)

        create_var_1 = globals()

        for _ in range(len(ethanol['shift'])):
            tkinter.Label(master=self.calibrate_frame,
                          text=ethanol['shift'][_]).grid(row=_ + 3, column=0)
            tkinter.Label(master=self.calibrate_frame,
                          text=ethanol['wavelength'][_]).grid(row=_ + 3, column=1)

            create_var_1['ethanol' + str(_)] = tkinter.Entry(self.calibrate_frame, width=10)
            eval('ethanol{}.grid(row={}, column=2)'.format(_, _+3))

        tkinter.Label(master=self.calibrate_frame, text='Acetone').grid(row=10, column=1)

        tkinter.Label(master=self.calibrate_frame,
                      text='Shift(cm^(-1))').grid(row=11, column=0)
        tkinter.Label(master=self.calibrate_frame,
                      text='Wavelength(nm)').grid(row=11, column=1)

        create_var_2 = globals()

        for _ in range(len(acetone['shift'])):
            tkinter.Label(master=self.calibrate_frame,
                          text=acetone['shift'][_]).grid(row=_ + 12, column=0)
            tkinter.Label(master=self.calibrate_frame,
                          text=acetone['wavelength'][_]).grid(row=_ + 12, column=1)

            create_var_2['acetone' + str(_)] = tkinter.Entry(self.calibrate_frame, width=10)
            eval('acetone{}.grid(row={}, column=2)'.format(_, _ + 12))

        tkinter.Button(self.calibrate_win,
                       text='Confirm',
                       command=click_calibrate
                       ).place(x=200, y=400, anchor='s')
        tkinter.Button(self.calibrate_win,
                       text='Cancel',
                       command=self.calibrate_win.destroy
                       ).place(x=300, y=400, anchor='s')
        self.calibrate_win.mainloop()

    def on_standardize(self):
        """
        横坐标归一化函数，仅改变bool变量，实际操作将在update函数中进行
        :return:
        """
        if not self.is_standardize:
            slope = self.slope_box.get()
            intercept = self.intercept_box.get()
            if self.msg_valid(slope) and self.msg_valid(intercept):
                self.slope = float(slope)
                self.intercept = float(intercept)
                self.stand_but_text.set('Standardized!')
                self.standardize_but.configure(fg='green')
                self.is_standardize = True
            else:
                messagebox.showerror(title='Error', message='Invalid parameters given!')
        else:
            self.stand_but_text.set('Standardize')
            self.standardize_but.configure(fg='black')
            self.is_standardize = False

    def on_start(self):
        tt = threading.Thread(target=self.on_start_, daemon=True)
        self.on_start_()

    def update(self, data):
        """
        用于更新光谱图的函数，将在独立的线程中循环运行
        :return:
        """
        if max(data) <= 0.9*self.y_max:
            self.y_max = max(data)
        elif max(data) > self.y_max:
            self.y_max = max(data)
        if min(data) >= 1.1*self.y_min:
            self.y_min = min(data)
        elif min(data) < self.y_min:
            self.y_min = min(data)
        if self.is_standardize:
            self.line_plot.set_data(np.linspace(self.slope + self.intercept, self.slope + 3648 * self.intercept, 3648),
                                    data)
            self.subplot.set_xticks(np.linspace(self.slope + self.intercept, self.slope + 3648 * self.intercept, 10))
            self.subplot.set_xlim(self.slope + self.intercept, self.slope + 3648 * self.intercept)
        else:
            self.line_plot.set_data(np.linspace(1, 3648, 3648), data)
            self.subplot.set_xticks(np.linspace(1, 3648, 10))
            self.subplot.set_xlim(0, 3648)
        self.subplot.set_ylim(self.y_min, self.y_max)
        # self.subplot.set_yticks()
        # plt.yticks(np.linspace(min(data), max(data), 10))
        self.line_plot.recache_always()
        self.subplot.autoscale_view()
        return self.line_plot,

    def on_wd_browse(self):
        """
        开启新线程选择文件目录
        :return:
        """
        t = threading.Thread(target=self.on_wd_browse_, daemon=True)
        t.start()

    def on_wd_browse_(self):
        """
        选择快速保存工作目录的响应函数
        :return:
        """
        self.working_dir = filedialog.askdirectory()
        self.working_dir_text.set(self.working_dir)

    def on_quick_save(self):
        """
        同时保存光谱数据和光谱图的响应函数
        :return:
        """
        ts = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        self.on_save_data(time_=ts)
        self.on_screenshot(time_=ts)

    def on_save_data(self, time_=None):
        save_data = self.y
        save_bg = self.background
        if time_ == None:
            time_stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        else:
            time_stamp = time_
        with open(os.path.join(self.working_dir, '{}_exp_{}.txt'.format(time_stamp, self.exposure)), 'w') as quick_save:
            quick_save.writelines('pixel\tdata\tbackground\n')
            for _ in range(3648):
                quick_save.writelines('{}\t{}\t{}\n'.format(_ + 1, save_data[_], save_bg[_]))

    def on_screenshot(self, time_=None):
        if time_ == None:
            time_stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        else:
            time_stamp = time_
        self.fig.savefig(os.path.join(self.working_dir,
                                      '{}_exp_{}.png'.format(time_stamp,
                                                             self.exposure)))

    def on_start_(self):
        """
        点击开始按钮的动作函数，向串口发送数据
        :return:
        """
        if self.is_pause:
            self.is_pause = False
        if self.is_stop:
            self.is_stop = False
            self.serial = serial.Serial(self.device_choice, self.bps, timeout=self.timex, parity='N', bytesize=8)
        print(self.serial)
        if self.serial != None:
            self.serial.write("#IT:001ms%".encode('utf-8'))
            self.serial.write('#Start%'.encode("utf-8"))
            self.is_start = True
            self.stopButton.configure(state='active')
            self.pauseButton.configure(state='active')
            self.bgButton.configure(state='active')
            self.startButton.configure(state='disabled')
            self.animate = animation.FuncAnimation(self.fig,
                                                   self.update,
                                                   self.data_generator,
                                                   interval=10,
                                                   # blit=True
                                                   )
            # self.fig.draw()
            self.fig_canvas.draw()
        else:
            messagebox.showerror(title='Error', message='No device connected!')

    def on_pause(self):
        """
        点击暂停按钮的动作函数，将向串口发送停止指令
        :return:
        """
        if self.serial != None:
            self.serial.write('#Stop%'.encode("utf-8"))
            self.pauseButton.configure(state='disabled')
            self.startButton.configure(state='active')
            self.is_pause = True

    def on_stop(self):
        """
        点击停止按钮的动作函数，向串口发送停止指令，并断开串口连接
        :return:
        """
        if self.serial != None:
            self.serial.write('#Stop%'.encode("utf-8"))
            self.serial.close()
            self.pauseButton.configure(state='disabled')
            self.startButton.configure(state='active')
            self.stopButton.configure(state='disabled')
            self.is_stop = True

    def sub_bg(self):
        """
        扣除暗背景的函数，仅改变bool变量，将在update中进行实际的减法操作
        :return:
        """
        if not self.is_sub_bg:
            self.bgButton.configure(fg='green')
            self.is_sub_bg = True
        else:
            self.bgButton.configure(fg='black')
            self.is_sub_bg = False

    def set_win_size(self, *args):
        self.width = self.win.winfo_width()
        self.height = self.win.winfo_height()
        self.win.update()

    def on_open(self):
        """
        菜单栏中打开文件的命令，暂时未使用
        :return:
        """
        file = filedialog.askopenfilenames(initialdir=os.path.dirname(__file__))
        if len(file) != 0:
            if str(file).split('.')[-1] != "txt":
                messagebox.showerror(title='Error', message="Unsupported format!")
            else:
                with open(file, 'r+') as f:
                    pass

    def on_save(self):
        """
        菜单栏中保存文件的命令，暂时未使用
        :return:
        """
        save_data = self.y
        save_bg = self.background
        savefile = filedialog.asksaveasfilename(initialdir=os.path.dirname(__file__))
        if len(savefile) != 0:
            with open(savefile, 'w') as f:
                f.writelines('pixel\tdata\tbackground\n')
                for _ in range(3648):
                    f.writelines('{}\t{}\t{}\n'.format(_ + 1, save_data[_], save_bg[_]))

    def on_connect(self):
        """
        用于选择连接ccd设备的交互程序，将于选中的设备进行串口通讯握手
        :return:
        """

        def click_connect(*args):
            if len(self.device_list) == 0:
                messagebox.showerror(title='Error', message='No device detected!')
            else:
                self.device_choice = self.device_box.get()
                self.bps = int(bps_box.get())
                if ' - ' in self.device_choice:
                    self.device_choice = self.device_choice.split('-')[0].strip()
                self.serial = serial.Serial(self.device_choice, self.bps, timeout=self.timex)
                self.is_connect = True
                self.connect_win.destroy()

        self.connect_win = tkinter.Toplevel()
        self.connect_win.title("Connect to devices")
        self.connect_win.geometry("500x150")
        self.connect_win.resizable(0, 0)
        self.connect_frame = tkinter.Frame(master=self.connect_win, height=300, width=400)
        self.connect_frame.pack(side=tkinter.TOP)

        tkinter.Label(master=self.connect_frame, text='Device List').grid(row=1, column=0)
        self.device_list = commu.get_device_list()
        self.device_box = ttk.Combobox(self.connect_frame,
                                       textvariable=self.device_choice
                                       )
        self.device_box.bind("<<ComboboxSelected>>", click_connect)
        self.device_box['values'] = self.device_list
        self.device_box.grid(row=1, column=1)
        for _ in self.device_list:
            self.device_box.insert(tkinter.END, _)

        tkinter.Label(master=self.connect_frame, text='Bitrate(bit/sec)').grid(row=2, column=0)
        bps_box = ttk.Combobox(self.connect_frame,
                               textvariable=self.bps
                               )
        bps_box['values'] = self.bps_list
        bps_box.grid(row=2, column=1)
        bps_box.bind("<<ComboboxSelected>>", click_connect)

        tkinter.Button(self.connect_win,
                       text='Connect',
                       command=click_connect
                       ).place(x=200, y=100, anchor='s')
        tkinter.Button(self.connect_win,
                       text='Cancel',
                       command=self.connect_win.destroy
                       ).place(x=300, y=100, anchor='s')
        self.connect_win.mainloop()

    def on_expose_time(self):
        """
        向串口发送指定的曝光时间命令，并修改应用的曝光时间变量
        :return:
        """
        self.exposure = self.inputExposingTime.get()
        if int(self.exposure) <= 999:
            self.serial.write("#IT:{}ms%".format(self.exposure.zfill(3)).encode('utf-8'))
        else:
            time_sec = round(int(self.exposure) / 1000)
            self.serial.write("#IT:{}ss%".format(str(time_sec).zfill(3)).encode('utf-8'))

    def on_capture_bg(self):
        self.background = self.y
        self.capture = True
        if self.capture:
            self.capture_text.set('Captured')
            self.captureButton.configure(fg='green')

    def on_license(self):
        messagebox.showinfo("About License", "该程序由北京大学化学与分子工程学院2018级本科生何嘉炜编写，用于在中物化实验中采集拉曼"
                                             "光谱数据，请勿商用，如有任何使用问题请联系1800011753@pku.edu.cn。项目源代码将在"
                                             "实验课程结束后公布于LeoAokma的github仓库中，欢迎学习交流。")

    def on_report(self):
        messagebox.showinfo("Report Bug", "请联系1800011753@pku.edu.cn")

    def on_language(self):
        """
        更换程序语言（暂时仅支持中英文），重启应用生效
        :return:
        """
        def click_ok(*args):
            self.lang_choice = self.lang_box.get()
            self.lang_win.destroy()

        self.lang_win = tkinter.Toplevel()
        self.lang_win.title("Connect to devices")
        self.lang_win.geometry("500x150")
        self.lang_win.resizable(0, 0)
        self.lang_frame = tkinter.Frame(master=self.lang_win, height=300, width=400)
        self.lang_frame.pack(side=tkinter.TOP)

        tkinter.Label(master=self.lang_frame, text='Choose a language').grid(row=1, column=0)
        self.lang_list = ['English', '简体中文']
        self.lang_box = ttk.Combobox(self.lang_frame,
                                       textvariable=self.lang_choice
                                       )
        self.lang_box.bind("<<ComboboxSelected>>", click_ok)
        self.lang_box['values'] = self.lang_list
        self.lang_box.grid(row=1, column=1)
        for _ in self.lang_list:
            self.lang_box.insert(tkinter.END, _)

        tkinter.Button(self.lang_win,
                       text='Set',
                       command=click_ok
                       ).place(x=200, y=100, anchor='s')
        tkinter.Button(self.lang_win,
                       text='Cancel',
                       command=self.lang_win.destroy
                       ).place(x=300, y=100, anchor='s')
        self.lang_win.mainloop()

    def quit(self):
        self.win.quit()
        self.win.destroy()
        exit()
