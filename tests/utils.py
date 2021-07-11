from queue import Queue, Empty
from sys import platform

from keywatch.listener import Listener

if platform == 'linux':
	from Xlib import XK
	from Xlib.display import Display
	d = Display()
	keycode_names = {
		'a': d.keysym_to_keycode(XK.string_to_keysym('a')),
		'b': d.keysym_to_keycode(XK.string_to_keysym('b')),
	}
elif platform == 'win32':
	keycode_names = {
		'a': 0x41,
		'b': 0x42,
	}
else:
	raise NotImplementedError('{} is an unsupported platform.'.format(platform))
keycode_names.update({
	'lmb': 1,
	'mmb': 2,
	'rmb': 3,
})

class SafetyNet:
	""" Creates and safely stops a Listener object. """
	def __init__(self, listener: Listener):
		self.listener = listener
	
	def __enter__(self) -> Listener:
		self.listener.start()
		return self.listener
	
	def __exit__(self, *_):
		self.listener.stop()
		self.listener.thread.join(timeout=2)

def add_to_queue(queue):
	queue.put(0)

def bind(queue, listener, keyname):
	listener.bind(lambda: add_to_queue(queue), keycode_names[keyname])
	print('Bound', keyname)

def unbind(listener, keyname):
	listener.unbind(keycode_names[keyname])

def wait_for_input(queue: Queue, timeout=10):
	print('Please press bound key within {} seconds.'.format(timeout))
	try:
		queue.get(timeout=timeout)
		queue.task_done()
	except Empty:
		print('Failed to press key in time.')
		return False
	print('Success')
	print()
	return True