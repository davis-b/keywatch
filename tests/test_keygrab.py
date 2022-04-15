from queue import Queue

from keywatch import Keygrab
from utils import SafetyNet
from general_tests import test_single_bind, test_unbind_rebind, test_expect_double_bind_error, test_grab_grabbed_listener

def test_expect_grab_error(listener: Keygrab):
	with SafetyNet(listener) as k:
		try:
			k._grab(0)
			k._grab(0)
		except Exception:
			pass
		else:
			raise Exception('Expected an error. Grabbed the keycode "0" twice in a row.')

def main():
	queue = Queue()
	k = Keygrab()

	test_expect_grab_error(Keygrab())
	test_unbind_rebind(k, queue, 'b')
	test_single_bind(k, queue, 'a')
	test_single_bind(k, queue, 'b')
	test_single_bind(k, queue, 'b')
	test_expect_double_bind_error(Keygrab(), queue, 'a')
	test_grab_grabbed_listener(Keygrab, 'b')


if __name__ == '__main__':
	main()