from queue import Queue

from keywatch import KeyboardGrab
from keywatch.listener import Listener
from utils import wait_for_input, bind, unbind, keycode_names, SafetyNet
from general_tests import test_single_bind, test_unbind_rebind, test_expect_double_bind_error, test_grab_grabbed_listener

def main():
	queue = Queue()
	k = KeyboardGrab()

	test_unbind_rebind(k, queue, 'b')
	test_single_bind(k, queue, 'a')
	test_single_bind(k, queue, 'b')
	test_single_bind(k, queue, 'b')
	test_expect_double_bind_error(KeyboardGrab(), queue, 'a')
	test_grab_grabbed_listener(KeyboardGrab, 'b')

if __name__ == '__main__':
	main()