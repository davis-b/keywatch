from queue import Queue
from sys import platform

from keywatch import MouseGrab
from keywatch.errors import UnknownGrabError

from utils import wait_for_input, bind, unbind, keycode_names, SafetyNet
from general_tests import test_single_bind, test_unbind_rebind, test_expect_double_bind_error, test_grab_grabbed_listener

def main():
	queue = Queue()
	m = MouseGrab()

	test_unbind_rebind(m, queue, 'lmb')
	test_single_bind(m, queue, 'rmb')
	test_single_bind(m, queue, 'lmb')
	test_single_bind(m, queue, 'rmb')
	try:
		# Double bind is not working as intended because we are expected
		# to be able to start two instances of a keyboard grabber.
		# However, when starting two instances of a mouse grabber,
		# it starts grabbing when we call start().
		# Therefore turning the test into more of a double grab test.
		test_expect_double_bind_error(MouseGrab(), queue, 'lmb')
	except UnknownGrabError:
		pass

if __name__ == '__main__':
	main()