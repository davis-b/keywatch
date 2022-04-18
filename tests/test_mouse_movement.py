from queue import Queue

from keywatch import CursorCapture

from utils import wait_for_input, bind, unbind, keycode_names, SafetyNet
from general_tests import test_single_bind, test_unbind_rebind, test_expect_double_bind_error, test_grab_grabbed_listener

def main():
	queue = Queue()
	cursor = CursorCapture(lambda x, y: queue.put([x, y]))
	cursor.start()
	timeout = 5
	print('Please move the cursor within {} seconds'.format(timeout))
	queue.get(timeout=timeout)
	print('Success')
	cursor.stop()
	cursor.thread.join(1)


if __name__ == '__main__':
	main()