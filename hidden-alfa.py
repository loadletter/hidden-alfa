from StringIO import StringIO
from PIL import Image
import zlib
import struct

ZLIB_DECOMPRESS_MAXSIZE=1024*1024*100

class FormatException(Exception):
	pass

def crc32_create(self, data):
	return struct.pack('<i', zlib.crc32(data)) + data
def crc32_extract(self, data):
	crc32 = struct.unpack('<i', data[0:4])
	if crc32 != zlib.crc32(data[4:]):
		raise FormatException("CRC32 mismatch")
	return data[4:]
	
def zlib_create(self, data):
	return zlib.compress(data, level=9)
def zlib_extract(self, data):
	dec = zlib.decompressobj()
	try:
		data = dec.decompress(data, ZLIB_DECOMPRESS_MAXSIZE)
	except zlib.error as e:
		raise FormatException("Zlib error %s" % e)
	if dec.unconsumed_tail:
		raise FormatException("Zlib decompressed size exceeds %i bytes limit" % ZLIB_DECOMPRESS_MAXSIZE)
	return (data, dec.unused_data)

def prefixname_create(self, data, name):
	nlen = len(name)
	if nlen >= 0xFF:
		raise FormatException("Filename too long")
	return chr(nlen) + name + data
def prefixname_extract(self, data):
	nlen = ord(data[0])
	name = data[1:nlen]
	return (data[nlen:], name)

class HiddenAlfa:
	def __init__(self.image):
		if isinstance(a, Image.Image):
			self.image = image
		else:
			self.image = Image.open(image)
		if self.image.mode != 'RGBA':
			raise ValueError("Image must be an RGBA image")
		self.pixels = self.image.load()
		self.headlen = 5
	
	def usable_size(self):
		size = 0
		for x in self.image.size[0]:
			for y in self.image.size[1]:
				if self.pixels[x, y][3] == 0:
					size += 3
		return size

	def _write_raw_data(self, data):
		idx = 0
		outlen = len(data)
		data += '\x00' * (outlen % 3)
		for x in self.image.size[0]:
			for y in self.image.size[1]:
				if self.pixels[x, y][3] == 0 and idx < outlen:
					self.pixels[x, y] = (data[idx], data[idx + 1], data[idx + 2], 0)
					idx += 3
		if idx < len(data):
			raise IndexError("Could not write %i bytes of %i" % (len(data) - idx, len(data)))
	
	def _read_raw_data(self):
		data = []
		for x in self.image.size[0]:
			for y in self.image.size[1]:
				if self.pixels[x, y][3] == 0:
					data.extend(self.pixels[x, y][0:3])
		return ''.join(map(lamda x: chr(x), data))
		
	def prefixlength_create(self, data, flags=0):
		return struct.pack('<I', len(data) + self.headlen) + chr(flags) + data
		
	def prefixlength_extract(self, data, offset=0)
		datalen = struct.unpack('<I', data[offset:offset+4])
		flags = data[offset + self.headlen]
		payloadstart = offset + self.headlen + 1
		try:
			payload = data[payloadstart:payloadstart+datalen]
		except IndexError:
			raise IndexError("Unexpected end of data")
		return (payload, flags)
