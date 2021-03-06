from Xlib import X, error

from ...errors import AlreadyGrabbedError

class MouseButtonGrab():
	"""
	Mix-in class that grabs mouse buttons.
	Note: Button Release events are currently not being tracked. # TODO Fix this
	"""

	def __init__(self):
		self._event_mask = X.ButtonReleaseMask | X.ButtonPressMask
		super().__init__()
		self._error_catcher = error.CatchError(error.BadCursor, error.BadAccess, error.BadValue, error.BadWindow)

	def _grab(self, keycode: int, modifiers: int=0, call_after_release=False):
		owner_events = True
		self._root.grab_button(
			keycode,
			modifiers,
			owner_events,
			self._event_mask,
			self._grab_mode,
			self._grab_mode,
			0, 0,
			onerror=self._error_catcher
		)
		try:
			self._maybe_raise_error(self._error_catcher)
		except Exception as e:
			if isinstance(e, error.BadAccess):
				raise AlreadyGrabbedError(str(e))
			else:
				raise e

	def _ungrab(self, keycode: int, modifiers: int=0, call_after_release=False):
		if not self._keyinfo_bound(keycode, modifiers):
			self._root.ungrab_button(keycode, modifiers)

	def _input(self):
		""" Blocking function that processes raw mouse events and yields our mouse button events. """
		for event in self._get_events((X.ButtonPress, X.ButtonRelease)):
			yield event.detail, event.state, event.type == X.ButtonRelease
			#     keycode       modifiers    is_keyup