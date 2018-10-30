import subprocess
import logging
import re
import cv2 as cv
import numpy as np
from random import randint
from typing import List, Tuple, Union

logging.basicConfig(level=logging.DEBUG)


class Device:
    """
    A class of the android device controller that provides interface such as screenshots and clicking.
    """

    def __init__(self, timeout: int = 15, adb_path: str = 'adb'):
        """

        :param timeout: the timeout of executing commands.
        :param adb_path: the path to the adb executable.
        """

        self.logger = logging.getLogger('device')

        self.adb_path = adb_path

        self.timeout = timeout

        self.size = (1280, 720)

    def run_cmd(self, cmd: List[str], raw: bool = False) -> Union[bytes, List[str]]:
        """
        Execute an adb command.
        Return the raw output if the `raw` parameter is set `True`.
        Else return the utf-8 encoded output, separated by line, as a list.

        :param cmd: the command to execute, separated as a string list.
        :param raw: whether to return the raw output
        :return: a list of the output, utf-8 decoded, separated by line, as a list.
        """
        cmd = [self.adb_path] + cmd
        self.logger.debug('Executing command: {}'.format(' '.join(cmd)))
        output = subprocess.check_output(cmd, timeout=self.timeout)
        if raw:
            return output
        else:
            return output.decode('utf-8').splitlines()

    def connect(self, addr: str = '127.0.0.1:62001', restart: bool = False) -> bool:
        """
        Connect to a device through adb.

        Attention: Only if connecting via tcp/ip this function needs to be called.
        Not needed if using USB or some emulator provided adb versions.

        :param addr: the ip address and port of the adb server.
        :param restart: if set True, run kill-server before connecting.
        :return: whether connection is successful.
        """
        if restart:
            self.run_cmd(['kill-server'])
        output = self.run_cmd(['connect', addr])
        for line in output:
            if line.startswith('connected'):
                self.logger.info('Connected to device at {}.'.format(addr))
                return True
        self.logger.error('Failed to connect to device at {}.'.format(addr))
        self.logger.error('Error message: {}'.format('\n'.join(output)))
        return False

    def connected(self) -> bool:
        """
        Check if a device is connected.
        """
        output = self.run_cmd(['devices'])
        devices = 0
        for line in output:
            if line.endswith('device'):
                devices += 1
        if devices == 0:
            self.logger.error('No device connected.')
            return False
        elif devices > 1:
            self.logger.error('More than one device connected.')
            return False
        else:
            self.logger.info('OK device connected.')
            return True

    def get_size(self) -> bool:
        """
        Get the resolution (screen size) of the device.

        :return: whether successful.
        """
        output = self.run_cmd(['shell', 'wm', 'size'])
        for line in output:
            if line.startswith('Physical size'):
                self.size = tuple(map(int, re.findall(r'\d+', line)))
                self.logger.info('Got screen size {:d} x {:d}'.format(self.size[0], self.size[1]))
                return True
        self.logger.error('Failed to get screen size')
        self.logger.error('Error message: {}'.format('\n'.join(output)))
        return False

    def tap(self, x: int, y: int) -> bool:
        """
        Input a tap event at `pos`.

        :param x: the x coord in pixels.
        :param y: the y coord in pixels.
        :return: whether the event is successful.
        """
        coords = '{:d} {:d}'.format(x, y)
        output = self.run_cmd(['shell', 'input tap {}'.format(coords)])
        for line in output:
            if line.startswith('error'):
                self.logger.error('Failed to tap at {}'.format(coords))
                self.logger.error('Error message: {}'.format('\n'.join(output)))
                return False
        self.logger.debug('Tapped at {}'.format(coords))
        return True

    def tap_rand(self, x: int, y: int, w: int, h: int) -> bool:
        """

        :param x: the top x coord in pixels.
        :param y: the left y coord in pixels.
        :param w: the width in pixels.
        :param h: the height in pixels.
        :return: whether the event is successful.
        """
        x = randint(x, x + w - 1)
        y = randint(y, y + h - 1)
        return self.tap(x, y)

    def swipe(self, pos0: Tuple[int, int], pos1: Tuple[int, int], duration: int = 500) -> bool:
        """
        Input a swipe event from `pos0` to `pos1`, taking `duration` milliseconds.

        :param pos0: the start coordinates in pixels.
        :param pos1: the end coordinates in pixels.
        :param duration: the time (in milliseconds) the swipe will take.
        :return: whether the event is successful.
        """
        coords0 = '{:d} {:d}'.format(pos0[0], pos0[1])
        coords1 = '{:d} {:d}'.format(pos1[0], pos1[1])
        output = self.run_cmd(['shell', 'input swipe {} {} {:d}'.format(coords0, coords1, duration)])
        for line in output:
            if line.startswith('error'):
                self.logger.error('Failed to swipe from {} to {} taking {:d}ms'.format(coords0, coords1, duration))
                self.logger.error('Error message: {}'.format('\n'.join(output)))
                return False
        self.logger.debug('Swiped from {} to {} taking {:d}ms'.format(coords0, coords1, duration))
        return True

    # methods of capturing the screen.
    FROM_SHELL = 0
    SDCARD_PULL = 1

    @staticmethod
    def png_sanitize(s: bytes) -> bytes:
        """
        Auto-detect and replace '\r\n' or '\r\r\n' by '\n' in the given byte string.

        :param s: the string to sanitize
        :return: the result string
        """
        logging.getLogger('device').debug('Sanitizing png bytes...')
        pos1 = s.find(b'\x1a')
        pos2 = s.find(b'\n', pos1)
        pattern = s[pos1 + 1:pos2 + 1]
        logging.getLogger('device').debug("Pattern detected: '{}'".format(pattern))
        return re.sub(pattern, b'\n', s)

    def capture(self, method=FROM_SHELL) -> Union[np.ndarray, None]:
        """
        Capture the screen.

        :return: a cv2 image as numpy ndarray
        """
        if method == self.FROM_SHELL:
            self.logger.debug('Capturing screen from shell...')
            img = self.run_cmd(['shell', 'screencap -p'], raw=True)
            img = self.png_sanitize(img)
            img = np.frombuffer(img, np.uint8)
            img = cv.imdecode(img, cv.IMREAD_COLOR)
            return img
        elif method == self.SDCARD_PULL:
            self.logger.debug('Capturing screen from sdcard pull...')
            self.run_cmd(['shell', 'screencap -p /sdcard/sc.png'])
            self.run_cmd(['pull', '/sdcard/sc.png', './sc.png'])
            img = cv.imread('./sc.png', cv.IMREAD_COLOR)
            return img
        else:
            self.logger.error('Unsupported screen capturing method.')
            return None
