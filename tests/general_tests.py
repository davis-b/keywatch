from queue import Queue
import multiprocessing

from keywatch.listener import Listener
from keywatch.errors import AlreadyGrabbedError
from utils import wait_for_input, bind, unbind, keycode_names, SafetyNet

def test_single_bind(listener: Listener, queue: Queue, character: str):
	with SafetyNet(listener) as k:
		bind(queue, k, character)
		success = wait_for_input(queue, timeout=7)
		unbind(k, character)
	if not success:
		raise Exception('User could or did not press the required input in time.')

def test_unbind_rebind(listener: Listener, queue: Queue, character: str):
	with SafetyNet(listener) as k:
		bind(queue, k, character)
		success = wait_for_input(queue, timeout=7)
		unbind(k, character)

		if not success:
			raise Exception('User could or did not press the required input in time. (First bind of two)')
		else:
			bind(queue, k, character)
			success = wait_for_input(queue, timeout=7)
			unbind(k, character)
			if not success:
				raise Exception('User could or did not press the required input in time. (Second bind of two)')

def test_expect_double_bind_error(listener: Listener, queue: Queue, character: str):
	with SafetyNet(listener) as k:
		bind(queue, k, character)
		try:
			bind(queue, k, character)
		except KeyError:
			pass
		else:
			raise Exception('Expected an error. Bound the same key combination twice.')
		success = wait_for_input(queue, timeout=7)
	if not success:
		raise Exception('User could or did not press the required input in time.')

def test_grab_grabbed_listener(T: type, character: str):
	"""
	This test sets up an environment where another process (the child in this test)
	grabs something (key, keyboard, etc) before our process does.
	We expect an exception to be raised when we try to grab an already grabbed character.
	"""
	def child(connection):
		queue = Queue()

		listener = T()
		with SafetyNet(listener):
			listener.bind(lambda: queue.put(0), keycode_names[character])

			# Signal parent that we have grabbed.
			connection.send(True)
			# Wait for parent to have tried grabbing.
			assert(connection.recv() == True)
			connection.close()

	def parent(connection):
		# Wait for child to have grabbed.
		assert(connection.recv() == True)

		try:
			listener = T()
			with SafetyNet(listener):
				listener.bind(lambda: print('Printing from parent. Should not get here.'), keycode_names[character])
		except AlreadyGrabbedError:
			print('Success. Was not able to grab something that was grabbed.')
			success = True
		else:
			print('Error! Did not receive an error when we should have. We tried to grab something that was already grabbed by another process.')
			success = False

		# Signal child that we have tried grabbing.
		connection.send(True)
		connection.close()
		return success

	parent_conn, child_conn = multiprocessing.Pipe()
	p = multiprocessing.Process(target=child, args=(child_conn,))

	print('Multiprocess grab test initiated.')
	p.start()
	success = parent(parent_conn)
	# Wait for child to end.
	p.join()
	print('Multiprocess grabbing test concluded\n')	
	if not success:
		raise Exception('Multiprocess grabbing test failed.')

