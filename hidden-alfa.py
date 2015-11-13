from PIL import Image
import zlib
import struct
import sys
import os

ALFA_ZLIB_DECOMPRESS_MAXSIZE=1024*1024*100

ALFA_CRC32=1
ALFA_ZLIB=2
ALFA_FILENAME=4

class FormatException(Exception):
	pass

def crc32_create(data):
	return struct.pack('<i', zlib.crc32(data)) + data
def crc32_extract(data):
	try:
		crc32 = struct.unpack('<i', data[0:4])[0]
	except struct.error:
		raise FormatException("Couldn't unpack CRC32")
	if crc32 != zlib.crc32(data[4:]):
		raise FormatException("CRC32 checksum mismatch")
	return data[4:]
	
def zlib_create(data):
	return zlib.compress(data, 9)
def zlib_extract(data):
	dec = zlib.decompressobj()
	try:
		data = dec.decompress(data, ALFA_ZLIB_DECOMPRESS_MAXSIZE)
	except zlib.error as e:
		raise FormatException("Zlib error %s" % e)
	if dec.unconsumed_tail:
		raise FormatException("Zlib decompressed size exceeds %i bytes limit" % ALFA_ZLIB_DECOMPRESS_MAXSIZE)
	assert len(dec.unused_data) == 0
	return data

def filename_create(data, name):
	nlen = len(name)
	if nlen >= 0xFF:
		raise FormatException("Filename too long")
	return chr(nlen) + name + data
def filename_extract(data):
	nlen = ord(data[0])
	name = data[1:nlen+1]
	return (data[nlen+1:], name)

class HiddenAlfa:
	def __init__(self, image):
		if isinstance(image, Image.Image):
			self.image = image
		else:
			self.image = Image.open(image)
		if self.image.mode != 'RGBA' or self.image.format != 'PNG':
			raise ValueError("Image must be an RGBA PNG image")
		self.pixels = self.image.load()
		self.headlen = 5
	
	def usable_size(self):
		size = 0
		for x in xrange(self.image.size[0]):
			for y in xrange(self.image.size[1]):
				if self.pixels[x, y][3] == 0:
					size += 3
		return size

	def write_raw_data(self, data):
		idx = 0
		outlen = len(data)
		data += '\xFF' * (3 - (outlen % 3)) * (outlen % 3 != 0)
		for x in xrange(self.image.size[0]):
			for y in xrange(self.image.size[1]):
				if self.pixels[x, y][3] == 0 and idx < outlen:
					self.pixels[x, y] = (ord(data[idx]), ord(data[idx + 1]), ord(data[idx + 2]), 0)
					idx += 3
		if idx < len(data):
			raise FormatException("Could not write %i bytes of %i" % (len(data) - idx, len(data)))
	
	def read_raw_data(self):
		data = []
		for x in xrange(self.image.size[0]):
			for y in xrange(self.image.size[1]):
				if self.pixels[x, y][3] == 0:
					data.extend(self.pixels[x, y][0:3])
		return ''.join(map(lambda x: chr(x), data))
		
	def prefixlength_create(self, data, flags=0):
		return struct.pack('<I', len(data) + self.headlen) + chr(flags) + data
		
	def prefixlength_extract(self, data, offset=0):
		datalen = struct.unpack('<I', data[offset:offset+4])[0]
		if datalen + offset > self.usable_size():
			raise FormatException("Overflow")
		flags = ord(data[offset + self.headlen - 1])
		payloadstart = offset + self.headlen
		payload = data[payloadstart:offset+datalen]
		if datalen != len(payload):
			raise FormatException("Expected %i bytes, got %i" % (datalen, len(payload)))
		return (payload, flags)
	
	def save(self, filename):
		self.image.save(filename, format='PNG')


def cmdline():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("image", help="PNG image to use")
	parser.add_argument("-w", "--write", help="write one or more files to the image, use - to read stdin",  action='append', metavar="file")
	parser.add_argument("-e", "--extract-one", help="extract a file to te specified filename, use - to write to stdout", action="store", metavar="file")
	parser.add_argument("-x", "--extract-many", help="try extracting more than one file", action="store_true")
	parser.add_argument("-t", "--test", help="test image for data", action="store_true")
	parser.add_argument("-r", "--remove", help="blanks transparencies in the image", action="store_true")
	parser.add_argument("-a", "--anonymous", help="don't store file names", action="store_true")
	parser.add_argument("-d", "--destination", help="destination image, defaults to overwriting the original image", action="store")
	args = parser.parse_args()
	destination = args.image
	if args.destination:
		destination = args.destination
	if args.extract_one:
		ha = HiddenAlfa(args.image)
		rawdata = ha.read_raw_data()
		data, flags = ha.prefixlength_extract(rawdata)
		if (flags & ALFA_CRC32) == ALFA_CRC32:
			data = crc32_extract(data)
		elif (flags & ALFA_ZLIB) == ALFA_ZLIB:
			data = zlib_extract(data)
		if (flags & ALFA_FILENAME) == ALFA_FILENAME:
			data, _ = filename_extract(data)
		if args.extract_one == '-':
			sys.stdout.write(data)
			sys.stdout.flush()
		else:
			with open(args.extract_one, 'wb') as f:
				f.write(data)
	elif args.extract_many or args.test:
		ha = HiddenAlfa(args.image)
		rawdata = ha.read_raw_data()
		if args.test:
			print "Total alpha size:", ha.usable_size()
		offset = 0
		filecount = 0
		while True:
			try:
				data, flags = ha.prefixlength_extract(rawdata, offset)
				datalen = len(data)
				if (flags & ALFA_CRC32) == ALFA_CRC32:
					data = crc32_extract(data)
				elif (flags & ALFA_ZLIB) == ALFA_ZLIB:
					data = zlib_extract(data)
				if (flags & ALFA_FILENAME) == ALFA_FILENAME:
					data, fn = filename_extract(data)
				else:
					fn = str(filecount + 1)
			except FormatException:
				break
			else:
				filename = args.image + '_' + os.path.basename(fn)
				if args.extract_many:
					with open(filename, 'wb') as f:
						f.write(data)
				print "File:", filename, len(data), "bytes" 
				offset += datalen
				filecount += 1
	elif args.remove:
		ha = HiddenAlfa(args.image)
		transpsize = ha.usable_size()
		ha.write_raw_data('\xFF' * transpsize)
		ha.save(destination)
	elif args.write:
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
				flags |= ALFA_FILENAME
			zd = zlib_create(d)
			dout = ''
			if (len(zd) + 8) < len(d):
				flags |= ALFA_ZLIB
				dout += zd
			else:
				flags |= ALFA_CRC32
				dout += crc32_create(d)
			out += ha.prefixlength_create(dout, flags)
		ha.write_raw_data(out)
		ha.save(destination)
	else:
		parser.print_help()


if __name__ == "__main__":
	cmdline()
