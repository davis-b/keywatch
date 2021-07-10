from sys import platform

if platform == 'linux':
	from .linux import *
elif platform == 'win32':
	from .windows import *
else:
	raise NotImplementedError('{} is not a supported platform.'.format(platform))