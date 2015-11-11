from PIL import Image
import zlib
import struct

ALFA_ZLIB_DECOMPRESS_MAXSIZE=1024*1024*100

ALFA_CRC32=1
ALFA_ZLIB=2
ALFA_FILENAME=4

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
		data = dec.decompress(data, ALFA_ZLIB_DECOMPRESS_MAXSIZE)
	except zlib.error as e:
		raise FormatException("Zlib error %s" % e)
	if dec.unconsumed_tail:
		raise FormatException("Zlib decompressed size exceeds %i bytes limit" % ALFA_ZLIB_DECOMPRESS_MAXSIZE)
	return (data, dec.unused_data)

def filename_create(self, data, name):
	nlen = len(name)
	if nlen >= 0xFF:
		raise FormatException("Filename too long")
	return chr(nlen) + name + data
def filename_extract(self, data):
	nlen = ord(data[0])
	name = data[1:nlen]
	return (data[nlen:], name)

class HiddenAlfa:
	def __init__(self, image):
		if isinstance(a, Image.Image):
			self.image = image
		else:
			self.image = Image.open(image)
		if self.image.mode != 'RGBA' or self.image.format != 'PNG':
			raise ValueError("Image must be an RGBA PNG image")
		self.pixels = self.image.load()
		self.headlen = 5
	
	def usable_size(self):
		size = 0
		for x in self.image.size[0]:
			for y in self.image.size[1]:
				if self.pixels[x, y][3] == 0:
					size += 3
		return size

	def write_raw_data(self, data):
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
	
	def read_raw_data(self):
		data = []
		for x in self.image.size[0]:
			for y in self.image.size[1]:
				if self.pixels[x, y][3] == 0:
					data.extend(self.pixels[x, y][0:3])
		return ''.join(map(lambda x: chr(x), data))
		
	def prefixlength_create(self, data, flags=0):
		return struct.pack('<I', len(data) + self.headlen) + chr(flags) + data
		
	def prefixlength_extract(self, data, offset=0):
		datalen = struct.unpack('<I', data[offset:offset+4])
		flags = data[offset + self.headlen]
		payloadstart = offset + self.headlen + 1
		try:
			payload = data[payloadstart:payloadstart+datalen]
		except IndexError:
			raise IndexError("Unexpected end of data")
		return (payload, flags)
	
	def save(self, filename):
		self.image.save(filename)


def cmdline():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("image", help="PNG image to use")
	parser.add_argument("-w", "--write", help="write one or more files to the image, use - to read stdin",  action='append', metavar="file")
	parser.add_argument("-e", "--extract-one", help="extract one file, use - to write to stdout", action="store_true")
	parser.add_argument("-x", "--extract-many", help="try extracting more than one file", action="store_true")
	parser.add_argument("-t", "--test", help="test image for data", action="store_true")
	parser.add_argument("-r", "--remove", help="blanks transparencies in the image", action="store_true")
	parser.add_argument("-a", "--anonymous", help="don't store file names", action="store_false")
	parser.add_argument("-d", "--destination", help="destination image, defaults to overwriting the original image", action="store")
	parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
	args = parser.parse_args()
	destination = args.image
	if args.destination:
		destination = args.destination
	if args.write:
		data = []
		for num, fn in enumerate(args.write):
			if args.anonymous:
				n = ''
			else:
				n = os.path.basename(fn)
			if fn == '-':
				data.append((n, sys.stdin.read()))
			else:
				with open(fn, 'rb') as f:
					data.append((n, f.read()))
		ha = HiddenAlfa(args.image)
		out = ''
		for n, d in data:
			flags = 0
			if n:
				d = filename_create(d, n)
				flags =| ALFA_FILENAME
			zd = zlib_create(d)
			dout = ''
			if (len(zd) + 8) < len(d):
				flags =| ALFA_ZLIB
				dout += zd
			else:
				flags =| ALFA_CRC32
				dout += crc32_create(d)
			out += ha.prefix_create(dout, flags)
		ha.write_raw_data(out)
		ha.save(destination)
	elif args.extract_one:
		pass
	elif args.extract_many:
		pass
	elif args.test:
		pass
	elif args.remove:
		pass
	else:
		pass


if __name__ == "__main__":
	cmdline()
