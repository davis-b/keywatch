from threading import Event
from typing import Callable

from Xlib import X
from Xlib.ext.xtest import fake_input

from ...errors import AlreadyGrabbedError, UnknownGrabError

def _default_on_movement_fn(pos, delta):
	print('Cursor moved by {}.'.format((delta)), end=' ')
	print('Change this function by calling CursorCapture.set_movement_fn() with your own function.')

class CursorCapture():
	""" Mix-in class that tracks cursor movement. """

	def __init__(self, on_movement: Callable[[int, int], None] = _default_on_movement_fn):
		self._event_mask = X.PointerMotionMask
		super().__init__()
		self.is_grabbed = Event()
		self._on_movement = on_movement
		self._start_pos = (0, 0)
		self._would_be_pos = [0, 0]

	def set_movement_fn(self, function: Callable[[int, int], None]):
		"""
		This class operates slightly differently than the other Listeners.
		Instead of calling a function for each different keypress, we only have
		a single function to call for each instance of cursor movement.
		That function is set via this function.
		"""
		self._on_movement = function

	def start(self, *args, **kwargs):
		"""
		Grabs the cursor, and then starts
		listening to the cursor on a new thread.
		Raises an error if the grab did not succeed.
		"""
		if not self.is_grabbed.is_set() and not self.living.is_set():
			self._grab_cursor()
		try:
			super().start(*args, **kwargs)
		except Exception as e:
			self._ungrab_cursor()
			raise e

	def _grab_cursor(self, confine=False):
		if self.is_grabbed.is_set():
			return AlreadyGrabbedError('Error grabbing cursor. self.is_grabbed is already set.')
		owner_events = True
		confinement = self._root if confine else 0
		result = self._root.grab_pointer(
			owner_events,
			self._event_mask,
			self._grab_mode,
			self._grab_mode,
			confinement,
			0,
			X.CurrentTime,
			# 'onerror' argument is not available for this function.
		)
		if result != X.GrabSuccess:
			raise UnknownGrabError
		self._start_pos = self.pos
		self._would_be_pos = list(self._start_pos)

	def _ungrab_cursor(self):
		self._display.ungrab_pointer(X.CurrentTime)
		self.is_grabbed.clear()
		self._next_event()

	def _input(self):
		""" Blocking function that yields mouse movement. """
		for event in self._get_events([X.NotifyPointerRoot]):
			xy = (event.root_x, event.root_y)
			delta = self._stick_cursor(xy)
			self._on_movement(tuple(self._would_be_pos), delta)
	
	def _stick_cursor(self, xy):
		"""
		Takes a new location that the cursor has moved to.  
		Warps the cursor back to its starting location.  
		Returns the movement delta from its starting location.  
		A cursor's starting location is set when it is grabbed.  
		"""
		# Linux uses (0,0) as the top left of the monitor.
		# Therefore, we determine our movement delta by reducing
		# our new position by our start position.
		x = xy[0] - self._start_pos[0]
		y = xy[1] - self._start_pos[1]
		self._would_be_pos[0] += x
		self._would_be_pos[1] += y
		if (x != 0 and y != 0):
			fake_input(self._display, X.MotionNotify, x=self._start_pos[0], y=self._start_pos[1])
			self._display.flush()
		return x, y

	@property
	def pos(self):
		data = self._root.query_pointer()._data
		return data['root_x'], data['root_y']