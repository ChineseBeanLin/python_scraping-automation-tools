"""
ADBShell Wrapper Module

Note:
This module is based on an open-source ADB wrapper project (original source currently unavailable).
It has been customized and extended to support specific automation requirements for this portfolio.
Modifications include [change_default_tools or commands, input specific keyevent].
"""
from cgi import print_arguments
import os
from config import ADB_ROOT, ADB_HOST, SCREEN_SHOOT_SAVE_PATH, ShellColor
from PIL import Image
from time import sleep
import time
from random import random
import re


class ADBShell(object):
    def __init__(self):
        self.resolution = [1920, 1080]
        self.SCREEN_SHOOT_SAVE_PATH = SCREEN_SHOOT_SAVE_PATH
        os.chdir(ADB_ROOT)
        self.ADB_ROOT = ADB_ROOT
        self.ADB_HOST = ADB_HOST
        self.__command = ".\\ADB\\win32\\adb.exe {tools} {command}"
        self.__buffer = ""
        self.shell_color = ShellColor()
        self.__adb_tools = ""
        self.__adb_command = ""
        if self.ADB_ROOT != "" :
            self.__adb_connect()
        self.__choose_devices()
        

    def __adb_connect(self):
        self.__adb_tools = "connect"
        self.__adb_command = self.ADB_HOST
        self.run_cmd(DEBUG_LEVEL=1)
        if "device" in self.__buffer or "already connected to {}".format(self.ADB_HOST) in self.__buffer or "connected to {}".format(self.ADB_HOST) in self.__buffer:
            self.shell_color.warning_text("[+] Connect to DEVICE {}  Success".format(self.ADB_HOST))
        else:
            self.shell_color.failure_text("[-] Connect to DEVICE {}  Failed".format(self.ADB_HOST))


    def __choose_devices(self):
        self.__adb_tools = "devices"
        self.__adb_command = ""
        self.run_cmd(DEBUG_LEVEL=1)
        print(self.__buffer)
        devices = []
        orig_msg = self.__buffer.split("\n")
        for device in orig_msg:
            if ("device" in device) & (not "List" in device):
                devices.append(device)
        if len(devices) > 1 :
            print("the number of devices more than one, please enter number to choose the follow devices:")
            for i in range(0, len(devices)) :
                print(str(i) + " " + devices[i])
            device_no = int(input())
        else :
            device_no = 0
        device_name = devices[device_no].split("\t")[0]
        self.__command = ".\\ADB\\win32\\adb.exe -s " + device_name + " {tools} {command}"



    def run_cmd(self, DEBUG_LEVEL=2):
        """
        :param DEBUG_LEVEL:
            0 : cannot get any info
            1 : use get_buffer() to get info
            2 : print command and can use get_buffer() to get info
            3 : print command and print the return content
        :return:
        """
        if DEBUG_LEVEL == 3:
            print(self.shell_color.H_OK_BLUE +
                  self.__command.format(
                      tools=self.__adb_tools,
                      command=self.__adb_command) + self.shell_color.E_END
                  )

            self.__buffer = os.popen(self.__command.format(
                tools=self.__adb_tools,
                command=self.__adb_command
            )).read()
            self.get_buffer()
        elif DEBUG_LEVEL == 2:
            print(self.shell_color.H_OK_BLUE +
                  self.__command.format(
                      tools=self.__adb_tools,
                      command=self.__adb_command) + self.shell_color.E_END
                  )
            self.__buffer = os.popen(self.__command.format(
                tools=self.__adb_tools,
                command=self.__adb_command
            )).read()
        elif DEBUG_LEVEL == 1:
            self.__buffer = os.popen(self.__command.format(
                tools=self.__adb_tools,
                command=self.__adb_command
            )).read()
        else:
            os.system(self.__command.format(
                tools=self.__adb_tools,
                command=self.__adb_command
            ))

    def get_buffer(self, n=1024, BUFFER_OUT_PUT_LEVEL=1):
        """
        :param n: buffer size default 1024 chars
        :param BUFFER_OUT_PUT_LEVEL:
            1 INFO - color blue
            0 HELPER - color green
            -1 WEARING - color red
        :return:
        """
        if BUFFER_OUT_PUT_LEVEL == 1:
            print(self.shell_color.H_OK_BLUE + "[+] DEBUG INFO " + self.shell_color.E_END + "\n" +
                  self.__buffer[0:n])
        elif BUFFER_OUT_PUT_LEVEL == -1:
            print(self.shell_color.H_FAIL + "[+] DEBUG WARNING " + self.shell_color.E_END + "\n" +
                  self.__buffer[0:n])
        elif BUFFER_OUT_PUT_LEVEL == 0:
            print(self.shell_color.H_OK_GREEN + "[+] DEBUG HELPER " + self.shell_color.E_END + "\n" +
                  self.__buffer[0:n])

    @staticmethod
    def get_sub_screen(src_name, screen_range, save_name=""):
        if save_name == "":
            save_name = src_name
        i = Image.open(SCREEN_SHOOT_SAVE_PATH + src_name)
        i.crop(
            (
                screen_range[0][0],
                screen_range[0][1],
                screen_range[0][0] + screen_range[1][0],
                screen_range[0][1] + screen_range[1][1]
            )
        ).save(SCREEN_SHOOT_SAVE_PATH + save_name)

    def get_screen_shot(self, file_name="screenshot.png", screen_range=None):
        if screen_range is None:
            screen_range = []
        self.__adb_tools = "shell"
        self.__adb_command = "/system/bin/screencap -p /sdcard/screenshot.png"
        self.run_cmd(1)
        self.__adb_tools = "pull"
        self.__adb_command = "/sdcard/screenshot.png {}".format(self.SCREEN_SHOOT_SAVE_PATH + file_name)
        self.run_cmd(1)
        self.__adb_tools = "shell"
        self.__adb_command = "rm /sdcard/screenshot.png"
        self.run_cmd(1)
        if screen_range.__len__() == 2:
            self.get_sub_screen(file_name, screen_range)

    def get_mouse_swipe(self, start_point, end_point, FLAG=None):
        # XY = list(XY[0], XY[1])
        # mXmY = list(mXmY[0], mXmY[1])
        # if FLAG is not None:
        #     FLAG_XY, FLAG_mXmY = FLAG
        #     XY[0] = XY[0] + randint(-FLAG_XY[0], FLAG_XY[0])
        #     XY[1] = XY[0] + randint(-FLAG_XY[1], FLAG_XY[1])
        #     mXmY[0] = mXmY[0] + randint(-FLAG_mXmY[0], FLAG_mXmY[0])
        #     mXmY[1] = mXmY[1] + randint(-FLAG_mXmY[1], FLAG_mXmY[1])
        self.__adb_tools = "shell"
        self.__adb_command = "input swipe {X1} {Y1} {X2} {Y2}".format(
            X1=start_point[0], Y1=start_point[1], X2=end_point[0], Y2=end_point[1]
        )
        self.run_cmd(DEBUG_LEVEL=0)

    def get_mouse_click(self, XY=None, FLAG=None):
        sleep(1)
        if XY is None:
            XY = [0, 0]
        # else:
        #     XY = [XY[0], XY[1]]
        # if FLAG is None:
        #     FLAG = FLAGS_CLICK_BIAS_TINY
        # print(FLAG)
        # XY[0] = XY[0] + randint(-FLAG[0], FLAG[0])
        # XY[1] = XY[0] + randint(-FLAG[1], FLAG[1])
        self.__adb_tools = "shell"
        self.__adb_command = "input tap {} {}".format(XY[0], XY[1])
        self.run_cmd(DEBUG_LEVEL=0)

    def get_mouse_click_random(self, box=None, FLAG=None):
        if box is None:
            box = [[0, 0], [0, 0]]
        self.__adb_tools = "shell"
        self.__adb_command = "input tap {} {}".format(box[0][0]+int(box[1][0]*random()), box[0][1]+int(box[1][1]*random()))
        self.run_cmd(DEBUG_LEVEL=0)

    def mv_file(self, file_name, file_path="/sdcard/", RM=False):
        self.__adb_tools = "pull"
        self.__adb_command = "{} {}".format(
            file_path + file_name,
            SCREEN_SHOOT_SAVE_PATH + file_name
        )
        self.run_cmd(DEBUG_LEVEL=0)
        if RM:
            self.__adb_tools = "shell"
            self.__adb_command = "rm {}".format(file_path + file_name)

    @staticmethod
    def img_difference(img1, img2):
        img1 = Image.open(img1).convert('1')
        img2 = Image.open(img2).convert('1')
        hist1 = list(img1.getdata())
        hist2 = list(img2.getdata())
        sum1 = 0
        for i in range(len(hist1)):
            if (hist1[i] == hist2[i]):
                sum1 += 1
            else:
                sum1 += 1 - float(abs(hist1[i] - hist2[i])) / max(hist1[i], hist2[i])
        return sum1 / len(hist1)

    def ch_tools(self, tools):
        self.__adb_tools = tools

    def ch_abd_command(self, command):
        self.__adb_command = command


    @staticmethod
    def wait(min_time, prefix_time):
        wait_time = min_time + prefix_time * random()
        time.sleep(wait_time)
        
    
    def start_app(self, packet_name):
        self.__adb_tools = "shell"
        self.__adb_command = "am start -n {}".format(packet_name)
        self.run_cmd(DEBUG_LEVEL=0)
        
        
    def stop_app(self, packet_name):
        self.__adb_tools = "shell"
        self.__adb_command = "am force-stop {}".format(packet_name)
        self.run_cmd(DEBUG_LEVEL=0)   


    def click_back_keyevent(self):
        self.__adb_tools = "shell"
        self.__adb_command = "input keyevent 4"
        self.run_cmd(0)


if __name__ == '__main__':
    a = ADBShell()
