"""
Combines button grabbing and cursor capturing into one
interface that matches the one we have for Windows.
"""

from Xlib import X

from .xlistener import XListener
from .mouse_button_grab import MouseButtonGrab
from .mouse_movement_capture import CursorCapture
from ...errors import AlreadyGrabbedError

class MouseGrab(MouseButtonGrab, CursorCapture, XListener):
	"""
	Grabs cursor movement and mouse button presses, preventing them from being used in the rest of the OS.
	The cursor still moves around visually, despite being grabbed.

	Example usage:  
	mouse = MouseGrab()  
	mouse.on_movement = lambda x, y: print(x, y)  
	mouse.start()  
	mouse.bind(some_function, lmb_keycode)
	sleep(5)  
	mouse.stop()  
	"""

	def __init__(self):
		super().__init__()
		self._event_mask = X.PointerMotionMask | X.ButtonPressMask | X.ButtonReleaseMask

	def _input(self):
		"""
		Blocking function that processes raw mouse events.
		Yields mouse button events, calls self._on_movement(xy, delta) for cursor movement events.
		"""
		for event in self._get_events((X.ButtonPress, X.ButtonRelease, X.NotifyPointerRoot)):
			if event.type == X.NotifyPointerRoot:
				xy = (event.root_x, event.root_y)
				delta = self._stick_cursor(xy)
				# self._stick_cursor generates movement events by warping the pointer back to its starting location,
				# therefore the movement delta is (0, 0).
				# We should and do ignore those events.
				if (delta[0] == delta[1] and delta[0] == 0): continue
				self._on_movement(tuple(self._would_be_pos), delta)
			else:
				yield event.detail, event.state, event.type == X.ButtonRelease
				#     keycode       modifiers    is_keyup