from threading import Event
from Xlib import X, error

from .xlistener import XListener
from ...errors import AlreadyGrabbedError


class KeyboardGrab(XListener):
	"""
	Uses X's grab_keyboard function to grab entire keyboard.
	Keys will not be received by other programs.
	This keyboard grabber grabs the entire keyboard upon .start()
	"""
	def __init__(self):
		super().__init__()
		self.is_grabbed = Event()

	def start(self, *args, **kwargs):
		"""
		Grabs the keyboard, and then starts
		listening to the keyboard on a new thread.
		Raises an error if the grab did not succeed.
		"""
		if not self.is_grabbed.is_set() and not self.living.is_set():
			self._grab_keyboard()
		try:
			super().start(*args, **kwargs)
		except Exception as e:
			self._ungrab_keyboard()
			raise e

	def _input(self):
		for event in self._get_events((X.KeyPress, X.KeyRelease)):
			yield event.detail, event.state, event.type == X.KeyRelease
			#     keycode       modifiers    is_keyup

	def _grab_keyboard(self):
		"""
		Grab whole keyboard here.
		After this function succeeds, keyboard events will only be sent to this class.
		Effectively, the keyboard will be inoperable for the rest of the OS.
		"""
		if self.is_grabbed.is_set():
			return AlreadyGrabbedError('Error grabbing keyboard. self.is_grabbed is already set.')
		result = self._root.grab_keyboard(False, self._grab_mode, self._grab_mode, X.CurrentTime)
		success = (result == 0)
		if not success:
			if result == 1:
				raise AlreadyGrabbedError('Error grabbing keyboard.')
			else:
				raise Exception('Error grabbing keyboard. Error # {}'.format(result))
		self._next_event()
		self.is_grabbed.set()
	
	def _ungrab_keyboard(self):
		""" Ungrabs the keyboard. Cannot fail. """
		self._display.ungrab_keyboard(X.CurrentTime)
		self.is_grabbed.clear()
		self._next_event()
	
	def _stop(self):
		"""
		Exits and cleans up the Listener.
		This is the only function needed to safely stop the Listener.
		"""
		super()._stop()
		self._ungrab_keyboard()