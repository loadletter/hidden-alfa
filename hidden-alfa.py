from StringIO import StringIO
from PIL import Image
import zlib
import tarfile
import struct
import os


class ZlibFormat:
	def create(self, **kwargs):
		return zlib.compress(kwargs['data'], level=9)
	def extract(self, **kwargs):
		return zlib.extract(kwargs['data'], data)
		
class TarFormat:
	def create(self, **kwargs):
		fo = StringIO()
		with tarfile.open(mode='w', fileobj=fo) as tar:
			tar.add(kwargs['path'], recursive=True)
		data = fo.getvalue()
		fo.close()
		return data
		
	def extract(self, **kwargs):
		pass

class HiddenAlfa:
	def __init__(self.image):
		if isinstance(a, Image.Image):
			self.image = image
		else:
			self.image = Image.open(image)
		if self.image.mode != 'RGBA':
			raise ValueError("Image must be an RGBA image")
		self.pixels = self.image.load()
		self._zlib = ZlibFormat()
		self._tar = TarFormat()
		self.formats = {
			"z" : self._zlib,
			"t" : self._tar
		}
	
	def _pack_size(self, i):
		data = struct.pack('<I', i)
		assert len(data) == 4
		return data
		
	def _unpack_size(self, data):
		assert len(data) == 4
		return struct.unpack('<I', data)
	
	def usable_size(self):
		size = 0
		for x in self.image.size[0]:
			for y in self.image.size[1]:
				if self.pixels[x, y][3] == 0:
					size += 3
		return size
		
	def _add_raw_data(self, data, flags=''):
		headlen = 4 + len(flags) + 1
		out = self._pack_size(len(data) + headlen) + flags + '|' + data
		idx = 0
		outlen = len(out)
		out += '\x00' * (outlen % 3)
		for x in self.image.size[0]:
			for y in self.image.size[1]:
				if self.pixels[x, y][3] == 0 and idx < outlen:
					self.pixels[x, y] = (out[idx], out[idx + 1], out[idx + 2], 0)
					idx += 3
		if idx < len(out):
			raise IndexError("Could not write %i bytes of %i" % (len(out) - idx, len(out)))
	
	def create(self, path='', fileobj=None, flags=''):
		if not (os.path.exists(path) or fileobj):
			raise IOError("File or directory not found: %s" % path)
		if (os.path.isdir(path) or archive) and not fileobj:
			data = self.formats['t'].create(path)
			_add_raw_data(flags
		else:
			if fileobj:
				data = fileobj.read()
			else:
				with open(path, 'rb') as f:
					data = f.read()
			return data	
