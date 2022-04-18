from queue import Queue
from sys import platform

from keywatch import MouseButtonGrab

from utils import wait_for_input, bind, unbind, keycode_names, SafetyNet
from general_tests import test_single_bind, test_unbind_rebind, test_expect_double_bind_error, test_grab_grabbed_listener

def main():
	queue = Queue()
	m = MouseButtonGrab()

	test_unbind_rebind(m, queue, 'lmb')
	test_single_bind(m, queue, 'rmb')
	test_single_bind(m, queue, 'lmb')
	test_single_bind(m, queue, 'rmb')
	test_expect_double_bind_error(MouseButtonGrab(), queue, 'lmb')
	# Windows is producing an error during setup of the test code.
	# It appears to be related to multiprocess.Process. 
	if platform != 'win32':
		test_grab_grabbed_listener(MouseButtonGrab, 'rmb')

if __name__ == '__main__':
	main()