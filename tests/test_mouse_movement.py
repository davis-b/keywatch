from queue import Queue

from keywatch import MouseGrab

def main():
	queue = Queue()
	cursor = MouseGrab()
	cursor.set_movement_fn(lambda x, y: queue.put([x, y]))
	cursor.start()
	timeout = 5
	print('Please move the cursor within {} seconds'.format(timeout))
	queue.get(timeout=timeout)
	print('Success')
	cursor.stop()
	cursor.thread.join(1)


if __name__ == '__main__':
	main()