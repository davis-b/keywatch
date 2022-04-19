from threading import Thread, Event
from abc import ABC, abstractmethod
from typing import Optional
from functools import namedtuple

HardwareEvent = namedtuple('Event', [
	'keycode', 'modifiers', 'is_keyup',
])

class Listener(ABC):
	def __init__(self):
		self.keycode_function_map = {}
		self.living = Event()
		self.thread: Optional[Thread] = None
	
	def start(self, daemon=True):
		""" Start listening to a peripheral on a new thread. """
		if self.living.is_set():
			raise Exception('Listener has already been started.')
		self.thread = Thread(target=self._thread_entry, daemon=daemon)
		self.thread.start()
		self.living.wait()
	
	def _thread_entry(self):
		""" 
		The function that is called in a new thread when this module is started.
		Initializes anything required for a specific peripheral grabbing method.
		Finally, begins the input loop.
		"""
		self.living.set()
		self.input_loop()

	def input_loop(self):
		"""
		Default function to be ran after we initialize our new thread.
		Waits for input info that matches a bound keystate we have, and
		then runs the associated function.	
		"""
		for func in self._wait_for_functions():
			func()

	@abstractmethod
	def stop(self):
		""" Stop listening to the peripheral. Can be started again after stopping. """
		self.unbind_all()
		if not self.living.is_set():
			raise Exception('Tried to stop a Listener that is not living.')
		self.living.clear()

	def bind(self, function, keycode: int, modifiers: int=0, call_after_release: bool=False):
		""" 
		Binds a function to a specific keypress/keystate. May grab the key if necessary.
		Raises an Exception if the bind was not successful.
		"""
		if not self.living.is_set():
			raise Exception('Cannot bind keys until the Listener has been started.')
		info = (keycode, modifiers, call_after_release)
		if self.keycode_function_map.get(info, None) is not None:
			raise KeyError('Tried to bind an already bound key combination.')
		self._grab(keycode, modifiers, call_after_release)
		self.keycode_function_map[info] = function
	
	def unbind(self, keycode: int, modifiers: int=0, call_after_release: bool=False):
		""" Unbinds a function from a specific keypress/keystate. Will ungrab the key if able. """
		self.keycode_function_map.pop((keycode, modifiers, call_after_release))
		self._ungrab(keycode, modifiers, call_after_release)

	def unbind_all(self):
		""" Calls self.unbind() on all bound key combinations. """
		for info in self.keycode_function_map.copy():
			self.unbind(*info)

	def _grab(self, keycode: int, modifiers: int, call_after_release: bool):
		""" Grabs the key, button, cursor, etc. """
	
	def _ungrab(self, keycode: int, modifiers: int, call_after_release: bool):
		""" Ungrabs the key, button, cursor, etc. """

	@abstractmethod
	def _input(self):
		""" Generator that yields peripheral input information for any grabbed keys/buttons. """

	def _wait_for_functions(self):
		""" Blocking process that receives grabbed key/button information
		and yields the functions bound to those key combinations. """
		# for input_info in self._input():
		for input_info in self._input():
			if not self.living.is_set():
				break
			try:
				yield self.keycode_function_map[input_info]
			except KeyError:
				continue