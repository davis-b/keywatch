from queue import Queue
from threading import Event, Condition, local, Thread
from typing import Optional
from ctypes import wintypes
import ctypes
u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

from ..listener import Listener

# Required for Windows callback events.
# When we grab the keyboard, we set our active class for that thread.
# During a callback event, we can then access that class.
local_data = local()
local_data.active_class = None

class Flags:
	WM_DESTROY = 2
	WM_QUIT = 18
	WH_KEYBOARD_LL = 13
	HC_ACTION = 0
	LLKHF_UP = 128

	kill_thread_flag = 122
	grab_flag = 123
	ungrab_flag = 124

# This should not have two c_int types in it. Yet it the function we provide receives 3 arguments instead of all 4 of these.
HOOK_CALLBACK = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

class HookStruct(ctypes.Structure):
	_fields_ = [
		('vk_code', wintypes.DWORD),
		('scanCode', wintypes.DWORD),
		('flags', wintypes.DWORD),
		('time', wintypes.DWORD),
		('dwExtraInfo', wintypes.DWORD),
	]

class Keystates:
	down = 0x100
	up = 0x101
	sysdown = 0x104
	sysup = 0x105


class Modifiers:
	alt = 0x01
	control = 0x02
	shift = 0x04
	win = 0x08
	numlock = 0x016

# The actual values to OR together when the selected modifiers are pressed down.
# We have to manually track these, as they are not tracked by the hooking method we are using.
_modifier_values = {
	'alt': 0x01,
	'control': 0x02,
	'shift': 0x04,
	'win': 0x08,
	# 'numlock': 0x016, # Numlock modifier not recognized by Windows
}

_modifier_vkcodes = {
	'win': 0x5B,  #  Left Windows key 
	'lwin': 0x5B,  #  Left Windows key 
	'rwin': 0x5C,  #  Right Windows key 
	'shift': 0x10,
	'lshift': 0xA0,  #  Left SHIFT key,
	'rshift': 0xA1,  #  Right SHIFT key,
	'control': 0x11,
	'lcontrol': 0xA2,  #  Left CONTROL key,
	'rcontrol': 0xA3,  #  Right CONTROL key,
	'alt': 0x12, # could not find left/right alt vk_codes
}

# A map between the vk_code and the modifier value. 
# Used when we manually track our current modifiers.
_modifier_keycodes = {
	_modifier_vkcodes['alt']: _modifier_values['alt'],
	_modifier_vkcodes['control']: _modifier_values['control'],
	_modifier_vkcodes['lcontrol']: _modifier_values['control'],
	_modifier_vkcodes['rcontrol']: _modifier_values['control'],
	_modifier_vkcodes['shift']: _modifier_values['shift'],
	_modifier_vkcodes['lshift']: _modifier_values['shift'],
	_modifier_vkcodes['rshift']: _modifier_values['shift'],
	_modifier_vkcodes['win']: _modifier_values['win'],
	_modifier_vkcodes['lwin']: _modifier_values['win'],
	_modifier_vkcodes['rwin']: _modifier_values['win'],
}


