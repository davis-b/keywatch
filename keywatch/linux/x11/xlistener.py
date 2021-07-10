from os import environ
from queue import Queue

from Xlib import X, error
from Xlib.display import Display
from Xlib.protocol.event import AnyEvent

from ...listener import Listener

class Flags:
	# The event type we use to send our custom event.
	message_event = X.FocusIn
	# event_mask = X.FocusChangeMask
	event_mask = X.KeyPressMask
	# A flag signifying we only sent a custom event in order to go through another input loop.
	next_event_flag = 255

class X11Error(BaseException):
	pass

class XListener(Listener):
	def __init__(self):
		super().__init__()
		self._display = Display(environ['DISPLAY'])
		self._root = self._display.screen().root 
		self._grab_mode = X.GrabModeAsync
		self._initial_root_event_mask = 0

		self._modifiers = {
			'shift': X.ShiftMask, # 1
			'control': X.ControlMask, # 4
			'alt': X.Mod1Mask, # 8
			'win': X.Mod4Mask, # 0x40 aka super
			'numlock': X.Mod2Mask,
			'any': X.AnyModifier
		}
	
	def _thread_entry(self):
		self._set_window_attributes()
		super()._thread_entry()	
		self._reset_window_attributes()
	
	def stop(self):
		super().stop()
		self._next_event()
	
	def _get_events(self, type_filter):
		while self.living.is_set():
			event = self._root.display.next_event()
			if event.type in type_filter:
				yield event

	def _maybe_raise_error(self, error_catcher: error.CatchError):
		"""
		Raises the first caught error, or does nothing if there is no error.

		To properly use this function, the caller should add the
		onerror keyword with error_catcher as the key value to whichever
		function they are trying to catch errors from.

		The caller is suggested to properly configure the error_catcher for
		their use case as well.
		"""
		self._display.sync()
		maybe_error = error_catcher.get_error()
		# Getting an error does not remove it from our error catcher.
		# Therefore, we must reset it after each error.
		error_catcher.reset()
		if maybe_error:
			raise maybe_error

	def _modifiers_including_numlock(self, modifiers):
		including_numlock = modifiers | self._modifiers['numlock']
		if modifiers == including_numlock:
			return (modifiers,)
		return (modifiers, including_numlock)

	def _custom_event(self, flag):
		"""
		Sends a custom event to our _input loop.
		"""
		data = bytes([Flags.message_event, flag]+[0]*30)
		event = AnyEvent(data, self._display)
		self._root.send_event(event, event_mask=Flags.event_mask)
		self._display.flush()

	def _next_event(self):
		"""
		Harmlessly flushes the input loop.
		"""
		self._custom_event(Flags.next_event_flag)

	def _keyinfo_bound(self, keycode, modifiers):
		"""
		Returns True if keycode+modifiers are bound with any keystate.
		This function exists because some X11 functions grab without care for keystate.
		Thus, if we grab a key with keyup, and then with keydown, it will perform the same
		grab twice.
		"""
		for state in [True, False]:
			if self.keycode_function_map.get((keycode, modifiers, state), None):
				return True
		
	def _set_window_attributes(self):
		self._initial_root_event_mask = self._root.get_attributes()._data['your_event_mask']
		self._root.change_attributes(event_mask = Flags.message_event)
	
	def _reset_window_attributes(self):
		self._root.change_attributes(event_mask = self._initial_root_event_mask)