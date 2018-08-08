import collections
import ctypes
import fcntl
import os
import platform
import time

# Pythonification of linux/ioctl.h
IOC_NONE = 0
IOC_WRITE = 1
IOC_READ = 2

IOC_NRBITS = 8
IOC_TYPEBITS = 8
IOC_SIZEBITS = 14
IOC_DIRBITS = 2

# Non-generic platform special cases
machine = platform.machine()

# Non-generic platform special cases
machine = platform.machine()
if machine in ['mips', 'sparc', 'powerpc', 'ppc64']:
    IOC_SIZEBITS = 13
    IOC_DIRBITS = 3
    IOC_NONE, IOC_WRITE, IOC_READ = 1, 2, 4
elif machine == 'parisc':
    IOC_WRITE, IOC_READ = 2, 1

IOC_NRSHIFT = 0
IOC_TYPESHIFT = IOC_NRSHIFT + IOC_NRBITS
IOC_SIZESHIFT = IOC_TYPESHIFT + IOC_TYPEBITS
IOC_DIRSHIFT = IOC_SIZESHIFT + IOC_SIZEBITS


def IOW(type_, nr, size):
    return IOC(IOC_WRITE, type_, nr, size)


def IOR(type_, nr, size):
    return IOC(IOC_READ, type_, nr, size)


def IOWR(type_, nr, size):
    return IOC(IOC_READ | IOC_WRITE, type_, nr, size)


def IOC(dir_, type_, nr, size):
    return (dir_ << IOC_DIRSHIFT) \
        | (ord(type_) << IOC_TYPESHIFT) \
        | (nr << IOC_NRSHIFT) \
        | (size << IOC_SIZESHIFT)


# Pythonification of linux/watchdog.h

WATCHDOG_IOCTL_BASE = 'W'


class watchdog_info(ctypes.Structure):
    _fields_ = [
        ('options', ctypes.c_uint32),           # Options the card/driver supports
        ('firmware_version', ctypes.c_uint32),  # Firmware version of the card
        ('identity', ctypes.c_uint8 * 32),      # Identity of the board
    ]


struct_watchdog_info_size = ctypes.sizeof(watchdog_info)
int_size = ctypes.sizeof(ctypes.c_int)

WDIOC_GETSUPPORT = IOR(WATCHDOG_IOCTL_BASE, 0, struct_watchdog_info_size)
WDIOC_GETSTATUS = IOR(WATCHDOG_IOCTL_BASE, 1, int_size)
WDIOC_GETBOOTSTATUS = IOR(WATCHDOG_IOCTL_BASE, 2, int_size)
WDIOC_GETTEMP = IOR(WATCHDOG_IOCTL_BASE, 3, int_size)
WDIOC_SETOPTIONS = IOR(WATCHDOG_IOCTL_BASE, 4, int_size)
WDIOC_KEEPALIVE = IOR(WATCHDOG_IOCTL_BASE, 5, int_size)
WDIOC_SETTIMEOUT = IOWR(WATCHDOG_IOCTL_BASE, 6, int_size)
WDIOC_GETTIMEOUT = IOR(WATCHDOG_IOCTL_BASE, 7, int_size)
WDIOC_SETPRETIMEOUT = IOWR(WATCHDOG_IOCTL_BASE, 8, int_size)
WDIOC_GETPRETIMEOUT = IOR(WATCHDOG_IOCTL_BASE, 9, int_size)
WDIOC_GETTIMELEFT = IOR(WATCHDOG_IOCTL_BASE, 10, int_size)

# Implementation

class LinuxWatchdogDevice():

    def __init__(self):
        self.device = '/dev/watchdog0'
        self._support_cache = None
        self._fd = None

    @classmethod
    def from_config(cls, config):
        device = config.get('device', cls.DEFAULT_DEVICE)
        return cls(device)

    @property
    def is_running(self):
        return self._fd is not None

    @property
    def is_healthy(self):
        return os.path.exists(self.device) and os.access(self.device, os.W_OK)

    def open(self):
        try:
            self._fd = os.open(self.device, os.O_WRONLY)
        except OSError as e:
            print ("Can't open watchdog device: {0}".format(e))

    def close(self):
        if self.is_running:
            try:
                os.write(self._fd, b'V')
                os.close(self._fd)
                self._fd = None
            except OSError as e:
                print ("Error while closing {0}: {1}".format(self.describe(), e))

    @property
    def can_be_disabled(self):
        return self.get_support().has_MAGICCLOSE

    def _ioctl(self, func, arg):
        "Checks is Watchdog is opened"
        if self._fd is None:
            print ("Watchdog device is closed")
        fcntl.ioctl(self._fd, func, arg, True)

    def get_support(self):
        if self._support_cache is None:
            info = watchdog_info()
            try:
                self._ioctl(WDIOC_GETSUPPORT, info)
            except Exception as e:
                print ("Could not get information about watchdog device: {}".format(e))
            self._support_cache = WatchdogInfo(info.options,
                                               info.firmware_version,
                                               bytearray(info.identity).decode(errors='ignore').rstrip('\x00'))
        return self._support_cache

    def describe(self):
        dev_str = " at {0}".format(self.device) if self.device != self.DEFAULT_DEVICE else ""
        ver_str = ""
        identity = "Linux watchdog device"
        if self._fd:
            try:
                _, version, identity = self.get_support()
                ver_str = " (firmware {0})".format(version) if version else ""
            except Exception as e:
                pass

        return identity + ver_str + dev_str

    def keepalive(self):
        try:
            os.write(self._fd, b'1')
        except Exception as e:
            print ("Could not send watchdog keepalive: {0}".format(e))

    def has_set_timeout(self):
        """Returns True if setting a timeout is supported."""
        return self.get_support().has_SETTIMEOUT

    def set_timeout(self, timeout):
        timeout = int(timeout)
        if not 0 < timeout < 0xFFFF:
            print ("Invalid timeout {0}. Supported values are between 1 and 65535".format(timeout))
        try:
            self._ioctl(WDIOC_SETTIMEOUT, ctypes.c_int(timeout))
        except Exception as e:
            print ("Could not set timeout on watchdog device: {}".format(e))

    def get_timeout(self):
        timeout = ctypes.c_int()
        try:
            self._ioctl(WDIOC_GETTIMEOUT, timeout)
        except Exception as e:
            print ("Could not get timeout on watchdog device: {}".format(e))
        return timeout.value


mywatchdog=LinuxWatchdogDevice()
mywatchdog.open()
mywatchdog.set_timeout(8)
timef = mywatchdog.get_timeout()
print ("Timeout value: " + str(timef))

for i in range (8):

	print ("Feeding Watchdog...")
	mywatchdog.keepalive()
	time.sleep(1)

for i in range(8):

	print "System should reboot in: " + str(8-i) + " seconds"
	time.sleep(1)

time.sleep(1)

mywatchdog.close()

                                        
