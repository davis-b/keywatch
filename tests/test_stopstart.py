from keywatch import MouseGrab, KeyboardGrab, KeyGrab

def main():
	for i in (MouseGrab(), KeyboardGrab(), KeyGrab()):
		i.start()
		i.stop()
		i.start()
		i.stop()


if __name__ == '__main__':
	main()