class KeyboardGrab(Listener):
	"""
	Grabs entire keyboard using user32.SetWindowsHookExW.
	
	change _callback if you would like to implement your own handling
	"""
	def __init__(self, allow_key_propagation=False):
		super().__init__()
		self.allow_key_propagation = allow_key_propagation
		if self.allow_key_propagation:
			self.allow_key_propagation = False
			print('TODO: Fix key_propagation (passive keyboard grab) on Windows.')
			print('Key propagation has been set to False.')
		self.is_grabbed = Event()
		self._windows_thread_alive = Event()
		# This variable is accessed from different threads.
		# However, its access is synchronized using the self.is_grabbed Event.
		self._grab_error: Optional[int] = None


		self._thread_id: Optional[int] = None
		self._hook = None
		# Stores input from the hook callback function.
		self._events = Queue()

		self.current_modifiers = 0

		self._message_grab = 16

	def start(self, *args, **kwargs):
		"""
		Grabs the keyboard, and then starts
		listening to the keyboard on a new thread.
		Raises an error if the grab did not succeed.
		"""
		if self.is_grabbed.is_set() or self.living.is_set():
			raise EnvironmentError('Keyboard already grabbed')
		Thread(target=self._windows_thread, daemon=True).start()
		self._grab_keyboard()
		if self._grab_error:
			raise Exception('Error in an attempt to grab entire keyboard. Error # {} {}'.format(
				self._grab_error, ctypes.FormatError(self._grab_error)
				)
			)
		try:
			super().start(*args, **kwargs)
		except Exception as e:
			self._ungrab_keyboard()
			raise e

	def stop(self):
		self._windows_thread_alive.clear()
		self._post_message(Flags.WM_DESTROY, Flags.kill_thread_flag)
		super().stop()
		self._ungrab_keyboard()
		self.current_modifiers = 0
		
	def _grab_keyboard(self):
		"""
		Grabs the entire keyboard.
		Whether or not the OS receives keypresses (passive grab)
		or not (active grab), depends on the 'self.propagation' member of this class.
		If events propagate, we will perform a passive grab.
		'self.propagation' can be changed while a grab is active.
		"""
		self._windows_thread_alive.wait(5)
		if not self._windows_thread_alive.is_set():
			raise Exception('Windows thread was not created properly. Error #', k32.GetLastError())

		self._grab_error = None
		self._post_message(self._message_grab, Flags.grab_flag, Flags.grab_flag)
		# Wait here for other thread to do the OS level grabbing.
		self.is_grabbed.wait(5)
		if not self.is_grabbed.is_set():
			raise Exception('Unable to grab keyboard. Error #', self._grab_error, k32.GetLastError())

		if self._grab_error:
			self.is_grabbed.clear()
			raise Exception('Error in an attempt to grab entire keyboard. Error # {} {}'.format(
				self._grab_error, ctypes.FormatError(self._grab_error)
				)
			)

	def _windows_thread_grab(self):
		hook = u32.SetWindowsHookExW(Flags.WH_KEYBOARD_LL, self._generic_callback, 0, 0)
		if hook:
			self._hook = hook
			local_data.active_class = self
		else:
			self._grab_error = k32.GetLastError()
		self.is_grabbed.set()

	def _ungrab_keyboard(self):
		unhook_success = u32.UnhookWindowsHookEx(self._hook)
		if unhook_success:
			self._hook = None
			self.is_grabbed.clear()
		else:
			if self.is_grabbed.is_set():
				err = k32.GetLastError()
				raise EnvironmentError('Unable to unhook from keyboard {}. Error # {} {}'.format(
					self._hook, err, ctypes.FormatError(err)
				))

	def _input(self):
		while self.living.is_set():
			event = self._events.get()
			yield event

	def _callback(self, keystate, struct_pointer):
		event = HookStruct.from_address(struct_pointer)
		keyup = keystate == Keystates.up or keystate == Keystates.sysup
		try:
			modifier_value = _modifier_keycodes[event.vk_code]
			if self.current_modifiers & modifier_value:
				if keyup:
					self.current_modifiers ^= modifier_value
			elif not keyup:
				self.current_modifiers ^= modifier_value
		except KeyError:
			pass
		self._events.put((event.vk_code, self.current_modifiers, keyup))

	def _windows_thread(self):
		self._thread_id = k32.GetCurrentThreadId()
		msg = ctypes.wintypes.MSG()
		self._windows_thread_alive.set()
		while self._windows_thread_alive.is_set():
			get_msg = u32.GetMessageW(ctypes.byref(msg), None, 0, 0)
			if msg.message == self._message_grab and msg.wParam == Flags.grab_flag:
				self._windows_thread_grab()

	def _post_message(self, msg, wparam, lparam=0):
		""" Sends a custom message to our Windows thread. """
		signal_posted = u32.PostThreadMessageW(self._thread_id, msg, wparam, lparam)
		if not signal_posted:
			error = k32.GetLastError()
			raise Exception('Error posting a thread message to thread id {}. Error # {} {}'.format(
				self._thread_id, error, ctypes.FormatError(error)
				)
			)

	@staticmethod
	@HOOK_CALLBACK
	def _generic_callback(ncode, keystate, struct_pointer):
		if ncode != Flags.HC_ACTION or ncode < 0:
			return u32.CallNextHookEx(0, ncode, keystate, struct_pointer) 
		local_data.active_class._callback(keystate, struct_pointer)
		if local_data.active_class.allow_key_propagation:
			return u32.CallNextHookEx(0, ncode, keystate, struct_pointer) 
		else:
			return 1 