# pyWatchdog
This are a few lines of Python code to set hardware Watchdog in Linux.

If you want to set Watchdog in Linux please copy or download Watchdog+.py file.

This library does not require any special or additional libraries.

Then run it. It will establish connection with the selected Watchdog device. First the Python script will set the Watchdog timeout in 8 seconds ( for diferent timeouts please consult drivers options).Then it will feed Watchdog for 8 seconds. After that the system will reboot after timeout (8 seconds). To real implementation set mywatchdog.keepalive() in a while True loop. So that system will only reboot the it crashes or program breaks.

For more information please contact here or at andermutu@gmail.com
