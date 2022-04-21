"""
Combines button grabbing and cursor capturing into one
interface that matches the one we have for Windows.
"""

from Xlib import X

from .xlistener import XListener
from .mouse_button_grab import MouseButtonGrab
from .mouse_movement_capture import CursorCapture
from ...errors import AlreadyGrabbedError

def _default_on_movement_fn(x, y):
	print('Cursor moved to {}.'.format((x, y)), end=' ')
	print('Change this function by calling CursorCapture.set_movement_fn() with your own function.')

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
		Yields mouse button events, calls self._on_movement(x, y) for cursor movement events.
		# TODO should we also include a movement delta? Revisit this when we work out a solution for windows.
		"""
		for event in self._get_events((X.ButtonPress, X.ButtonRelease, X.NotifyPointerRoot)):
			if event.type == X.NotifyPointerRoot:
				self._on_movement(event.event_x, event.event_y)
				#     x pos          y pos
			else:
				yield event.detail, event.state, event.type == X.ButtonRelease
				#     keycode       modifiers    is_keyup