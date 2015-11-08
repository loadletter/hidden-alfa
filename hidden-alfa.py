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
		#todo
		return


def pack_size(self, i):
	data = struct.pack('<I', i)
	assert len(data) == 4
	return data
	
def unpack_size(self, data):
	assert len(data) == 4
	return struct.unpack('<I', data)

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
			"Z" : self._zlib,
			"t" : self._tar
		}
	
	def usable_size(self):
		size = 0
		for x in self.image.size[0]:
			for y in self.image.size[1]:
				if self.pixels[x, y][3] == 0:
					size += 3
		return size
		
	def _write_raw_data(self, data, flags=''):
		headlen = 4 + len(flags) + 1
		out = pack_size(len(data) + headlen) + flags + '|' + data
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
	
	def _read_raw_data(self):
		data = []
		for x in self.image.size[0]:
			for y in self.image.size[1]:
				if self.pixels[x, y][3] == 0:
					data.extend(self.pixels[x, y][0:3])
		data = ''.join(map(lamda x: chr(x), data))
		datalen = unpack_size(data[0:4])
		headbuff = data[4:13]
		if  not '|' in headbuff:
			raise ValueError("Header error")
		flags = headbuff[0:headbuff.index('|')]
		payloadstart = headbuff.index('|') + 4 + 1
		try:
			payload = data[payloadstart:payloadstart+datalen]
		except IndexError:
			raise IndexError("Unexpected end of data")
		return (payload, flags)
	
	def create(self, path='', fileobj=None, flags=''):
		if os.path.isfile(path):
			with open(path, 'rb') as f:
				data = f.read()
		elif fileobj:
			data = fileobj.read()
		elif os.path.isdir(path) and (not 't' in flags):
			raise ValueError("Can't archive a directory without an archive format")
		else:
			raise IOError("File or directory not found: %s" % path)
		for fl in flags:
			data = self.formats[fl].create(path=path, data=data)
		self._write_raw_data(data, flags=flags)

	def extract(self, path='', fileobj=None):
		if os.path.exists(path):
			raise IOError("Destination alredy exists: %s" % path)
		data, flags = _read_raw_data(self)
		flags.reverse()
		for fl in flags:
			data = self.formats[fl].extract(path=path, data=data)
		if data:
			if fileobj:
				fileobj.write(data)
			else:
				with open(path, 'wb') as f:
					f.write(data)
		
