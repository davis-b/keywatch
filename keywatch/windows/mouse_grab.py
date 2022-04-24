import ctypes
from ctypes.wintypes import POINT, DWORD, ULONG
from queue import Queue

from .windows_hook import WinHook
from ..listener import Listener


WH_MOUSE_LL = 14
WM_MOUSEMOVE   = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP   = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP   = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP   = 0x0208
WM_MOUSEWHEEL  = 0x020A
WM_MOUSEHWHEEL = 0x020E

class Buttons:
	"""
	Generic button codes.
	We output these instead of the messy internal ones
	"""
	left = 1
	middle = 2
	right = 3
	mousewheel_up = 4
	mousewheel_down = 5
	mousewheel_left = 6
	mousewheel_right = 7


class Cursor_POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_ulong),
                ("y", ctypes.c_ulong)]
				

dwExtraInfo = ULONG()
class HookStruct(ctypes.Structure):
	_fields_ = [
		('pt', POINT),
		('mouseData', DWORD),
		('flags', DWORD),
		('time', DWORD),
		# ('dwExtraInfo', POINTER(dwExtraInfo)),
		('dwExtraInfo', DWORD),
	]


_keycode_transformations = {
	WM_LBUTTONDOWN: (Buttons.left, 0),
	WM_LBUTTONUP: (Buttons.left, 1),
	WM_MBUTTONDOWN: (Buttons.middle, 0),
	WM_MBUTTONUP: (Buttons.middle, 1),
	WM_RBUTTONDOWN: (Buttons.right, 0),
	WM_RBUTTONUP: (Buttons.right, 1),
	(WM_MOUSEWHEEL, 1): (Buttons.mousewheel_down, 0),
	(WM_MOUSEWHEEL, -1): (Buttons.mousewheel_up, 0),
	(WM_MOUSEHWHEEL, 1): (Buttons.mousewheel_left, 0),
	(WM_MOUSEHWHEEL, -1): (Buttons.mousewheel_right, 0)
}


def _default_on_movement_fn(pos, delta):
	print('Cursor moved to {}.'.format((pos, delta)), end=' ')
	print('Change this function by calling self.set_movement_fn() with your own function.')

class MouseGrab(WinHook, Listener):
	def __init__(self, *args, **kwargs):
		"""
		Tracks mouse movement and button events
		Modifiers do not work with button events for this class.
		"""
		super().__init__(*args, **kwargs)
		self._on_movement = _default_on_movement_fn
		self._mousewheel_deltas = { 'up': 0, 'down': 0, 'left': 0, 'right': 0 }
		self._mousewheel_activation_point = 120
		self._events = Queue()
		self._start_pos = (0, 0)
		self._would_be_pos = [0, 0]

	def start(self, *args, **kwargs):
		self.init_hook(WH_MOUSE_LL)
		self._start_pos = self.pos
		self._would_be_pos = list(self._start_pos)
		super().start(*args, **kwargs)
	
	def _stop(self):
		self.deinit_hook()
		super()._stop()

	def _input(self):
		""" Yields mouse button events. """
		while self.living.is_set():
			event = self._events.get()
			yield event

	def set_movement_fn(self, func):
		self._on_movement = func

	def _hook_callback(self, button, struct_pointer):
		"""
		Callback of our hook from the Windows kernel.  
		Places mouse button events into our '_events' queue.  
		For mouse movement events, this function calls 'self._on_movement(pos, delta)'.
		"""
		event = HookStruct.from_address(struct_pointer)
		wheel_vertical = button == WM_MOUSEWHEEL
		if button == WM_MOUSEMOVE:
			xy = event.pt.x, event.pt.y
			# Windows uses (0,0) as the top left of the monitor.
			# Therefore, we determine our movement delta by reducing
			# our new position by our start position.
			delta = (xy[0] - self._start_pos[0], xy[1] - self._start_pos[1])
			self._would_be_pos[0] += delta[0]
			self._would_be_pos[1] += delta[1]
			self._on_movement(tuple(self._would_be_pos), delta)
		elif wheel_vertical or button == WM_MOUSEHWHEEL:
			# TODO Ensure the following two lines work correctly with mice that
			# provide partial wheel increments.
			wheel_movement = (event.mouseData >> 16) & 0xff
			positive = (event.mouseData & 0x80000000) == 0
			for _ in self._register_mousewheel(wheel_movement, wheel_vertical, positive):
				keycode = _keycode_transformations[(button, 1 if positive else -1)]
				self._events.put(keycode)
		else:
			keycode, keyup = _keycode_transformations[button]
			modifiers = 0
			self._events.put((keycode, modifiers, keyup))

	def _register_mousewheel(self, wheel_delta:int, vertical:bool, positive:bool):
		"""
		Sums previous wheel_delta values until an activation point has been reached.
		At which time, the stored delta gets reduced by the activation point,
		and the function yields True.
		"""
		if positive:
			if vertical:
				direction = 'down'
			else:
				direction = 'left'
		else:
			if vertical:
				direction = 'up'
			else:
				direction = 'right'

		self._mousewheel_deltas[direction] += wheel_delta
		while self._mousewheel_deltas[direction] > self._mousewheel_activation_point:
			self._mousewheel_deltas[direction] -= self._mousewheel_activation_point
			yield True

	@property
	def pos(self):
		"""Returns current cursor position. Accepts no arguments.  """
		cursor = Cursor_POINT()
		ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor))
		return (int(cursor.x), int(cursor.y))
	