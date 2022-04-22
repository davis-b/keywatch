from queue import Queue
from sys import platform

from keywatch import Keygrab

from general_tests import test_single_bind, test_unbind_rebind, test_expect_double_bind_error, test_grab_grabbed_listener

def main():
	queue = Queue()
	k = Keygrab()

	test_unbind_rebind(k, queue, 'b')
	test_single_bind(k, queue, 'a')
	test_single_bind(k, queue, 'b')
	test_single_bind(k, queue, 'b')
	test_expect_double_bind_error(Keygrab(), queue, 'a')
	# Windows is producing an error during setup of the test code.
	# It appears to be related to multiprocess.Process. 
	if platform != 'win32':
		test_grab_grabbed_listener(Keygrab, 'b')


if __name__ == '__main__':
	main()