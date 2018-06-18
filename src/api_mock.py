"""
Mock for api.py's wrapper around control and video dbus interfaces to allow for
easier development of the QT interface.

This mock is less "complete" than the C-based mock, as this mock only returns
values sensible enough to develop the UI with. Currently the C-based mock is
used for the camera API, and this mock is used for the control api. Note that
this mock is still available for external programs to use via the dbus
interface.

Usage:
import api_mock as api
print(api.control('get_video_settings'))

Remarks:
The service provider component can be extracted if interaction with the HTTP
api is desired. While there is a more complete C-based mock, in chronos-cli, it
is exceptionally hard to add new calls to.
"""

import sys
from debugger import dbg, brk; dbg, brk

from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusReply


# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	sys.exit(-1)


##############################################
#    Set up mock dbus interface provider.    #
##############################################

class ControlMock(QObject):
	def __init__(self):
		super(ControlMock, self).__init__()
		self._state = {
			"recordingGeometry": {
				"hres": 200,
				"vres": 300,
				"hoffset": 800,
				"voffset": 480,
			},
			"recordingExposure": 85000,
			"recordingPeriod": 40000,
			"analogGain": 2,
			
			
		}
		
	@pyqtSlot(result='QVariantMap')
	def get_camera_data(self):
		return {
			"model": "Mock Camera 1.4",
			"apiVersion": "1.0",
			"fpgaVersion": "3.14",
			"memoryGB": "16",
			"serial": "Captain Crunch",
		}	
		
	@pyqtSlot(result='QVariantMap')
	def get_video_settings(self):
		return {k: self._state[k] for k in ("recordingGeometry", "recordingExposure", "recordingPeriod", "analogGain")}
	
	@pyqtSlot('QVariantMap')
	def set_video_settings(self, data):
		for k in ("recordingGeometry", "recordingExposure", "recordingPeriod", "analogGain"):
			self._state[k] = data[k]
	
	@pyqtSlot(result='QVariantMap')
	def get_sensor_data(self):
		return {
			"name": "acme9001",
			"hMax": 1920,
			"vMax": 1080,
			"hMin": 256,
			"vMin": 64,
			"hIncrement": 2,
			"vIncrement": 32,
			"pixelRate": 1920 * 1080 * 1000,
			"pixelFormat": "BYR2",
			"framerateMax": 1000,
			"quantizeTiming": 250,
			"maxExposure": int(1e9),
			"minExposure": 1000,
			"maxShutterAngle": 330,
		}
	
	@pyqtSlot(result='QVariantMap')
	def get_timing_limits(self):
		return {
			"tMaxPeriod": sys.maxsize,
			"tMinPeriod": (self._state['recordingGeometry']['hres'] * self._state['recordingGeometry']['vres'] * int(1e9)) / self.get_sensor_data()['pixelRate'],
			"tMinExposure": int(1e3),
			"tMaxExposure": int(1e9),
			"tExposureDelay": 1000, 
			"tMaxShutterAngle": 330,
			"fQuantization": 1e9 / self.get_sensor_data()['quantizeTiming'],
		}





if not QDBusConnection.systemBus().registerService('com.krontech.chronos.control.mock'):
	sys.stderr.write(f"Could not register service: {QDBusConnection.systemBus().lastError().message() or '(no message)'}\n")
	sys.exit(2)

controlMock = ControlMock() #This absolutely, positively can't be inlined or it throws error "No such object path '/'".
QDBusConnection.systemBus().registerObject('/', controlMock, QDBusConnection.ExportAllSlots)




#######################
#    Use the mock.    #
#######################

cameraControlAPI = QDBusInterface(
	'com.krontech.chronos.control.mock', #Service
	'/', #Path
	'', #Interface
	QDBusConnection.systemBus() )
cameraVideoAPI = QDBusInterface(
	'com.krontech.chronos.video', #Service
	'/com/krontech/chronos/video', #Path
	'com.krontech.chronos.video', #Interface
	QDBusConnection.systemBus() )

cameraControlAPI.setTimeout(16) #Default is -1, which means 25000ms. 25 seconds is too long to go without some sort of feedback, and the only real long-running operation we have - saving - can take upwards of 5 minutes. Instead of setting the timeout to half an hour, we should probably use events which are emitted as the event progresses. One frame (at 60fps) should be plenty of time for the API to respond, and also quick enough that we'll notice any slowness. The mock replies to messages in under 1ms, so I'm not too worried here.
cameraVideoAPI.setTimeout(16)

if not cameraControlAPI.isValid():
	print("Error: Can not connect to Camera D-Bus API at %s. (%s: %s)" % (
		cameraControlAPI.service(), 
		cameraControlAPI.lastError().name(), 
		cameraControlAPI.lastError().message(),
	), file=sys.stderr)
	sys.exit(-2)
if not cameraVideoAPI.isValid():
	print("Error: Can not connect to Camera D-Bus API at %s. (%s: %s)" % (
		cameraVideoAPI.service(), 
		cameraVideoAPI.lastError().name(), 
		cameraVideoAPI.lastError().message(),
	), file=sys.stderr)
	sys.exit(-2)


class DBusException(Exception):
	"""Raised when something goes wrong with dbus. Message comes from dbus' msg.error().message()."""
	pass


def control(*args, **kwargs):
	"""
	Call the camera control DBus API. First arg is the function name.
	
	See http://doc.qt.io/qt-5/qdbusabstractinterface.html#call for details about calling.
	See https://github.com/krontech/chronos-cli/tree/master/src/api for implementation details about the API being called.
	See README.md at https://github.com/krontech/chronos-cli/tree/master/src/daemon for API documentation.
	"""
	
	msg = QDBusReply(cameraControlAPI.call(*args, **kwargs))
	if not msg.isValid():
		raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))
	return msg.value()


def video(*args, **kwargs):
	"""
	Call the camera video DBus API. First arg is the function name.
	
	See http://doc.qt.io/qt-5/qdbusabstractinterface.html#call for details about calling.
	See https://github.com/krontech/chronos-cli/tree/master/src/api for implementation details about the API being called.
	See README.md at https://github.com/krontech/chronos-cli/tree/master/src/daemon for API documentation.
	"""
	msg = QDBusReply(cameraVideoAPI.call(*args, **kwargs))
	if not msg.isValid():
		raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))
	return msg.value()


# Only export the functions we will use. Keep it simple. (This can be complicated later as the need arises.)
__all__ = [control, video]


if __name__ == '__main__':
	from PyQt5.QtCore import QCoreApplication
	app = QCoreApplication(sys.argv)
	
	print("Self-test: echo service")
	print(f"min recording period: {control('get_timing_limits')['tMinPeriod']}")
	print("Self-test passed. Python mock API is running.")
	
	sys.exit(app.exec_())