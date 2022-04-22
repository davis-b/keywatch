from Xlib import X, error

from .xlistener import XListener
from ...errors import AlreadyGrabbedError

class KeyGrab(XListener):
	"""
	Uses XGrabKey to grab keys.
	The 'transparent' parameter determines whether or not
	other programs will receive key events from grabbed keys.
	When transparent, programs _will_ receive key events.
	"""
	def __init__(self, transparent=False):
		super().__init__()
		self._error_catcher = error.CatchError(error.BadAccess, error.BadValue, error.BadWindow)
		if transparent:
			self._grab_mode = X.GrabModeSync

	def _input(self):
		for event in self._get_events((X.KeyPress, X.KeyRelease)):
			if self._grab_mode == X.GrabModeSync:
				# Propagate events, letting other programs receive keypresses.
				self._display.allow_events(X.ReplayKeyboard, event.time)
			yield event.detail, event.state, event.type == X.KeyRelease
			#     keycode       modifiers    is_keyup

	def _ungrab(self, keycode: int, modifiers: int=0, call_after_release=False):
		"""
		Attempts to ungrab a key.
		If we would be ungrabbing a key bound to a different call_after_release state,
		do nothing instead.
		"""
		bound_with_different_keystate = self.keycode_function_map.get((keycode, modifiers, not call_after_release))
		if not bound_with_different_keystate:
			for mods in self._modifiers_including_numlock(modifiers):
				self._root.ungrab_key(keycode, mods)
				self._maybe_raise_error(self._error_catcher)
			self._next_event()

	def _grab(self, keycode: int, modifiers: int=0, call_after_release=False):
		""" Grabs a key with specific modifiers, but only if it would be a new key+modifier combo. """
		already_bound = self._keyinfo_bound(keycode, modifiers)
		if not already_bound:
			for mods in self._modifiers_including_numlock(modifiers):
				self._root.grab_key(keycode, mods, True, self._grab_mode, self._grab_mode, onerror=self._error_catcher)
				try:
					self._maybe_raise_error(self._error_catcher)
				except Exception as e:
					if isinstance(e, error.BadAccess):
						raise AlreadyGrabbedError(str(e))
					else:
						raise e
			self._next_event()