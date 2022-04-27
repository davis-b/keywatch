from abc import ABC, abstractmethod
from threading import Event, Thread
from typing import Optional
import ctypes
u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

class Flags:
	WM_DESTROY = 2
	kill_thread_flag = 122

class WinMessager(ABC):
	"""
	Handles Windows messaging thread management.
	"""
	def __init__(self):
		self._windows_thread_alive = Event()
		self._windows_thread_dead = Event()
		self._thread_id: Optional[int] = None
		super().__init__()

	def start_windows_thread(self):
		if self._windows_thread_alive.is_set():
			raise EnvironmentError('Listener already has an active Windows thread')
		Thread(target=self._windows_thread, daemon=True).start()
		self._windows_thread_alive.wait(5)
		if not self._windows_thread_alive.is_set():
			raise Exception('Windows thread was not created properly. Error #', k32.GetLastError())

	def stop_windows_thread(self):
		self._post_message(Flags.WM_DESTROY, Flags.kill_thread_flag)
		self._windows_thread_dead.wait(5)
	
	@abstractmethod
	def _windows_thread(self):
		self._thread_id = k32.GetCurrentThreadId()
		msg = ctypes.wintypes.MSG()
		self._windows_thread_alive.set()
		while True:
			get_msg = u32.GetMessageW(ctypes.byref(msg), None, 0, 0)
			if get_msg:
				if msg.message == Flags.WM_DESTROY and msg.wParam == Flags.kill_thread_flag:
					break
			yield get_msg, msg
		self._windows_thread_alive.clear()
		self._windows_thread_dead.set()

	def _post_message(self, msg, wparam, lparam=0):
		""" Sends a custom message to our Windows thread. """
		signal_posted = u32.PostThreadMessageW(self._thread_id, msg, wparam, lparam)
		if not signal_posted:
			error = k32.GetLastError()
			raise Exception('Error posting a thread message to thread id {}. Error # {} {}'.format(
				self._thread_id, error, ctypes.FormatError(error)
				)
			)