# Keywatch #

## What Is Keywatch? ##

_Keywatch_ is a Python library that allows users to easily get access to keyboard and mouse input.  

_Keywatch_ is able to 'grab' single keys or the entire keyboard. Mouse input is not as granular as keyboard input, it's all or nothing there if you want cross platform compatibility. If you can eschew that requirement, and are using Linux, you can dig into [x11/mouse_button_grab.py](keywatch/linux/x11/mouse_button_grab.py) and grab single mouse buttons.

There are two terms that will be used here, active and passive grabbing. An active grab prevents other programs from receiving input from that key, while a passive grab does not. Otherwise, the two grab types are the same, and will call your bound function whenever applicable.  

Grabs are active by default, however Linux does have some options for passive grabbing.  
In a future version, perhaps Windows could reach parity with Linux on this front, and a unified interface could be created.

---

## How To Use / Examples ##

_Keywatch_ exposes 3 primary classes to use. KeyGrab, KeyboardGrab, and MouseGrab.  
KeyGrab and KeyboardGrab operate similarly, with one fundamental difference in implementation. KeyGrab will only grab singular keys when its .bind() function is called, while KeyboardGrab will grab the entire keyboard as soon as .start() is called.  

The requirements for any use of these classes are:
* Initialize the class
* Call instance.start()
* Optionally: call instance.bind() here. It can be called as many times as you want, so long as it comes after instance.start().
* Clean up with instance.stop()

Generally, you will want to call instance.bind() in order to achieve something with this library, however there are exceptions to that.  
The bind() function assigns a keycode to your given function, and it may also start a grab on that key.  


A use case where _Keywatch_ excels is adding a global hotkey to your program.
```python3
from keywatch import KeyGrab

keyboard = KeyGrab()
# Note that _Keywatch_ operates in a new thread, created when you call .start().
keyboard.start()
keyboard.bind(your_function, keycode_to_grab, modifier_keys)
# At this point, _Keywatch_ will call your_function whenever the given keycode is pressed while the specified modifiers are active.

[... your code here ... ]

# Cleanup the grab(s).
keyboard.stop()
```

One may wish to use KeyboardGrab when they want to track all keyboard inputs. You can even hook into the processing code and skip over binding keycodes.

```python3
def process_input(self):
	for event in self._input():
		print('Keycode: {}, modifiers: {}, key released: {}'.format(*event))
		if event[0] == QUIT_KEYCODE: # QUIT_KEYCODE is an example user-defined keycode. It is not part of keywatch
			self.stop()

from keywatch import KeyboardGrab

keyboard = KeyboardGrab()
# This function will be called by the keywatch thread.
# Typically it waits for 'bound' keys to be pressed, and calls
# their associated function.
# We can replace it and do whatever we'd like with the keypresses.
keyboard.input_loop = lambda: process_input(keyboard)
# The keyboard gets grabbed during the start() function.
keyboard.start()
keyboard.thread.join(timeout=10)
```