from abc import ABC, abstractmethod
from .windows_messages import WinMessager

from threading import Event, local, Thread
from typing import Optional
from ctypes import wintypes
import ctypes
u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32


# Required for Windows callback events.
# When we set up a hook, we set our active class for that thread.
# During a callback event, we can then access that class.
local_data = local()
local_data.active_class = None

class Flags:
	HC_ACTION = 0

	hook_flag = 123
	unhook_flag = 124
	message_hook = 16

# This should not have two c_int types in it. Yet it the function we provide receives 3 arguments instead of all 4 of these.
HOOK_CALLBACK = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


class WinHook(WinMessager):
	"""
	Handles Windows' HookEx management.
	"""
	def __init__(self, allow_key_propagation=False):
		super().__init__()
		self.allow_key_propagation = allow_key_propagation
		if self.allow_key_propagation:
			self.allow_key_propagation = False
			print('TODO: Fix key_propagation (passive hook) on Windows.')
			print('Key propagation has been set to False.')
		self.is_hooked = Event()
		# This variable is accessed from different threads.
		# However, its access is synchronized using the self.is_hooked Event.
		self._hook_error: Optional[int] = None

		self._active_hook = None
		self._hook_type = None

	@abstractmethod
	def _hook_callback(self, param, struct_pointer):
		pass

	def init_hook(self, hook_type):
		if self.is_hooked.is_set():
			raise EnvironmentError('Already hooked!')
		self.start_windows_thread()
		self._hook(hook_type)
		if self._hook_error:
			self.deinit_hook()
			raise Exception('Error in an attempt to install hook. Error # {} {}'.format(
				self._hook_error, ctypes.FormatError(self._hook_error)
				)
			)

	def deinit_hook(self):
		self.stop_windows_thread()
		self._unhook()
		
	def _hook(self, hook_type):
		""" Registers a hook. """
		self._hook_error = None
		self._hook_type = hook_type
		self._post_message(Flags.message_hook, Flags.hook_flag, Flags.hook_flag)
		# Wait here for the other thread to initialize the hook.
		self.is_hooked.wait(5)
		if not self.is_hooked.is_set() or self._hook_error:
			self.is_hooked.clear()
			raise Exception('Unable to initialize hook. Error #', self._hook_error, k32.GetLastError())

	def _windows_thread_grab(self, hook_type):
		hook = u32.SetWindowsHookExW(hook_type, self._generic_callback, 0, 0)
		if hook:
			self._active_hook = hook
			local_data.active_class = self
		else:
			self._grab_error = k32.GetLastError()
		self.is_hooked.set()

	def _unhook(self):
		unhook_success = u32.UnhookWindowsHookEx(self._active_hook)
		if unhook_success:
			self._active_hook = None
			self.is_hooked.clear()
		else:
			if self.is_hooked.is_set():
				err = k32.GetLastError()
				raise EnvironmentError('Unable to unhook from keyboard {}. Error # {} {}'.format(
					self._active_hook, err, ctypes.FormatError(err)
				))

	def _windows_thread(self):
		for get_msg, msg in super()._windows_thread():
			if msg.message == Flags.message_hook and msg.wParam == Flags.hook_flag:
				self._windows_thread_grab(self._hook_type)
				self._hook_type = None

	@staticmethod
	@HOOK_CALLBACK
	def _generic_callback(ncode, param2, struct_pointer):
		if ncode != Flags.HC_ACTION or ncode < 0:
			return u32.CallNextHookEx(0, ncode, param2, struct_pointer) 
		local_data.active_class._hook_callback(param2, struct_pointer)
		if local_data.active_class.allow_key_propagation:
			return u32.CallNextHookEx(0, ncode, param2, struct_pointer) 
		else:
			return 1 