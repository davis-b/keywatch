import ctypes
from queue import Queue
from threading import Event
from ctypes import wintypes

from .windows_hook import WinHook
from ..listener import Listener

class Flags:
	WH_KEYBOARD_LL = 13

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


class KeyboardGrab(WinHook, Listener):
	"""
	Grabs entire keyboard using user32.SetWindowsHookExW.
	
	change _callback if you would like to implement your own handling
	"""
	def __init__(self, allow_key_propagation=False):
		super().__init__(allow_key_propagation)
		# Stores input from the hook callback function.
		self._events = Queue()

		self.current_modifiers = 0

	def start(self, *args, **kwargs):
		"""
		Grabs the keyboard, and then starts
		listening to the keyboard on a new thread.
		Raises an error if the grab did not succeed.
		"""
		self.init_hook(Flags.WH_KEYBOARD_LL)
		try:
			super().start(*args, **kwargs)
		except Exception as e:
			self.stop()
			raise e

	def stop(self):
		self.deinit_hook()
		super().stop()
		self.current_modifiers = 0
		
	def _input(self):
		while self.living.is_set():
			event = self._events.get()
			yield event

	def _hook_callback(self, keystate, struct_pointer):
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