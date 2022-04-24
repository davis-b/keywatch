from queue import Queue
from threading import Event, Condition
from typing import Optional
from ctypes import wintypes
import ctypes
u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

from ..listener import Listener

# from windows_messages import WinMessager
#TODO : Use windows_messages.WinMessager

class Flags:
	WM_HOTKEY = 786
	WM_DESTROY = 2
	WM_BIND = 16
	MOD_NOREPEAT = 0x4000 # Flag to only send message once per keypress, instead of while being held down

	kill_thread_flag = 122
	grab_flag = 123
	ungrab_flag = 124

class KeyGrab(Listener):
	""" Grabs specific keys using user32.RegisterHotkey. """
	def __init__(self):
		super().__init__()
		self._thread_id: Optional[int] = None
		self._grab_queue = Queue()
		# This variable is accessed from different threads.
		# However, its access is synchronized using the grab queue.
		self._grab_error: Optional[int] = None

		self._highest_hotkey_id = 30
		self._keycode_id_map = {}
		self._id_keycode_map = {}
	
	def _thread_entry(self):
		self._thread_id = k32.GetCurrentThreadId()

		# Peek message here, expecting a null result.
		# We do this to create a message queue for this thread.
		# Otherwise, we run into race conditions if the caller
		# tries to grab a hotkey before we create a queue using GetMessage.
		peek_message()
		super()._thread_entry()
	
	def _stop(self):
		""" Posts a message to self.thread_id telling the thread to stop. """
		super()._stop()
		self._post_message(Flags.WM_DESTROY, Flags.kill_thread_flag)
	
	def _grab(self, keycode: int, modifiers: int, call_after_release: bool):
		"""
		NOTE: call_after_release does nothing for this implementation of KeyGrab.
		This is due to limitations with the API call itself.

		While we would love to grab the key right here, we must call it from 
		within our 'input looping' thread instead. Another API quirk.
		Thus, we pass along the message that the thread should check the grab queue.
		"""
		if call_after_release:
			print('NOTE: call_after_release does nothing for this implementation of {}'.format(self.__class__.__name__))
		self._highest_hotkey_id += 1
		modifier = Flags.MOD_NOREPEAT | modifiers
		self._grab_error = None
		self._grab_queue.put((self._highest_hotkey_id, keycode, modifier))

		self._post_message(Flags.WM_BIND, Flags.grab_flag)
		# Wait here for other thread to do the OS level grabbing.
		self._grab_queue.join()

		if self._grab_error:
			raise Exception('Error in an attempt to grab {}. Error # {} {}'.format(
				keycode, self._grab_error, ctypes.FormatError(self._grab_error)
				)
			)
		else:
			self._keycode_id_map[(keycode, modifiers, call_after_release)] = self._highest_hotkey_id
			self._id_keycode_map[self._highest_hotkey_id] = (keycode, modifiers, call_after_release)
	
	def _windows_thread_grab(self):
		"""
		To be called form within our input looping thread.
		Does the OS level grabbing.
		"""
		hotkey_id, keycode, modifiers = self._grab_queue.get()
		success = u32.RegisterHotKey(None, hotkey_id, modifiers, keycode)
		if not success:
			self._grab_error = k32.GetLastError()
			if self._grab_error is None:
				self._grab_error = 0
		self._grab_queue.task_done()
	
	def _ungrab(self, keycode: int, modifiers: int, call_after_release: bool):
		id_ = self._keycode_id_map.pop((keycode, modifiers, call_after_release))
		self._id_keycode_map.pop(id_)
		self._grab_error = None
		self._grab_queue.put(id_)

		self._post_message(Flags.WM_BIND, Flags.ungrab_flag)
		# Wait here for other thread to do the OS level grabbing.
		self._grab_queue.join()

		if self._grab_error:
			raise Exception('Error while ungrabbing a windows key {}. Error # {} {}'.format(
				keycode, self._grab_error, ctypes.FormatError(self._grab_error)
				)
			)
	
	def _windows_thread_ungrab(self):
		hotkey_id = self._grab_queue.get()
		success = (u32.UnregisterHotKey(None, hotkey_id) != 0)
		if not success:
			self._grab_error = k32.GetLastError()
		self._grab_queue.task_done()
	
	def _input(self):
		"""
		Continuously calls GetMessageW (Windows function),
		which blocks until a message is received.
		"""
		msg = wintypes.MSG()
		while self.living.is_set():
			get_message = u32.GetMessageW(ctypes.byref(msg), None, 0, 0)
			if get_message:
				if get_message == -1:
					error = k32.GetLastError()
					print('Unknown error occurred. Error Code =', error, ctypes.FormatError(error))
					break
				if msg.message == Flags.WM_HOTKEY:
					keyinfo = self._id_keycode_map.get(msg.wParam, None)
					if keyinfo:
						yield keyinfo
				elif msg.message == Flags.WM_BIND and msg.wParam == Flags.grab_flag:
					self._windows_thread_grab()
				elif msg.message == Flags.WM_BIND and msg.wParam == Flags.ungrab_flag:
					self._windows_thread_ungrab()
				elif msg.message == Flags.WM_DESTROY and msg.wParam == Flags.kill_thread_flag:
					# stop has been called. self.living is already set to false.
					pass
				else:
					print('Unknown message caught', msg.message, msg.wParam, msg.lParam)
				u32.TranslateMessage(ctypes.byref(msg))
				u32.DispatchMessageW(ctypes.byref(msg))
			else:
				print('Windows GetMessageW returned nothing.')
		
	def _post_message(self, msg, wparam, lparam=0):
		""" Sends a custom message to our input thread. """
		signal_posted = u32.PostThreadMessageW(self._thread_id, msg, wparam, lparam)
		if not signal_posted:
			error = k32.GetLastError()
			raise Exception('Error posting a thread message to thread id {}. Error # {} {}'.format(
				self._thread_id, error, ctypes.FormatError(error)
				)
			)

def peek_message():
	msg = wintypes.MSG()
	NO_REMOVE = 0 # Do not remove messages from the queue.
	u32.PeekMessageW(ctypes.byref(msg), None, 0, 0, NO_REMOVE)